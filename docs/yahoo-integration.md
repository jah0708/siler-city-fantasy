# Siler City Fantasy — Yahoo integration

## Current operating model

The member site is `https://siler-city-login-trial.vercel.app/`, implemented in [prototypes/yahoo-login](../prototypes/yahoo-login/README.md). Yahoo is the member sign-in method. The old GitHub Pages entrypoint redirects there; it does not provide a shared-password fallback. The historical trial names remain in the existing Vercel project and ciphertext branch to preserve working URLs and integrations.

Read [AGENTS.md](../AGENTS.md), [the adoption record](engineering/ADOPTION.md) and [code review and verification](engineering/CODE_REVIEW.md) before changing this integration. Current Python/Node/Vercel components remain supported. Language/framework changes need a documented benefit and compatible contracts; preserve the existing infrastructure unless a separate cost case and explicit owner decision approve a migration. Do not rotate credentials or launch live data writes as an incidental documentation or review task.

## Data flow and ownership

1. `scripts/update_from_yahoo.py` and the existing `update-yahoo.yml` workflow own scheduled provider synchronization and the encrypted source archive. Preserve validated historical seasons, custom standings, manual fallback and per-section freshness. A partial provider failure must not replace valid records with empty data.
2. `scripts/secure_site.py` stores the server-only archive in `.github/league-archive.enc.json`. Archive and fallback private-key encryption use separate-purpose keys derived from server-side `YAHOO_CLIENT_SECRET`; the retired website password is not the current encryption credential.
3. After successful non-PR synchronization, `export-login-snapshot.yml` publishes only encrypted member snapshots on `login-trial-data`. This exporter makes no Yahoo calls and does not change the provider token chain. The API's private decryption key is server-only.
4. The member API validates the session and configured season-specific league before decrypting/returning the snapshot. Preserve Yahoo membership checks at sign-in, PKCE/state/nonce and identity validation, secure cookies, origin-checked POST sign-out and private/no-store responses. See the member-site README for settings and exact boundaries.

The existing scheduled workflow runs every three hours and supports manual dispatch. Reuse it; do not add another importer or export producer. A green workflow can include a safe provider no-op, so verify data freshness and the completed operation before claiming a live refresh. The source merge, import, export and hosted member experience are distinct results.

## Credentials and Yahoo reauthorization

Keep `YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET` and the established `YAHOO_REFRESH_TOKEN` seed in the repository's secret store. Newly issued refresh tokens live in the encrypted token chain. The member host also has server-only session and delivery keys listed in its `.env.example`; no actual secret belongs in source or browser code.

For a required reauthorization of the current registered application, use `authorize-yahoo.yml` and a short-lived `YAHOO_AUTH_CODE` secret. Confirm the intended app and registered callback before exchange, leave the refresh-token seed intact, and remove the consumed authorization-code secret afterward. The member callback is `https://siler-city-login-trial.vercel.app/api/auth/callback`; the existing server authorization setup retains its registered callback. Do not interchange these roles.

A client-secret rotation is a data/key migration: preserve and re-encrypt the archive, fallback key and token chain under their separate purposes, validate recovery and coordinate the member host before retiring the old secret. Do not repair a decryption failure by generating a new fallback key while encrypted backups still depend on the existing one. Do not reintroduce the retired `SCFL_SITE_PASSWORD` as an operating requirement.

## Privacy and historical records

This repository is public. Commit only the allowed encrypted outputs and public source. Never commit decrypted league records, member identifiers, passwords, OAuth material, private screenshots or logs. Historical exposure is not retroactively removed by the present encryption scheme.

Preserve season-specific adjusted standings, completed-week boundaries, provisional current-week labels, seeds, consolation, historical corrections and source lineage. The imported clubhouse sections include teams, weekly rosters/points, season player statistics, a bounded available-player pool, completed transactions, draft picks and schedules. Retain last-successful section snapshots on errors; do not manufacture a fresh timestamp for stale data. Private claims, pending trades, manager emails and account identifiers are excluded.

The [manual-score record](manual-week-4-5.md) explains encrypted fallback lineage. The member-site README retains the Yahoo approval evidence and its limitations; this engineering guide makes no broader authorization claim.

## Verification

Use the scoped commands and failure cases in [CODE_REVIEW.md](engineering/CODE_REVIEW.md). Keep the Python privacy/scoring suite, member-service OAuth/encryption tests, synthetic browser checks and existing workflow publication exclusions. Test fixtures remain synthetic and are not published as league data. Use live accounts or the live updater only when that operation is within the authorized task, and retain privacy-safe evidence of the actual result.
