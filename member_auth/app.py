"""Same-origin Yahoo member authentication. Run behind a TLS reverse proxy."""
from __future__ import annotations

import base64
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

import jwt
from flask import Flask, jsonify, redirect, request, send_file, make_response

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from secure_site import decrypt_records

ISSUER = 'https://api.login.yahoo.com'
AUTHORIZE = ISSUER + '/oauth2/request_auth'
TOKEN = ISSUER + '/oauth2/get_token'
DISCOVERY = ISSUER + '/.well-known/openid-configuration'
API = 'https://fantasysports.yahooapis.com/fantasy/v2/'
FLOW_COOKIE = '__Host-scfl-flow'
SESSION_COOKIE = '__Host-scfl-session'
FLOW_TTL = 600
SESSION_TTL = 3600


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def remote_json(url, *, data=None, token=None):
    headers = {'Accept': 'application/json'}
    body = None
    if data is not None:
        body = urlencode(data).encode()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    if token:
        headers['Authorization'] = 'Bearer ' + token
    with urlopen(Request(url, data=body, headers=headers), timeout=15) as response:
        return json.load(response)


def validate_identity(encoded, client_id, nonce):
    discovery = remote_json(DISCOVERY)
    keys_url = discovery['jwks_uri']
    parsed = urlparse(keys_url)
    if discovery.get('issuer') != ISSUER or parsed.scheme != 'https' or parsed.hostname != 'api.login.yahoo.com' or parsed.username or parsed.password:
        raise ValueError('Invalid discovery document')
    header = jwt.get_unverified_header(encoded)
    if header.get('alg') not in ('RS256', 'ES256'):
        raise ValueError('Invalid signing algorithm')
    keys = remote_json(keys_url)['keys']
    key = next(k for k in keys if k.get('kid') == header.get('kid') and k.get('alg', header['alg']) == header['alg'] and k.get('use', 'sig') == 'sig')
    claims = jwt.decode(encoded, jwt.PyJWK.from_dict(key).key,
                        algorithms=[header['alg']], audience=client_id, issuer=ISSUER,
                        options={'require': ['exp', 'iat', 'sub', 'iss', 'aud', 'nonce']})
    if not isinstance(claims['sub'], str) or not claims['sub'] or not secrets.compare_digest(claims['nonce'], nonce):
        raise ValueError('Invalid identity')
    if isinstance(claims['aud'], list) and len(claims['aud']) > 1 and 'azp' not in claims:
        raise ValueError('Missing authorized party')
    if claims.get('azp', client_id) != client_id:
        raise ValueError('Invalid authorized party')
    return claims['sub']


def owns_team(payload, league_key):
    """Called only with the authenticated user's teams collection, never league teams."""
    if isinstance(payload, dict):
        key = payload.get('team_key')
        if isinstance(key, str) and re.fullmatch(re.escape(league_key) + r'\.t\.\d+', key):
            return True
        return any(owns_team(v, league_key) for v in payload.values())
    if isinstance(payload, list):
        return any(owns_team(v, league_key) for v in payload)
    return False


def member_page(source):
    start = source.index('<section class="unlock" id="unlockPanel">')
    end = source.index('</section>', start) + len('</section>')
    source = source[:start] + '''<section class="unlock" id="unlockPanel"><div class="unlock-card">
    <img src="/scfl-logo.png" alt="Siler City Fantasy League logo">
    <h1>League members</h1><p>Sign in with the Yahoo account you use for your league team.</p>
    <a href="/auth/yahoo">Continue with Yahoo</a><p id="unlockStatus" role="status" aria-live="polite"></p>
    </div></section>''' + source[end:]
    start = source.index('    async function unlockLeague(){')
    end = source.index('    async function initialize(){', start)
    source = source[:start] + '''    async function unlockLeague(){
      const status=document.getElementById('unlockStatus');
      const messages={denied:'Yahoo sign-in was cancelled. You can try again.',
        expired:'Your sign-in expired. Please try again.',
        member:'This Yahoo account does not own a team in this league.',
        unavailable:'We could not verify league membership with Yahoo. Please try again later.',
        invalid:'We could not complete sign-in. Please try again.'};
      const reason=new URLSearchParams(location.search).get('login');
      if(reason){status.textContent=messages[reason]||messages.invalid;history.replaceState(null,'',location.pathname);}
      const response=await fetch('/api/league',{credentials:'same-origin',cache:'no-store'});
      if(response.status===401)return new Promise(()=>{});
      if(!response.ok){status.textContent='League records are temporarily unavailable. Please try again later.';return new Promise(()=>{});}
      const db=await response.json();
      document.getElementById('unlockPanel').hidden=true;document.body.classList.remove('locked');
      return db;
    }

''' + source[end:]
    source = source.replace('<footer class="shell">', '''<footer class="shell"><form action="/auth/logout" method="post"><button type="submit">Sign out</button></form>''', 1)
    return source


def create_app(config=None):
    app = Flask(__name__, static_folder=None)
    app.config.update(
        PUBLIC_ORIGIN=os.getenv('SCFL_PUBLIC_ORIGIN', ''),
        YAHOO_CLIENT_ID=os.getenv('YAHOO_CLIENT_ID', ''),
        YAHOO_CLIENT_SECRET=os.getenv('YAHOO_CLIENT_SECRET', ''),
        LEAGUE_KEY=os.getenv('SCFL_LEAGUE_KEY', ''),
        SITE_PASSWORD=os.getenv('SCFL_SITE_PASSWORD', ''),
        AUTH_DB=os.getenv('SCFL_AUTH_DB', ''),
        DATA_FILE=str(ROOT / 'data/league-data.enc.json'),
    )
    if config:
        app.config.update(config)
    cfg = app.config
    origin = urlparse(cfg['PUBLIC_ORIGIN'])
    if origin.scheme != 'https' or not origin.netloc or origin.path or origin.query or origin.fragment or origin.username or origin.password:
        raise ValueError('SCFL_PUBLIC_ORIGIN must be an HTTPS origin without a trailing slash')
    if not re.fullmatch(r'\d+\.l\.\d+', cfg['LEAGUE_KEY']):
        raise ValueError('Set the exact season-specific SCFL_LEAGUE_KEY')
    if not cfg['YAHOO_CLIENT_ID'] or not cfg['YAHOO_CLIENT_SECRET'] or len(cfg['SITE_PASSWORD']) < 20:
        raise ValueError('Configure Yahoo credentials and the existing data encryption password')
    if not cfg['AUTH_DB'] or not Path(cfg['AUTH_DB']).is_absolute():
        raise ValueError('SCFL_AUTH_DB must be an absolute persistent private database path')
    database = Path(cfg['AUTH_DB'])
    if database.is_relative_to(ROOT):
        raise ValueError('Session database must be outside the repository')
    database.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with sqlite3.connect(database) as db:
        db.execute('CREATE TABLE IF NOT EXISTS flows (id TEXT PRIMARY KEY, state TEXT, nonce TEXT, verifier TEXT, expires INTEGER)')
        db.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, subject TEXT, expires INTEGER)')
    database.chmod(0o600)

    @contextmanager
    def connect():
        db = sqlite3.connect(database, timeout=10)
        db.row_factory = sqlite3.Row
        now = int(time.time())
        db.execute('DELETE FROM flows WHERE expires <= ?', (now,))
        db.execute('DELETE FROM sessions WHERE expires <= ?', (now,))
        db.commit()
        try:
            with db:
                yield db
        finally:
            db.close()

    def clear_cookie(response, name):
        response.delete_cookie(name, path='/', secure=True, httponly=True, samesite='Lax')

    def failure(reason):
        response = redirect('/?login=' + reason, 303)
        clear_cookie(response, FLOW_COOKIE)
        return response

    @app.after_request
    def protect(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        return response

    @app.get('/')
    def index():
        return make_response(member_page((ROOT / 'index.html').read_text()))

    @app.get('/scfl-logo.png')
    def logo():
        return send_file(ROOT / 'scfl-logo.png')

    @app.get('/auth/yahoo')
    def login():
        flow, state, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(4))
        with connect() as db:
            old = request.cookies.get(FLOW_COOKIE, '')
            db.execute('DELETE FROM flows WHERE id = ?', (digest(old),))
            db.execute('INSERT INTO flows VALUES (?,?,?,?,?)',
                       (digest(flow), state, nonce, verifier, int(time.time()) + FLOW_TTL))
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        query = urlencode(dict(client_id=cfg['YAHOO_CLIENT_ID'], redirect_uri=cfg['PUBLIC_ORIGIN'] + '/auth/callback',
                               response_type='code', scope='openid fspt-r', state=state, nonce=nonce,
                               code_challenge=challenge, code_challenge_method='S256'))
        response = redirect(AUTHORIZE + '?' + query)
        response.set_cookie(FLOW_COOKIE, flow, max_age=FLOW_TTL, secure=True, httponly=True, samesite='Lax', path='/')
        return response

    @app.get('/auth/callback')
    def callback():
        # Atomically consume the flow before any exchange; replays cannot mint sessions.
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            flow = db.execute('SELECT * FROM flows WHERE id = ?', (digest(request.cookies.get(FLOW_COOKIE, '')),)).fetchone()
            db.execute('DELETE FROM flows WHERE id = ?', (digest(request.cookies.get(FLOW_COOKIE, '')),))
        if not flow:
            return failure('expired')
        states = request.args.getlist('state')
        if len(states) != 1 or not secrets.compare_digest(states[0], flow['state']):
            return failure('invalid')
        if request.args.get('error'):
            return failure('denied')
        codes = request.args.getlist('code')
        if len(codes) != 1 or not codes[0] or len(codes[0]) > 4096:
            return failure('invalid')
        try:
            tokens = remote_json(TOKEN, data=dict(grant_type='authorization_code', code=codes[0],
                redirect_uri=cfg['PUBLIC_ORIGIN'] + '/auth/callback', client_id=cfg['YAHOO_CLIENT_ID'],
                client_secret=cfg['YAHOO_CLIENT_SECRET'], code_verifier=flow['verifier']))
            subject = validate_identity(tokens['id_token'], cfg['YAHOO_CLIENT_ID'], flow['nonce'])
            # Reading a public league does not prove membership. Query only this user's teams.
            game = cfg['LEAGUE_KEY'].split('.')[0]
            teams = remote_json(API + f'users;use_login=1/games;game_keys={game}/teams?format=json', token=tokens['access_token'])
            if not owns_team(teams, cfg['LEAGUE_KEY']):
                return failure('member')
        except (HTTPError, URLError, TimeoutError, OSError):
            return failure('unavailable')
        except (ValueError, KeyError, TypeError, StopIteration, jwt.PyJWTError):
            return failure('invalid')
        session_id = secrets.token_urlsafe(32)
        with connect() as db:
            db.execute('DELETE FROM sessions WHERE id = ?', (digest(request.cookies.get(SESSION_COOKIE, '')),))
            db.execute('INSERT INTO sessions VALUES (?,?,?)', (digest(session_id), subject, int(time.time()) + SESSION_TTL))
        response = redirect('/', 303)
        clear_cookie(response, FLOW_COOKIE)
        response.set_cookie(SESSION_COOKIE, session_id, max_age=SESSION_TTL, secure=True, httponly=True, samesite='Lax', path='/')
        # Yahoo access/refresh/ID tokens are discarded; scheduled commissioner sync stays separate.
        return response

    @app.get('/api/league')
    def league():
        with connect() as db:
            session = db.execute('SELECT subject FROM sessions WHERE id = ?', (digest(request.cookies.get(SESSION_COOKIE, '')),)).fetchone()
        if not session:
            return jsonify(error='sign_in_required'), 401
        try:
            payload = json.loads(Path(cfg['DATA_FILE']).read_text())
            records = decrypt_records(payload, cfg['SITE_PASSWORD'])
        except Exception:
            # No upstream errors, keys, tokens or ciphertext appear in the response/log.
            return jsonify(error='records_unavailable'), 503
        return jsonify(records)

    @app.post('/auth/logout')
    def logout():
        if request.headers.get('Origin') != cfg['PUBLIC_ORIGIN']:
            return jsonify(error='invalid_origin'), 403
        with connect() as db:
            db.execute('DELETE FROM sessions WHERE id = ?', (digest(request.cookies.get(SESSION_COOKIE, '')),))
        response = redirect('/', 303)
        clear_cookie(response, SESSION_COOKIE)
        return response

    return app
