"""Server-only league archive. Member access is authenticated by Yahoo, never a shared password."""
from __future__ import annotations
import base64,json,os
from pathlib import Path
from secrets import token_bytes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
ROOT=Path(__file__).resolve().parents[1]
ENCRYPTED=ROOT/'.github/league-archive.enc.json'
AAD=b'scfl-league-archive-v2'

def encode(value:bytes)->str:return base64.b64encode(value).decode('ascii')
def decode(value:str)->bytes:return base64.b64decode(value,validate=True)
def server_key(secret:str,salt:bytes,purpose:bytes)->bytes:
    if len(secret)<20:raise ValueError('A server credential of at least 20 characters is required')
    if len(salt)!=16:raise ValueError('Invalid encryption salt')
    return HKDF(algorithm=hashes.SHA256(),length=32,salt=salt,info=purpose).derive(secret.encode())
def encrypt_records(records:dict,secret:str)->dict:
    salt,nonce=token_bytes(16),token_bytes(12)
    key=server_key(secret,salt,AAD)
    clear=json.dumps(records,ensure_ascii=False,separators=(',',':')).encode()
    return {'version':2,'kdf':'HKDF-SHA256','salt':encode(salt),'nonce':encode(nonce),'ciphertext':encode(AESGCM(key).encrypt(nonce,clear,AAD))}
def decrypt_records(payload:dict,secret:str)->dict:
    if payload.get('version')!=2 or payload.get('kdf')!='HKDF-SHA256':raise ValueError('Unsupported server archive; migrate legacy storage before syncing')
    salt,nonce,cipher=decode(payload['salt']),decode(payload['nonce']),decode(payload['ciphertext'])
    if len(nonce)!=12 or not 16<=len(cipher)<=4_000_000:raise ValueError('Invalid server archive')
    return json.loads(AESGCM(server_key(secret,salt,AAD)).decrypt(nonce,cipher,AAD))
def load_records(secret:str)->dict:
    return decrypt_records(json.loads(ENCRYPTED.read_text(encoding='utf-8')),secret)
def store_records(records:dict,secret:str)->None:
    if not records.get('seasons') or not records.get('currentStandings'):raise ValueError('Refusing to replace complete league history with empty records')
    payload=encrypt_records(records,secret)
    ENCRYPTED.parent.mkdir(parents=True,exist_ok=True)
    temporary=ENCRYPTED.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload,separators=(',',':'))+'\n',encoding='utf-8')
    os.replace(temporary,ENCRYPTED)
