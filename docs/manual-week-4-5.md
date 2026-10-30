# Encrypted manual-score backup while Yahoo Fantasy API is unavailable

- GitHub Pages serves a password-encrypted league snapshot; no plaintext league scores are committed to the public repository.
- Original October 16 Week 4–5 scores are stored in `data/manual-fallback.enc.json`.
- The October 30 screenshots provide Week 5–7 final matchup scores, stored separately in `data/manual-week-5-7.enc.json`. Gray projected scores are excluded.
- Both files are encrypted with X25519 + AES-256-GCM using the stable public key in `.github/fallback-public-key.json`. GitHub Actions holds the password-encrypted private key and `SCFL_SITE_PASSWORD` secret.
- The trusted GitHub Actions runner decrypts both inputs, validates ten teams and five games per week, and merges them in chronological order. The newer Week 5 screenshot supersedes the earlier encrypted Week 5 record; Week 4 is retained from the original backup.
- The updater rebuilds regular-season head-to-head records and top-five scoring records through Week 7, encrypts the complete league data with the member password, and updates `data/league-data.enc.json`.
- A valid live Yahoo scoreboard replaces the manual scores once its completed week catches up. If Yahoo only supplies Weeks 1–6, those completed live scores are preserved, and Week 7 remains the manual fallback. No stored newer scores are downgraded.
- The site identifies manually saved scores as such until Yahoo sync succeeds. Automatic refresh continues every three hours, with retries on subsequent runs.
- The manual snapshots are intentionally retained as a backup during Yahoo outages. Only approved encrypted JSON files are published.

To rotate the website password, use a deliberate key rewrapping procedure: do not delete the private-key file or generate a different key while an encrypted backup still depends on it.
