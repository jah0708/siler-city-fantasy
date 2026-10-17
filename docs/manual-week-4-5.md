# Manual-score backup while Yahoo Fantasy API is unavailable

- The static encrypted league snapshot always remains available on GitHub Pages.
- The October 16 screenshot scores for Weeks 4 and 5 are stored only in data/manual-fallback.enc.json (X25519 + AES-256-GCM ciphertext).
  Its plaintext is never committed to this public repository.
- GitHub Actions holds the shared league password in SCFL_SITE_PASSWORD.
  The first main-branch run generates a stable X25519 keypair:
  .github/fallback-public-key.json (public encryption key) and
  .github/fallback-key.enc.json (private key encrypted with the password).
- The manual fallback file is encrypted to that public key, so it can be
  committed safely without knowing or exposing the league password.
- The importer decrypts the fallback only on the trusted GitHub Actions runner,
  validates ten teams and five matchups per week, and rebuilds the regular-season
  point and head-to-head records from Weeks 1–5. It then writes the entire
  snapshot to the existing password-encrypted data/league-data.enc.json.
- The manual record is labeled clearly in the website as manual while Yahoo is
  pending. Yahoo import runs automatically every three hours.
- The saved manual Week 5 snapshot wins over incomplete Yahoo weeks (1–4).
  A valid Yahoo week 5 or later supersedes it; no manual records disappear
  during an API outage.
- Neither the public HTML nor the repository exposes the unencrypted scores.
- If the site password changes, use an explicit key rewrapping process; do not
  delete the private-key file or generate a new key while an encrypted backup
  is still in use.
