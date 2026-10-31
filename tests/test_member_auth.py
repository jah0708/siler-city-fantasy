"""Security boundaries for per-member Yahoo authentication; no live credentials."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
from urllib.error import HTTPError

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from member_auth import app as auth
from scripts.secure_site import encrypt_records

ORIGIN = 'https://league.example'
KEY = '461.l.844486'
PASSWORD = 'test-password-that-is-long-enough'


class MemberTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.data = root / 'data.json'
        self.records = {'seasons': {'2018': [{'name': 'Private Team'}]}, 'currentStandings': [{'name': 'Current Team'}]}
        self.data.write_text(json.dumps(encrypt_records(self.records, PASSWORD)))
        self.app = auth.create_app(dict(TESTING=True, PUBLIC_ORIGIN=ORIGIN,
            YAHOO_CLIENT_ID='test-client', YAHOO_CLIENT_SECRET='test-secret',
            LEAGUE_KEY=KEY, SITE_PASSWORD=PASSWORD, AUTH_DB=str(root / 'auth.sqlite'), DATA_FILE=str(self.data)))
        self.client = self.app.test_client()

    def get(self, path):
        return self.client.get(path, base_url=ORIGIN)

    def start(self):
        response = self.get('/auth/yahoo')
        query = parse_qs(urlparse(response.location).query)
        self.assertEqual(query['scope'], ['openid fspt-r'])
        self.assertEqual(query['code_challenge_method'], ['S256'])
        self.assertNotIn('test-secret', response.location)
        self.assertIn('Secure', response.headers['Set-Cookie'])
        self.assertIn('HttpOnly', response.headers['Set-Cookie'])
        return query['state'][0]

    def finish(self, state, member=True, error=None):
        teams = {'fantasy_content': {'users': {'user': {'games': {'game': {'teams': [
            {'team': [{'team_key': KEY + '.t.1' if member else '461.l.100.t.1'}]}
        ]}}}}}}
        def upstream(url, **kwargs):
            if url == auth.TOKEN:
                if error:
                    raise error
                self.assertIn('code_verifier', kwargs['data'])
                self.assertEqual(kwargs['data']['redirect_uri'], ORIGIN + '/auth/callback')
                return {'id_token': 'test', 'access_token': 'private-access', 'refresh_token': 'private-refresh'}
            self.assertIn('users;use_login=1', url)
            return teams
        with patch.object(auth, 'remote_json', side_effect=upstream), patch.object(auth, 'validate_identity', return_value='member-id'):
            return self.get('/auth/callback?code=test-code&state=' + state)

    def test_private_routes_are_closed_and_shell_contains_no_password_gate(self):
        self.assertEqual(self.get('/api/league').status_code, 401)
        for path in ['/data/league-data.enc.json', '/.github/yahoo-oauth.enc.json', '/scripts/secure_site.py']:
            self.assertEqual(self.get(path).status_code, 404)
        shell = self.get('/').text
        self.assertIn('Continue with Yahoo', shell)
        self.assertNotIn('unlockPassword', shell)
        self.assertNotIn('crypto.subtle', shell)
        self.assertNotIn('Private Team', shell)

    def test_member_signin_records_logout_and_replay(self):
        state = self.start()
        response = self.finish(state)
        self.assertEqual(response.location, '/')
        cookie = response.headers.getlist('Set-Cookie')[-1]
        self.assertIn('HttpOnly', cookie)
        self.assertIn('Secure', cookie)
        self.assertIn('SameSite=Lax', cookie)
        result = self.get('/api/league')
        self.assertEqual(result.json, self.records)
        self.assertEqual(result.headers['Cache-Control'], 'no-store')
        self.assertEqual(self.finish(state).location, '/?login=expired')
        self.assertEqual(self.client.post('/auth/logout', base_url=ORIGIN).status_code, 403)
        self.assertEqual(self.client.post('/auth/logout', base_url=ORIGIN, headers={'Origin': ORIGIN}).status_code, 303)
        self.assertEqual(self.get('/api/league').status_code, 401)

    def test_other_league_and_upstream_failure_cannot_sign_in(self):
        self.assertEqual(self.finish(self.start(), member=False).location, '/?login=member')
        self.assertEqual(self.get('/api/league').status_code, 401)
        error = HTTPError(auth.API, 403, 'not authorized', {}, None)
        self.assertEqual(self.finish(self.start(), error=error).location, '/?login=unavailable')
        self.assertEqual(self.get('/api/league').status_code, 401)

    def test_state_mismatch_consumes_flow_before_exchange(self):
        state = self.start()
        with patch.object(auth, 'remote_json') as upstream:
            self.assertEqual(self.get('/auth/callback?code=x&state=wrong').location, '/?login=invalid')
            upstream.assert_not_called()
        self.assertEqual(self.finish(state).location, '/?login=expired')

    def test_cancel_expiry_and_cross_browser_callback(self):
        state = self.start()
        self.assertEqual(self.get('/auth/callback?error=access_denied&state=' + state).location, '/?login=denied')
        state = self.start()
        other = self.app.test_client()
        self.assertEqual(other.get('/auth/callback?code=x&state=' + state, base_url=ORIGIN).location, '/?login=expired')
        with patch.object(auth.time, 'time', return_value=time.time() + auth.FLOW_TTL + 1):
            self.assertEqual(self.finish(state).location, '/?login=expired')

    def test_session_expiry_and_tokens_not_persisted(self):
        self.finish(self.start())
        with patch.object(auth.time, 'time', return_value=time.time() + auth.SESSION_TTL + 1):
            self.assertEqual(self.get('/api/league').status_code, 401)
        raw = Path(self.app.config['AUTH_DB']).read_bytes()
        self.assertNotIn(b'private-access', raw)
        self.assertNotIn(b'private-refresh', raw)

    def test_wrong_decryption_password_does_not_leak_records(self):
        self.finish(self.start())
        self.app.config['SITE_PASSWORD'] = PASSWORD + 'wrong'
        response = self.get('/api/league')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json, {'error': 'records_unavailable'})


class IdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(cls.key.public_key()))
        cls.jwk.update(kid='key-one', alg='RS256', use='sig')

    def token(self, **changes):
        claims = dict(iss=auth.ISSUER, sub='member', aud='client', iat=int(time.time()), exp=int(time.time()) + 60, nonce='nonce')
        claims.update(changes)
        return jwt.encode(claims, self.key, algorithm='RS256', headers={'kid': 'key-one'})

    def validate(self, token):
        with patch.object(auth, 'remote_json', side_effect=[{'issuer': auth.ISSUER, 'jwks_uri': auth.ISSUER + '/keys'}, {'keys': [self.jwk]}]):
            return auth.validate_identity(token, 'client', 'nonce')

    def test_signed_identity_and_claim_validation(self):
        self.assertEqual(self.validate(self.token()), 'member')
        for change in [dict(iss='https://evil.example'), dict(aud='other'), dict(exp=1), dict(nonce='other'), dict(azp='other')]:
            with self.assertRaises((ValueError, jwt.PyJWTError)):
                self.validate(self.token(**change))
        bad = self.token()
        parts = bad.split('.')
        parts[1] = jwt.utils.base64url_encode(json.dumps({'sub': 'forged'}).encode()).decode()
        with self.assertRaises(jwt.PyJWTError):
            self.validate('.'.join(parts))

    def test_team_keys_must_match_exact_league(self):
        self.assertTrue(auth.owns_team([{'team_key': KEY + '.t.10'}], KEY))
        self.assertFalse(auth.owns_team({'league_key': KEY}, KEY))
        self.assertFalse(auth.owns_team({'team_key': KEY + '0.t.1'}, KEY))
        self.assertFalse(auth.owns_team({'team_key': '449.l.844486.t.1'}, KEY))


if __name__ == '__main__':
    unittest.main()
