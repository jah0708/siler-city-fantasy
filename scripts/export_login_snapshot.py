"""Export only ciphertext to the isolated trial branch; no Yahoo calls or token writes."""
from __future__ import annotations
import base64,hashlib,json,os
from pathlib import Path
from secrets import token_bytes
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
from secure_site import ROOT,load_records
INFO=b'scfl-login-hub-v1'
AAD=b'scfl-login-snapshot-v1'
BRANCH='login-trial-data'

def enc(v):return base64.b64encode(v).decode('ascii')
def encrypt_snapshot(records,public):
    raw=base64.b64decode(public['public_key'],validate=True)
    key_id=hashlib.sha256(raw).hexdigest()[:16]
    if public.get('version')!=1 or public.get('algorithm')!='X25519-HKDF-SHA256-A256GCM' or public.get('key_id')!=key_id:
        raise ValueError('Invalid trial public key')
    key=x25519.X25519PublicKey.from_public_bytes(raw)
    ephemeral=x25519.X25519PrivateKey.generate();salt,nonce=token_bytes(16),token_bytes(12)
    aes=HKDF(algorithm=hashes.SHA256(),length=32,salt=salt,info=INFO).derive(ephemeral.exchange(key))
    clear=json.dumps(records,ensure_ascii=False,separators=(',',':')).encode()
    return {'version':1,'algorithm':public['algorithm'],'key_id':key_id,
            'ephemeral_public':enc(ephemeral.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)),
            'salt':enc(salt),'nonce':enc(nonce),'ciphertext':enc(AESGCM(aes).encrypt(nonce,clear,AAD))}

def main():
    records=load_records(os.environ['SCFL_SITE_PASSWORD'])
    public=json.loads((ROOT/'.github/login-trial-public-key.json').read_text())
    payload=encrypt_snapshot(records,public)
    repo=os.environ['GITHUB_REPOSITORY']
    if repo!='jah0708/siler-city-fantasy':raise RuntimeError('Unexpected export repository')
    token=os.environ['GH_EXPORT_TOKEN']
    def api(path,method='GET',data=None):
        request=Request('https://api.github.com/repos/'+repo+path,
            data=json.dumps(data).encode() if data is not None else None,method=method,
            headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
                     'X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json'})
        try:
            with urlopen(request,timeout=30) as r:return json.load(r)
        except HTTPError as e:
            if e.code==404:return None
            raise RuntimeError('Trial export could not publish ciphertext') from None
    if api('/git/ref/heads/'+BRANCH) is None:
        head=api('/git/ref/heads/main')['object']['sha']
        api('/git/refs','POST',{'ref':'refs/heads/'+BRANCH,'sha':head})
    previous=api('/contents/snapshot.enc.json?ref='+BRANCH)
    raw=(json.dumps(payload,separators=(',',':'))+'\n').encode()
    body={'message':'Refresh encrypted login-trial snapshot','branch':BRANCH,'content':enc(raw)}
    if previous:body['sha']=previous['sha']
    api('/contents/snapshot.enc.json','PUT',body)
    print('Published separate trial ciphertext. Existing site, password and Yahoo tokens were not modified.')

if __name__=='__main__':main()
