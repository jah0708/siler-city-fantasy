# Individual Yahoo member sign-in

The optional Python web service in `member_auth/` serves the existing league UI
with individual Yahoo sign-in instead of the shared-password screen. GitHub Pages
continues to serve the current password-protected site until a deliberate cutover.
No client secrets, Yahoo tokens, or record-decryption keys are sent to the browser.

## Member experience

1. Open the new HTTPS league URL and choose **Continue with Yahoo**.
2. Authorize with the Yahoo account that owns their league team.
3. The server validates Yahoo's signed OpenID identity and asks the Fantasy API
   for teams owned by that authenticated account. It requires an exact match to
   the configured season-specific league key. Merely reading league metadata
   never grants access.
4. Approved members see the existing standings, scores, playoffs, draft and history.
   Nonmembers are denied; an unavailable Yahoo API never grants access.
5. Sessions last one hour, then members sign in again and membership is rechecked.
   Sign out invalidates the server session. Removing a manager takes effect at
   their next sign-in, with a maximum one-hour session window. For immediate
   revocation, delete that subject's session rows on the private server.

The service requests `openid fspt-r`, not mail, contacts or calendar. Member Yahoo
access/refresh/ID tokens are discarded after membership verification. The existing
commissioner GitHub Actions sync remains separate, preserving its encrypted
refresh-token chain and three-hour schedule.

## Deployment inputs (required before live activation)

This cannot execute on GitHub Pages. Deploy the **whole repository** as a Python
WSGI service behind HTTPS with a persistent private volume. This change does not
provision a provider, incur a hosting charge, or change Yahoo registration.

| Environment variable | Value |
| --- | --- |
| `SCFL_PUBLIC_ORIGIN` | New HTTPS origin, e.g. `https://league.example.com`, no trailing slash |
| `YAHOO_CLIENT_ID` | SCFLv2 client ID |
| `YAHOO_CLIENT_SECRET` | SCFLv2 secret, in the host's private environment |
| `SCFL_LEAGUE_KEY` | Exact current Yahoo league key: `<NFL game key>.l.844486`. Verify the game key; do not substitute a prior season's key. |
| `SCFL_SITE_PASSWORD` | Existing GitHub Actions data-encryption password; retained only server-side |
| `SCFL_AUTH_DB` | Absolute persistent database path outside the repository, e.g. `/var/lib/scfl/auth.sqlite` |

Install and start from the repository root:

```sh
python -m pip install -r member_auth/requirements.txt
gunicorn --bind 0.0.0.0:8000 --workers 2 --error-logfile - 'member_auth.app:create_app()'
```

Keep Gunicorn access logging disabled. Configure the TLS proxy/provider access
logs to redact `/auth/callback` query strings: those contain short-lived codes.
Do not enable Flask debug mode. No CORS or cross-site cookies are needed: HTML,
authentication and records must use the same origin. Only `/`, the logo, and
explicit authentication/API routes are served; repository files and data files
are not exposed by the web service. Do not configure a blanket static file mount.

The private SQLite database contains short-lived OAuth transactions and hashed
session IDs/Yahoo subjects, not Yahoo tokens. Restrict its parent volume to the
service account (mode 0700), with database mode 0600. Use one service instance
with a shared local volume; do not put SQLite on a network filesystem or use
independent replicas. Restrict public request rates at the TLS proxy to prevent
unbounded creation of login transactions. Expired transactions and sessions are
removed on subsequent authentication/data requests.

Configure host auto-deploy on `main` commits **including data-only commits** so
each GitHub Actions encrypted snapshot is deployed to the web service. Session
storage must survive those deploys. If the provider skips data-only commits,
configure an explicit deploy hook or a private snapshot delivery job before
cutover. Otherwise displayed scores will remain at the deployed snapshot.

## Yahoo configuration and release checklist

- Add the exact new redirect URI `SCFL_PUBLIC_ORIGIN/auth/callback` to SCFLv2.
  Preserve the existing GitHub Pages callback while the commissioner workflow
  still uses it. If Yahoo only allows one callback for this registration, resolve
  the callback/sync migration before releasing; do not silently break the sync.
- Enable OpenID Connect and Fantasy Sports **read** permissions on that client.
  No profile/email scopes are required for membership checks.
- Confirm Yahoo has provisioned Fantasy API access. The previously observed
  HTTP 403 will block all member admissions; adding a login button cannot fix it.
- Set the six private host variables above. GitHub secrets cannot be read back;
  use the original values or rotate deliberately while accounting for the old
  encrypted token chain. Do not paste credentials into issues or source files.
- Test with an actual league member and an unrelated Yahoo account. Confirm the
  unrelated account receives no records, denial/cancel works, and sign out
  prevents a subsequent `/api/league` call.
- Check a newly synced snapshot appears after auto-deployment and history remains.
- Update the member-facing URL only after those checks. There is no automatic
  redirect or password-gate removal in this PR. The old Pages password route
  remains an alternative access path until separately retired; changing this
  service alone does not revoke that existing shared password.

## Validation and limitations

Run `python -m unittest discover -s tests -v` after installing the requirements.
Tests exercise signed identity validation, wrong issuer/audience/nonce/signature,
state binding, cross-browser callbacks, single-use codes, session expiry,
nonmember denial, Yahoo 403 failure, private route protection and logout.
No live Yahoo account or credential is used by these tests. Live callback,
Yahoo permission provisioning and hosting delivery remain deployment checks.

Prior plaintext records in public Git history are outside the scope of this
change. The server still decrypts the existing encrypted snapshot using the
existing password; it never gives members that key. It does not change league
rosters, commissioner privileges, the import workflow or stored history.

References:
- https://developer.yahoo.com/sign-in-with-yahoo/
- https://sports.yahoo.com/developer/docs/
