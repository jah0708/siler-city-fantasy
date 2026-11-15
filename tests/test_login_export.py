import sys,json,unittest,base64,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from export_login_snapshot import encrypt_snapshot,INFO,AAD
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
class LoginExportTests(unittest.TestCase):
 def test_separate_key_roundtrip_without_exposing_scores_or_password(self):
  private=x25519.X25519PrivateKey.generate();raw=private.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
  public={'version':1,'algorithm':'X25519-HKDF-SHA256-A256GCM','public_key':base64.b64encode(raw).decode(),'key_id':hashlib.sha256(raw).hexdigest()[:16]}
  records={'seasons':{'2025':[]},'currentStandings':[{'name':'Sensitive Synthetic Team'}]}
  result=encrypt_snapshot(records,public)
  self.assertNotIn('Sensitive Synthetic Team',json.dumps(result))
  shared=private.exchange(x25519.X25519PublicKey.from_public_bytes(base64.b64decode(result['ephemeral_public'])))
  key=HKDF(algorithm=hashes.SHA256(),length=32,salt=base64.b64decode(result['salt']),info=INFO).derive(shared)
  clear=AESGCM(key).decrypt(base64.b64decode(result['nonce']),base64.b64decode(result['ciphertext']),AAD)
  self.assertEqual(json.loads(clear),records)
  public['key_id']='wrong'
  with self.assertRaises(ValueError):encrypt_snapshot(records,public)
