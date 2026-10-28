# Siler City Fantasy - Yahoo API automated updates

Uses existing GitHub Pages and GitHub Actions only. No Supabase, new server or Vercel deployment.

## Included
- Yahoo importer: scripts/update_from_yahoo.py
- Encrypted site: scripts/secure_site.py
- Scheduled workflow: .github/workflows/update-yahoo.yml
- Automated tests: tests/test_secure_site.py
- Automatic retries every 3 hours plus manual workflow dispatch

## One-time setup required
1. Add GitHub Actions secret SCFL_SITE_PASSWORD: strong, unique, 20+ character league password. Use https://github.com/jah0708/siler-city-fantasy/settings/secrets/actions
2. Keep the existing YAHOO_CLIENT_ID, YAHOO_CLIENT_SECRET, YAHOO_REFRESH_TOKEN repository secrets configured for the signed Yahoo application.
3. Merge the integration into main. Run Actions -> Update Yahoo fantasy results (encrypted) -> Run workflow.
4. The first successful run encrypts the legacy commissioner data and installs the unlock page *before* checking Yahoo, whether Yahoo access has been enabled or not.
5. After Yahoo authorization is enabled, the next scheduled run imports and encrypts validated ten-team scoreboard results automatically.

## Replacing the Yahoo app (SCFLv2)
Yahoo requires a new app registration to enable the approved Fantasy Sports permission.
Keep the registered callback exactly `https://jah0708.github.io/siler-city-fantasy/`.

1. Replace the repository's `YAHOO_CLIENT_ID` and `YAHOO_CLIENT_SECRET` Actions secrets with the new app credentials. Do not put them in the website or repository source.
2. Authorize the new app for Fantasy Sports read access and store the short-lived authorization code in the `YAHOO_AUTH_CODE` Actions secret.
3. Run **Authorize Yahoo OAuth (one-time)** on `main` immediately. Leave `YAHOO_REFRESH_TOKEN` configured: it remains the seed identifying the encrypted token chain, while the newly issued refresh token is stored encrypted and used for subsequent syncs.
4. A successful authorization-code exchange replaces the old app's encrypted token state using the new client secret. Failed exchanges leave the old state intact. Ordinary scheduled refreshes never bypass decryption errors.
5. Remove the consumed `YAHOO_AUTH_CODE` secret. Check the import logs for a completed ten-team live update; a green workflow can also mean Yahoo provisioning is still pending.

## Security and limits
- The website shell is public GitHub Pages, but the actual league records are ciphertext. Members enter a shared password to decrypt in their browser.
- There is no individual account management or server-side authentication. Use a strong password because public ciphertext can be attacked offline.
- Historic plaintext records from previous commits may remain available in public Git history; this deployment does not rewrite history.
- Never store Yahoo plaintext results or secrets in public Git. It stages only the gated index.html and data/league-data.enc.json.
- Yahoo approved private, noncommercial league-member access, record retention and AI-assisted analysis under Personal Use.
- An unprovisioned Yahoo app produces a safe no-op and subsequent automatic retries. Expired OAuth refresh tokens still require manual reauthorization.
- Scoring while a week is in progress is provisional.

## Test locally
Install cryptography==46.0.4 and run: python -m unittest discover -s tests -v

