# Siler City Fantasy application standard adoption

Owner direction: 2026-11-24. Standard: 2026.11.1.

The [Application Architecture Charter](APPLICATION_STANDARD.md) governs new applications and deliberately replaced components. The current published site remains the baseline until a verified migration replaces it.

## Current implementation and target

| Area | Observed implementation | Approved destination |
| --- | --- | --- |
| Frontend | Static HTML/JavaScript with encrypted league snapshots | React 19, strict TypeScript, Vite 8, Tailwind 4; owned UI components |
| Backend/synchronization | Python Yahoo importer and scheduled GitHub Actions | C# / .NET 10 LTS; ASP.NET Core feature modules and appropriate managed tasks |
| League data | Encrypted files, historical snapshots and manual fallback | PostgreSQL 18 on Cloud SQL with EF Core/Npgsql; protected history and lineage |
| Member access | Browser-side unlock of encrypted snapshots | Identity Platform/Firebase Auth server sessions and equivalent league-access checks |
| Hosting | Existing GitHub Pages and Actions | Same-origin React and ASP.NET Core on Cloud Run |

Yahoo OAuth remains a provider integration distinct from member authentication. A new application identity system does not replace provider authorization requirements.

## Authority, branch and privacy

- Governing branch: `main`. [Yahoo integration](../yahoo-integration.md) describes the current operating lane until migration is accepted.
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

Preserve `python -m unittest discover -s tests -v`, `npm run test:browser` and the synthetic preview fixture in `.github/workflows/update-yahoo.yml`. Current CI uses Python 3.12, Node 22 and npm. Preserve the workflow's refusal to publish known plaintext data outputs.

Engineering policy and editor defaults are the adoption scope. Application, identity, database and synchronization migrations are **pending**. The application maintainer owns the Python/static-site migration boundary until replacement acceptance. Existing runtime versions, encryption, credentials, published data and hosting are unchanged.
