"""One-time local storage migration. No Yahoo calls or token-state changes."""
from __future__ import annotations
import hashlib,json,os
from secrets import token_bytes
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
import manual_fallback as fallback
from secure_site import ROOT,ENCRYPTED,decode,encode,encrypt_records,load_records,store_records

def legacy_key(password,salt,iterations=400_000):
    if len(password)<20 or not 200_000<=iterations<=1_000_000:
        raise ValueError('Legacy migration credential or work factor unavailable')
    return hashlib.pbkdf2_hmac('sha256',password.encode(),salt,iterations,32)

def migrate(secret,legacy_password):
    legacy=ROOT/'data/league-data.enc.json'
    if ENCRYPTED.exists():records=load_records(secret);new_archive=False
    else:
        blob=json.loads(legacy.read_text())
        if blob.get('version')!=1 or blob.get('kdf')!='PBKDF2-SHA256':raise ValueError('Unexpected legacy archive')
        key=legacy_key(legacy_password,decode(blob['salt']),int(blob['iterations']))
        records=json.loads(AESGCM(key).decrypt(decode(blob['nonce']),decode(blob['ciphertext']),b'scfl-data-v1'))
        if not records.get('seasons') or not records.get('currentStandings'):raise ValueError('Incomplete league history')
        # Validate the new format before either stored artifact changes.
        encrypt_records(records,secret);new_archive=True
    private=json.loads(fallback.PRIVATE_KEY.read_text());new_private=None
    if private.get('version')==2:fallback.validate_private_key(secret)
    elif private.get('version')==1:
        key=legacy_key(legacy_password,decode(private['salt']),int(private['iterations']))
        raw=AESGCM(key).decrypt(decode(private['nonce']),decode(private['ciphertext']),b'scfl-manual-private-v1')
        pair=x25519.X25519PrivateKey.from_private_bytes(raw)
        public=json.loads(fallback.PUBLIC_KEY.read_text())
        if pair.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)!=decode(public['public_key']):
            raise ValueError('Legacy fallback key mismatch')
        salt,nonce=token_bytes(16),token_bytes(12)
        cipher=AESGCM(fallback.private_key_key(secret,salt)).encrypt(nonce,raw,fallback.A_KEY)
        new_private={'version':2,'kdf':'HKDF-SHA256','salt':encode(salt),'nonce':encode(nonce),'ciphertext':encode(cipher)}
    else:raise ValueError('Unsupported fallback private key')
    if new_archive:store_records(records,secret)
    if new_private:
        tmp=fallback.PRIVATE_KEY.with_suffix('.tmp');tmp.write_text(json.dumps(new_private,separators=(',',':'))+'\n')
        os.replace(tmp,fallback.PRIVATE_KEY)
    # Both keys and the complete archive must validate before removing the old copy.
    if load_records(secret)!=records:raise ValueError('Archive verification failed')
    fallback.validate_private_key(secret)
    legacy.unlink(missing_ok=True)
    print('Server archive and fallback key verified; retired password-encrypted snapshot removed. No Yahoo calls or token changes.')

if __name__=='__main__':migrate(os.environ['YAHOO_CLIENT_SECRET'],os.getenv('LEGACY_SITE_PASSWORD',''))
