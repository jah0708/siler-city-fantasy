"""Migration preserves complete history and manual keys without changing Yahoo state."""
import base64,hashlib,json,sys,tempfile,unittest
from contextlib import ExitStack
from pathlib import Path
from secrets import token_bytes
from unittest.mock import patch
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import Encoding,PrivateFormat,PublicFormat,NoEncryption
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import secure_site as archive
import manual_fallback as fallback
import migrate_site_storage as migration
SECRET='synthetic-server-client-secret-unit-test-2026'
OLD='retired-shared-member-password-unit-test-2026'
def b64(v):return base64.b64encode(v).decode()
def old_envelope(clear,aad):
 salt,nonce=token_bytes(16),token_bytes(12)
 key=hashlib.pbkdf2_hmac('sha256',OLD.encode(),salt,400_000,32)
 return {'version':1,'kdf':'PBKDF2-SHA256','iterations':400_000,'salt':b64(salt),'nonce':b64(nonce),'ciphertext':b64(AESGCM(key).encrypt(nonce,clear,aad))}
class StorageMigrationTests(unittest.TestCase):
 def run_case(self,wrong=False):
  with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
   root=Path(directory);(root/'data').mkdir();(root/'.github').mkdir()
   legacy=root/'data/league-data.enc.json';new=root/'.github/league-archive.enc.json'
   public=root/'.github/fallback-public-key.json';private=root/'.github/fallback-key.enc.json'
   records={'seasons':{'2018':[{'name':'Historical Team'}]},'currentStandings':[{'name':'Current Team'}],'matchups':{'10':[['A',100,'B',90]]}}
   pair=x25519.X25519PrivateKey.generate();raw=pair.private_bytes(Encoding.Raw,PrivateFormat.Raw,NoEncryption())
   public.write_text(json.dumps({'version':1,'public_key':b64(pair.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw))}))
   private.write_text(json.dumps(old_envelope(raw,b'scfl-manual-private-v1')))
   legacy.write_text(json.dumps(old_envelope(json.dumps(records).encode(),b'scfl-data-v1')))
   before_private=private.read_bytes();before_public=public.read_bytes()
   token=root/'.github/yahoo-oauth.enc.json';token.write_text('existing-token-state-unchanged')
   for mod,name,value in [(migration,'ROOT',root),(migration,'ENCRYPTED',new),(archive,'ENCRYPTED',new),(fallback,'PUBLIC_KEY',public),(fallback,'PRIVATE_KEY',private)]:stack.enter_context(patch.object(mod,name,value))
   if wrong:
    with self.assertRaises(Exception):migration.migrate(SECRET,OLD+'wrong')
    self.assertFalse(new.exists());self.assertTrue(legacy.exists());self.assertEqual(private.read_bytes(),before_private)
   else:
    migration.migrate(SECRET,OLD)
    self.assertFalse(legacy.exists());self.assertEqual(archive.load_records(SECRET),records)
    self.assertEqual(fallback.validate_private_key(SECRET).private_bytes(Encoding.Raw,PrivateFormat.Raw,NoEncryption()),raw)
    self.assertEqual(public.read_bytes(),before_public)
    with self.assertRaises(Exception):archive.load_records(OLD)
    with self.assertRaises(Exception):fallback.validate_private_key(OLD)
    migration.migrate(SECRET,'') # All subsequent runs work without the retired password.
    self.assertEqual(archive.load_records(SECRET),records)
   self.assertEqual(token.read_text(),'existing-token-state-unchanged')
 def test_complete_archive_and_fallback_migrate_once_without_password_dependency(self):self.run_case()
 def test_bad_migration_password_cannot_modify_archive_fallback_or_tokens(self):self.run_case(wrong=True)
