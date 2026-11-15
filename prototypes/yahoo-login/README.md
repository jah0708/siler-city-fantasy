# Yahoo member sign-in trial

This is an isolated prototype. It does not change the live GitHub Pages site,
its password, its Yahoo registration, or its scheduled import.

## What is implemented

- Yahoo OIDC authorization code flow using maintained `openid-client`.
- PKCE S256, browser-bound encrypted state/nonce cookie, signature/issuer/audience/
  expiry/nonce verification, and fixed HTTPS callback.
- Membership lookup using **the member's access token**, then exact comparison
  with the current-season Siler City league key.
- One-hour encrypted `Secure; HttpOnly; SameSite=Lax` host-only sessions.
- No member Yahoo access, refresh or ID tokens retained or exposed to the page.
- Server-side decryption of a separate trial-key-encrypted league snapshot;
  guarded responses are `private, no-store`. Anonymous/non-members cannot fetch it.
- Existing navy/gold UI generated for the new same-origin host; no data files or
  secrets are copied into public build output.
- Same-origin POST logout; invalid, expired and cancelled logins fail closed.

## Session choice

This trial deliberately tests a one-hour membership lease with no token database.
Refreshing a page does not require a new login while the session remains valid.
After expiry, the user follows Yahoo sign-in again; Yahoo may already remember the
account. A seven- or thirty-day "remember me" option needs a durable server-side
session/token store, refresh-token rotation, membership rechecks and revocation.
It is a separate production extension, not implemented by this prototype.

## Local validation

Requires Node 22+.

```
npm ci
npm test
npm run build
```

The tests use synthetic identities and signed test ID tokens. They check wrong
state/nonce, forged signatures, wrong issuer/audience, expired ID tokens/sessions,
non-members, wrong-season membership, encrypted data handling, and logout CSRF.
They do not establish that the real registered Yahoo app accepts this flow.

## Hosted trial status — November 15, 2026

- Vercel project: `siler-city-login-trial` in `JAH0708 Projects`.
- Project ID: `prj_9lO1KI5gf5PnWrawR5UTKAnzisJn`.
- Isolated trial URL: https://siler-city-login-trial.vercel.app/
- Deployed source: `84bdbf9bda3dedcf872e843bdaf009bfba56524b`.
- Yahoo SCFLv2 is a Confidential Client with Fantasy Sports Read enabled.
- The additional callback `https://siler-city-login-trial.vercel.app/api/auth/callback`
  was saved successfully in Yahoo after Jonny's confirmation. The original
  `https://jah0708.github.io/siler-city-fantasy/` callback is preserved.
- Trial host returns `enabled:false`; protected league data is unavailable.
  Server secrets have not been configured and no real OAuth consent/token
  exchange has been performed through the trial.
- The existing site password and GitHub Yahoo credentials were not changed.
- Before enabling, verify the OIDC/Fantasy scope combination and configure
  server secrets. A new real-account authorization must be tested with care for
  the existing refresh-token chain, then the original sync rechecked.

## Preview configuration sequence

1. Create a **separate** preview hosting project using this directory as its root.
   Keep the UI and APIs on the same HTTPS origin. Do not reuse Wave Angler's project.
2. Confirm a stable callback `https://<new-origin>/api/auth/callback` with Yahoo.
   Preserve the existing `https://jah0708.github.io/siler-city-fantasy/` callback
   used by the import. Do not assume Yahoo allows multiple callbacks; inspect the
   app settings or ask Yahoo before modifying the working registration.
3. Confirm OIDC `openid` + the already-approved Fantasy Read permission for this
   client, and whether the requested use by other members is covered. The exact
   accepted Fantasy scope is configuration, not assumed by this code.
4. Set the values from `.env.example` as server secrets. `SESSION_KEY` is 32 random
   bytes, base64 encoded. Set `DATA_PRIVATE_KEY` from the trial-only keypair as a Secret. The existing
   league password stays in GitHub Actions and is never copied to the trial server.
5. Set the verified current-season league key from the live importer. Season keys
   must be updated at rollover; there is no fallback to a previous-season grant.
6. Enable the prototype only after configuration/permission checks. The default
   `YAHOO_LOGIN_ENABLED=false` exposes no functional login or league data route.
7. Test a member and a non-member, cancellation, refresh, expiry, logout and Yahoo
   outage. Confirm tokens/passwords are absent from frontend, logs and responses.
8. Review retention requirements and account/plan costs before league rollout.

## Existing approval evidence

John Klem's October 16 email explicitly answered yes to a private password-gated
league-participant site for scores/standings, retaining weekly scores/standings/
historical results, and the described non-training AI analysis. The October 28
completed agreement retains narrower sharing/caching language. The interaction
between the email and signed agreement is unresolved, and the email does not
explicitly cover OAuth member login or the expanded all-player/roster views.
This prototype is not a determination of contractual permission.

## Boundaries and remaining work

An isolated disabled hosting project and an additional Yahoo callback are now
prepared as recorded above. Trial-only server secrets are configured without changing the working sync
credentials. No consent settings or member invitations were changed. No real Yahoo round-trip has been performed. Deploying a disabled shell alone does not verify authentication.
Existing shared-password access remains available at the current site during any
pilot. The public ciphertext and old repository history are not retroactively
hidden by adding this login option. Rate limits and a durable session store are
production follow-up work if longer sessions or greater scale are needed.

## Primary references

- https://developer.yahoo.com/sign-in-with-yahoo/
- https://sports.yahoo.com/developer/docs/
- https://developer.yahoo.com/oauth2/guide/flows_authcode/
- https://github.com/panva/openid-client
- https://vercel.com/docs/functions/runtimes/node-js

## Separate encrypted data channel

`export-login-snapshot.yml` reads the saved snapshot using the existing Actions
password, encrypts it to `.github/login-trial-public-key.json`, and publishes only
ciphertext to the `login-trial-data` branch. It is independent of the working Yahoo
import and runs after a successful main-branch sync or by manual dispatch. It
never refreshes or modifies Yahoo tokens. Only the trial server has the private
key, stored as the unreadable `DATA_PRIVATE_KEY` Secret. The data route checks a
verified member session and season before serving decrypted records, with no-store
headers. The original site password is not required on the new server.
