"""Encrypt league records for GitHub Pages without exposing data in the public source.

The site is static: the page and encrypted payload remain publicly accessible,
but decrypting league records requires the high-entropy member password.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from pathlib import Path
from secrets import token_bytes

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
ENCRYPTED = ROOT / "data" / "league-data.enc.json"
AAD = b"scfl-data-v1"
ITERATIONS = 400_000
BLOCK = re.compile(r'\s*<script id="league-data" type="application/json">(.*?)</script>', re.S)


def _encode(blob: bytes) -> str:
    return base64.b64encode(blob).decode("ascii")


def _decode(value: str) -> bytes:
    return base64.b64decode(value, validate=True)


def encrypt_records(records: dict, password: str) -> dict:
    if len(password) < 20:
        raise ValueError("SCFL_SITE_PASSWORD must be at least 20 characters")
    salt, nonce = token_bytes(16), token_bytes(12)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS, 32)
    raw = json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encrypted = AESGCM(key).encrypt(nonce, raw, AAD)
    return {
        "version": 1,
        "kdf": "PBKDF2-SHA256",
        "iterations": ITERATIONS,
        "salt": _encode(salt),
        "nonce": _encode(nonce),
        "ciphertext": _encode(encrypted),
    }


def decrypt_records(payload: dict, password: str) -> dict:
    if payload.get("version") != 1 or payload.get("kdf") != "PBKDF2-SHA256":
        raise ValueError("Unsupported encrypted data format")
    work = int(payload["iterations"])
    if not 200_000 <= work <= 1_000_000:
        raise ValueError("Invalid encryption work factor")
    key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), _decode(payload["salt"]), work, 32
    )
    return json.loads(
        AESGCM(key).decrypt(_decode(payload["nonce"]), _decode(payload["ciphertext"]), AAD)
    )


def load_records(password: str) -> dict:
    if ENCRYPTED.exists():
        return decrypt_records(json.loads(ENCRYPTED.read_text(encoding="utf-8")), password)
    match = BLOCK.search(INDEX.read_text(encoding="utf-8"))
    if not match:
        raise RuntimeError("Neither a readable legacy snapshot nor encrypted data is present")
    return json.loads(match.group(1))


GATE_CSS = """
body.locked .masthead,body.locked nav,body.locked main,body.locked footer{display:none}
.unlock{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;
 background:linear-gradient(150deg,#263a5a,#14223a);color:#fff}
.unlock[hidden]{display:none}
.unlock-card{background:#fff;color:#263348;width:min(440px,100%);padding:30px;border-radius:20px;
 box-shadow:0 20px 70px #0005;text-align:center}
.unlock-card img{display:block;width:96px;max-height:100px;object-fit:contain;margin:0 auto 12px}
.unlock-card h1{font:700 1.8rem Georgia,serif;margin:8px 0}
.unlock-card p{color:#687386;margin:10px 0 20px}
.unlock-card label{display:block;text-align:left;font-size:.86rem;font-weight:700;margin-bottom:6px}
.unlock-card input{width:100%;padding:13px 14px;border:1px solid #a5adbd;border-radius:10px;
 font:inherit;margin-bottom:14px}
.unlock-card button{width:100%;border:0;background:#263a5a;color:#fff;padding:13px;
 border-radius:10px;cursor:pointer;font:700 1rem system-ui}
#unlockStatus{min-height:22px;font-size:.84rem;color:#a34e48;margin:10px 0 0}
"""

GATE_HTML = """
<section class="unlock" id="unlockPanel">
  <div class="unlock-card">
    <img src="scfl-logo.png" alt="Siler City Fantasy League logo">
    <h1>League members</h1>
    <p>Enter the league password to view standings, scores and history.</p>
    <form id="unlockForm">
      <label for="unlockPassword">League password</label>
      <input id="unlockPassword" type="password" autocomplete="off" required minlength="20">
      <button type="submit">View league results</button>
      <div id="unlockStatus" aria-live="polite"></div>
    </form>
  </div>
</section>
"""

GATE_JS = """
    async function unlockLeague(){
      const panel=document.getElementById('unlockPanel');
      const status=document.getElementById('unlockStatus');
      const form=document.getElementById('unlockForm');
      const passwordField=document.getElementById('unlockPassword');
      let payload;
      try{
        const response=await fetch('data/league-data.enc.json',{cache:'no-store'});
        if(!response.ok)throw new Error('Encrypted records unavailable');
        payload=await response.json();
        if(payload.version!==1||payload.kdf!=='PBKDF2-SHA256')throw new Error('Unsupported records');
      }catch(err){
        status.textContent='League data is temporarily unavailable. Please try later.';
        throw err;
      }
      const fromBase64=x=>Uint8Array.from(atob(x),c=>c.charCodeAt(0));
      return new Promise(resolve=>form.addEventListener('submit',async event=>{
        event.preventDefault();status.textContent='Unlocking…';
        form.querySelector('button').disabled=true;
        try{
          const pass=passwordField.value;
          const keySource=await crypto.subtle.importKey('raw',new TextEncoder().encode(pass),'PBKDF2',false,['deriveKey']);
          const key=await crypto.subtle.deriveKey(
            {name:'PBKDF2',salt:fromBase64(payload.salt),iterations:payload.iterations,hash:'SHA-256'},
            keySource,{name:'AES-GCM',length:256},false,['decrypt']
          );
          const clear=await crypto.subtle.decrypt(
            {name:'AES-GCM',iv:fromBase64(payload.nonce),additionalData:new TextEncoder().encode('scfl-data-v1')},
            key,fromBase64(payload.ciphertext)
          );
          const db=JSON.parse(new TextDecoder().decode(clear));
          passwordField.value='';
          panel.hidden=true;
          document.body.classList.remove('locked');
          resolve(db);
        }catch(err){status.textContent='Unable to unlock. Check the password and try again.'}
        finally{form.querySelector('button').disabled=false}
      }));
    }
"""


def protected_html(original: str) -> str:
    if 'id="unlockPanel"' in original:
        if BLOCK.search(original):
            raise RuntimeError("Protected HTML still contains plaintext league records")
        return original
    if not BLOCK.search(original):
        raise RuntimeError("Missing legacy league snapshot; refusing to transform")
    page = BLOCK.sub("", original, count=1)
    if page.count("  </style>") != 1 or page.count("<body>") != 1:
        raise RuntimeError("Original page layout changed; manual review needed")
    page = page.replace("  </style>", GATE_CSS + "\n  </style>", 1)
    page = page.replace("<body>", '<body class="locked">' + GATE_HTML, 1)
    needle = "    const db=JSON.parse(document.getElementById('league-data').textContent);"
    if page.count(needle) != 1:
        raise RuntimeError("Original page JavaScript initialization changed")
    page = page.replace(needle, GATE_JS + "\n    async function initialize(){\n    const db=await unlockLeague();", 1)
    ending = "  </script>\n</body>"
    if page.count(ending) != 1:
        raise RuntimeError("Original page JavaScript ending changed")
    page = page.replace(ending, "    }\n    initialize().catch(err=>console.error('League access unavailable',err));\n  </script>\n</body>", 1)
    old_note = "'2026 results through Week 3 · adjusted record = matchup + point record'"
    new_note = "(year+' results through Week '+(db.yahoo?.week??3)+' · adjusted record = matchup + point record')"
    if old_note in page:
        page = page.replace(old_note, new_note, 1)
    old_weeks = "yearButtons(document.getElementById('matchupWeeks'),renderMatchups,['1','2','3']);"
    if old_weeks not in page:
        raise RuntimeError("Cannot locate week selection buttons")
    page = page.replace(old_weeks,
        "const matchWeeks=Object.keys(db.matchups||{}).sort((a,b)=>Number(a)-Number(b));yearButtons(document.getElementById('matchupWeeks'),renderMatchups,matchWeeks);",1)
    page = page.replace("renderMatchups('3');",
                        "if(matchWeeks.length)renderMatchups(matchWeeks[matchWeeks.length-1]);",1)
    page = page.replace("Final results</p>", "Scores update automatically; current week may be provisional</p>",1)
    page = page.replace(
        "Siler City Fantasy League · League records sourced from the commissioner workbook</footer>",
        'Siler City Fantasy League · Historical records from the commissioner workbook · Fantasy data provided by <a href="https://sports.yahoo.com/fantasy/">Yahoo Fantasy</a></footer>',1
    )
    if 'id="league-data"' in page or not page.startswith("<!doctype html>"):
        raise RuntimeError("Unsafe page conversion; embedded records remain")
    return page


def store_records(records: dict, password: str) -> None:
    if not records.get("seasons") or not records.get("currentStandings"):
        raise ValueError("Refusing to replace complete league history with empty records")
    old_page = INDEX.read_text(encoding="utf-8")
    new_page = protected_html(old_page)
    payload = encrypt_records(records, password)
    ENCRYPTED.parent.mkdir(parents=True, exist_ok=True)
    temporary = ENCRYPTED.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(temporary, ENCRYPTED)
    if old_page != new_page:
        INDEX.write_text(new_page, encoding="utf-8")
