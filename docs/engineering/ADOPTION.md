# Siler City Fantasy application standard adoption

Owner direction: 2026-11-25. Standard: 2026.11.2. This correction supersedes the mandatory language and infrastructure destinations in 2026.11.1.

The [Application Architecture Charter](APPLICATION_STANDARD.md) defines common engineering requirements while allowing justified language/framework changes. Preserve the application's current infrastructure and access model. C#/React/PostgreSQL is a reference option, not a required rewrite or an instruction to move this application to GCP.

## Current implementation and retained infrastructure

| Area | Observed implementation | Decision for review and maintenance |
| --- | --- | --- |
| Frontend | Static HTML/JavaScript member interface in `web/league.html` and `assets`, built by the member-site package | Supported baseline; compare targeted improvements with any proposed UI conversion |
| Backend/synchronization | Node Yahoo member API in `prototypes/yahoo-login`, plus Python importer/exporter and scheduled GitHub Actions | Keep current ownership and schedules; a language change requires benefit and compatibility evidence |
| League data | Server-encrypted archive/manual fallback and public ciphertext delivery on `login-trial-data` | Retain encrypted storage/delivery and protected history/lineage; no Cloud SQL move is required |
| Member access | Yahoo OIDC login, current-season membership checks, server-side decryption and one-hour secure sessions; shared-password access is retired | Retain Yahoo member access and equivalent security controls; no Identity Platform/Firebase migration is required |
| Hosting | Existing Vercel member site and GitHub Actions; GitHub Pages redirects to the member site | Retain these providers and concrete services; no Cloud Run move is required |

An infrastructure or billing-plan change requires a separate cost and operational case and explicit owner decision. Include current versus proposed recurring charges, free-tier limits, migration effort and recovery. A language change does not authorize changing data storage, authentication or job infrastructure. Yahoo provider authorization remains distinct from application membership checks.

## Authority, branch and privacy

- Governing source branch: `main`; `login-trial-data` is the generated ciphertext delivery branch. [Yahoo integration](../yahoo-integration.md), [member-site instructions](../../prototypes/yahoo-login/README.md) and [code review](CODE_REVIEW.md) describe the current lane. This baseline was reconciled against current source on 2026-11-25; it retains the current supported implementation and does not restore retired password access.
- Preserve custom standings, season-specific rules, provisional/current-week boundaries, seeds, consolation paths, fallback records and freshness timestamps.
- This repository is public. Never commit decrypted league data, member information, passwords, OAuth material or private information belonging to another application.
- Use synthetic fixtures for automated/browser checks. Keep source templates distinct from generated encrypted outputs.

## Review and any separately scoped replacement

1. Capture scoring, history and privacy behavior with authoritative fixtures; distinguish existing issues from new regressions.
2. Evaluate targeted fixes and refactoring first. If a language/framework change is justified, prove the affected league journeys using synthetic data and compatible contracts on the retained infrastructure.
3. Preserve Yahoo integration and authoritative scoring. For changed implementations, compare results independently and retain the last successful source on partial failures and stable identities on retries.
4. If an independently approved data or key migration is in scope, rehearse backups/restore and reconcile historical records, totals and access boundaries without placing plaintext private data in Git or CI artifacts.
5. Verify affected member access, historical seasons, playoff views and scheduled synchronization. If a producer replacement is authorized, fence the prior updater before enabling its replacement and retain a confidentiality-preserving rollback.

## Verification and status

Follow [code review and verification](CODE_REVIEW.md). Preserve `python -m unittest discover -s tests -v`, `npm run test:browser`, the synthetic preview fixture in `.github/workflows/update-yahoo.yml`, and `npm test`/`npm run build` in `prototypes/yahoo-login` with its sign-in workflow. Current CI uses Python 3.12, Node 22 and npm. Preserve the workflow's refusal to publish known plaintext data outputs.

Engineering guidance is the scope of this correction. The earlier frontend/backend conversion and Cloud SQL/Identity Platform/Cloud Run destinations are **not required or authorized by this standard**. The application maintainer continues to own the supported Python importer/exporter, static frontend and Node/Vercel member service. No infrastructure migration is approved by this record; existing runtime versions, encryption, credentials, published data and hosting are unchanged by this policy update.
