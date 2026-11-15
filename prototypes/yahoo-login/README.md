# Siler City Yahoo member site

League URL: https://siler-city-login-trial.vercel.app/

Yahoo is the member site's only sign-in method. The hosting project retains its
original trial name to preserve the working callback and URL. The previous
GitHub Pages link redirects here and clears the retired password from tab storage.
No authorization codes or query parameters are forwarded by that redirect.

## Access

- Yahoo OIDC authorization code flow, PKCE S256, encrypted browser-bound state and
  nonce, signature/issuer/audience/expiry validation through `openid-client`.
- Exact current-season league membership checked using the signing-in member's
  access token. A non-member receives no session or decrypted league records.
- One-hour encrypted Secure, HttpOnly, SameSite=Lax, host-only session cookies.
  Refreshing within that hour retains access. Member Yahoo tokens are not stored.
- Same-origin POST sign-out, origin checking and private/no-store data responses.
- A server-only X25519 private data key is required. No shared-password fallback
  or public password-decrypted data endpoint is supported by the application.

Real member authorization, page refresh and sign-out were verified on November 15,
2026. Synthetic tests cover non-members, wrong-season membership, cancelled and
expired login, token tampering and cross-origin logout. Testing with additional
real member and non-member accounts remains useful during rollout.

## Data and server connection

The existing scheduled Yahoo import and refresh-token chain continue to run in
GitHub Actions. Their Yahoo credentials and token-state encryption are preserved.

The complete historical archive and manual fallback private key are encrypted
using separate-purpose HKDF-SHA256 keys derived from the existing server-side
`YAHOO_CLIENT_SECRET`. They are never exposed to the browser. The retired shared
password is not needed for regular imports, fallback handling or snapshot export.
The one-time migration converts the former archive and fallback key, verifies
both, then removes `data/league-data.enc.json`. It makes no Yahoo calls.

After a successful import, `export-login-snapshot.yml` encrypts the snapshot to
`.github/login-trial-public-key.json` and publishes only ciphertext on the
`login-trial-data` branch. Only Vercel has the unreadable `DATA_PRIVATE_KEY` Secret.
The API verifies the session and exact season before decrypting this snapshot.
If Yahoo is unavailable, the saved complete archive remains available. Old Git
history is not retroactively erased by this migration.

Do not rotate Yahoo client credentials casually: archive and fallback keys must
be migrated when rotating the underlying server secret, as must the existing
Yahoo token-state encryption. Session and delivery keys are separate.

## Source and hosting

- `web/league.html` and `assets/`: navy/gold member interface.
- Root `index.html`: fixed redirect from the old GitHub Pages address.
- `build.mjs`: allowlisted static build; no data, source secrets or API code copied.
- Vercel project `siler-city-login-trial`, ID `prj_9lO1KI5gf5PnWrawR5UTKAnzisJn`.
- Root directory `prototypes/yahoo-login`; Node 22; output `public`.
- Yahoo callback: `https://siler-city-login-trial.vercel.app/api/auth/callback`.
- Original GitHub Pages callback remains registered for existing server setup.
- Scopes `openid fspt-r` were accepted by SCFLv2 in the real authorization test.
- `.env.example` lists server-only configuration. Never commit actual values.

## Validation

Run `python -m unittest discover -s tests -v` from the repository root, then
`npm ci && npm test && npm run build` here. GitHub CI also runs the full dashboard
browser checks with synthetic records and native form sign-out under the deployed
referrer policy. Non-scheduled imports decrypt the real archive only in runner
memory for a rendering smoke check before publishing ciphertext. No private
screenshots or data files are uploaded by that check.

Longer sessions need a durable session store, revocation and membership rechecks.

## Approval evidence

John Klem's October 16 email answered yes to a private league-participant site for
scores/standings, weekly/historical retention and the described non-training AI
analysis. The October 28 agreement retains narrower sharing/caching language;
the email does not explicitly cover OAuth login or expanded roster/player views.
This implementation does not resolve that contractual interpretation.

## Primary references

- https://developer.yahoo.com/sign-in-with-yahoo/
- https://sports.yahoo.com/developer/docs/
- https://developer.yahoo.com/oauth2/guide/flows_authcode/
- https://github.com/panva/openid-client
- https://vercel.com/docs/functions/runtimes/node-js
