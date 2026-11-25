# Siler City Fantasy application standard adoption

Owner direction: 2026-11-24. Standard: 2026.11.1.

The [Application Architecture Charter](APPLICATION_STANDARD.md) governs new applications and deliberately replaced components. The current published site remains the baseline until a verified migration replaces it.

## Current implementation and target

| Area | Observed implementation | Approved destination |
| --- | --- | --- |
| Frontend | Static HTML/JavaScript member interface in `web/league.html` and `assets`, built by the member-site package | React 19, strict TypeScript, Vite 8, Tailwind 4; owned UI components |
| Backend/synchronization | Node Yahoo member API in `prototypes/yahoo-login`, plus Python importer/exporter and scheduled GitHub Actions | C# / .NET 10 LTS; ASP.NET Core feature modules and appropriate managed tasks |
| League data | Server-encrypted archive/manual fallback and public ciphertext delivery on `login-trial-data` | PostgreSQL 18 on Cloud SQL with EF Core/Npgsql; protected history and lineage |
| Member access | Yahoo OIDC login, current-season membership checks, server-side decryption and one-hour secure sessions; shared-password access is retired | Identity Platform/Firebase Auth server sessions and equivalent league-access checks |
| Hosting | Existing Vercel member site and GitHub Actions; GitHub Pages redirects to the member site | Same-origin React and ASP.NET Core on Cloud Run |

Yahoo OAuth remains a provider integration distinct from member authentication. A new application identity system does not replace provider authorization requirements.

## Authority, branch and privacy

- Governing source branch: `main`; `login-trial-data` is the generated ciphertext delivery branch. [Yahoo integration](../yahoo-integration.md), [member-site instructions](../../prototypes/yahoo-login/README.md) and [code review](CODE_REVIEW.md) describe the current lane. This baseline was reconciled against current source on 2026-11-25; it is not a return to retired password access or approval for another permanent stack.
- Preserve custom standings, season-specific rules, provisional/current-week boundaries, seeds, consolation paths, fallback records and freshness timestamps.
- This repository is public. Never commit decrypted league data, member information, passwords, OAuth material or private information belonging to another application.
- Use synthetic fixtures for automated/browser checks. Keep source templates distinct from generated encrypted outputs.

## Migration checkpoints

1. Capture scoring, history and privacy behavior with authoritative fixtures; distinguish existing issues from migration regressions.
2. Build the replacement frontend and ASP.NET Core host against synthetic data, using generated OpenAPI clients and real league journeys.
3. Port Yahoo integration and authoritative scoring. Compare results independently; preserve the last successful source on partial failures and stable identities on retries.
4. Rehearse protected-data migration, backups and restore. Reconcile historical records, totals and access boundaries without placing plaintext private data in Git or CI artifacts.
5. Verify member access, historical seasons, full playoff views and scheduled synchronization. Fence the prior updater before enabling its replacement and retain a confidentiality-preserving rollback.

## Verification and status

Follow [code review and verification](CODE_REVIEW.md). Preserve `python -m unittest discover -s tests -v`, `npm run test:browser`, the synthetic preview fixture in `.github/workflows/update-yahoo.yml`, and `npm test`/`npm run build` in `prototypes/yahoo-login` with its sign-in workflow. Current CI uses Python 3.12, Node 22 and npm. Preserve the workflow's refusal to publish known plaintext data outputs.

Engineering policy and editor defaults are the adoption scope. Application, identity, database and synchronization migrations are **pending**. The application maintainer owns the Python importer/exporter, static frontend and Node/Vercel member-service migration boundaries until replacement acceptance. Current Yahoo member access must remain equivalent until the replacement identity and authorization path is verified. Existing runtime versions, encryption, credentials, published data and hosting are unchanged.
