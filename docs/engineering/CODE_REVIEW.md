# Siler City Fantasy code review and verification

Read [AGENTS.md](../../AGENTS.md), [the charter](APPLICATION_STANDARD.md), [adoption](ADOPTION.md), [Yahoo integration](../yahoo-integration.md) and [the member site](../../prototypes/yahoo-login/README.md). This procedure applies to source changes through bounded PRs to `main`; the `login-trial-data` branch is a generated ciphertext delivery surface, not another source-development branch.

These instructions do not enable an automatic review setting or install enforceable merge protections. Check the actual repository configuration and run results before claiming either exists.

## Scope and coordination

Record the base/head commits, intended result, affected paths, acceptance criteria and preserved behavior. Inspect current source and unrelated work before editing. Define changed boundaries before parallel implementation: season/league/week/team identity, completed versus provisional scores, snapshot freshness, encryption/key ownership, membership/session authorization, retries and source/publication versions. Assign one writer per artifact and one delivery owner.

Use domain/data expertise for historical scoring, cutoffs and bracket changes; security/integration expertise for Yahoo login, secret rotation, encryption and export; interface expertise for readable standings, side-by-side matchups, playoff detail and mobile states. An efficiency reviewer challenges redundant calculations, state copies, requests, services and dependencies. Public search work must not expose private member routes or records for SEO. Activate only roles relevant to the change.

For consequential work, an independent QA reviewer checks actual source, fixtures and observed results, not only the implementer's summary. Repository instructions carry the durable requirements; the review runner need not have the owner's personal ChatGPT skills.

An initial codebase audit is separate from PR review: pin a revision, trace importer/archive/export/member API/browser paths, report covered and unexamined areas, and rank evidence-backed fixes. Do not treat a clean PR review as certification of all existing code or create a giant artificial diff to obtain an audit.

## Architecture and infrastructure decisions

Review the code against demonstrated user outcomes, security, maintainability, contracts and operating cost. A language/framework change needs a documented benefit, compatible deployment and focused verification; a difference from the earlier C#/React/PostgreSQL reference architecture is not itself a defect. Preserve the current providers and concrete services listed in [adoption](ADOPTION.md). Before an infrastructure or billing-plan migration, compare the current setup with the proposed one, including recurring costs, free-tier limits, migration effort and recovery, and obtain the owner's explicit decision. This also applies to a service substitution within one provider. The review itself does not authorize a rewrite or migration.

## Current verification commands

Use the current [root package](../../package.json), [member-site package](../../prototypes/yahoo-login/package.json) and workflows as command authority. The checked-in baseline uses Python 3.12 and Node 22 in CI.

| Change | Existing verification |
| --- | --- |
| Import, archive, encryption, historical scoring or fallback | From the repository root: install `cryptography==46.0.4` in the test environment, then `python -m unittest discover -s tests -v`. Use synthetic source fixtures and never print private decrypted records. |
| Yahoo member authentication, API or build | From `prototypes/yahoo-login`: `npm ci`, `npm test`, then `npm run build`. Include allowed/denied membership, season, expiry, callback and sign-out cases as applicable. |
| League interface | From root: `npm ci`, install Playwright Chromium, run `python tests/preview_fixture.py`, serve `/tmp/scfl-preview` on port 8765 and create `test-results`, then `npm run test:browser`. Follow the workflow's server setup rather than exercising live private data. |
| Member-site browser/auth interface | Build the member site, serve its `public` directory on 8767 and the synthetic preview on 8765, then from root run `node prototypes/yahoo-login/tests/browser.cjs` and `npm run test:browser`, as in the sign-in workflow. |
| Documentation-only | Verify instructions against current scripts/workflows and check relative links and contradictions. Record checks skipped by path filters as not run, never passed. |

The existing [update workflow](../../.github/workflows/update-yahoo.yml) contains `Unit tests and privacy checks`; [the sign-in workflow](../../.github/workflows/yahoo-login-prototype.yml) contains the `prototype` job. Both use path filters. Their absence on a docs-only PR is not evidence that runtime checks ran. Keep existing coverage when changing implementations; do not introduce another test framework to mirror a documentation change.

## Findings and merge evidence

Each finding states severity, exact source location, triggering condition, expected/actual result, impact, confidence and smallest safe correction. Distinguish a reproduced defect from an uncertain concern and existing debt from new regressions. Leave formatting and mechanical checks to the existing tools. Do not use arbitrary file-length or coverage targets, or demand a rewrite solely because the supported current implementation differs from a reference stack.

Resolve material findings within the authorized scope, rerun the affected checks and review the changed revision. Record any deferred issue and its impact. Verify applicable required CI and repository protections on the exact head being merged; AI review and written rules are not hard enforcement. A silent bot or reaction is not proof of full coverage.

## Release and synchronized-data evidence

Source merge, Vercel deployment, importer success, ciphertext export and successful member access are separate states. Record the source/deployed revision, target environment, relevant job and snapshot observation time, and privacy-safe behavior evidence. The update workflow can change encrypted source records and the export workflow can update `login-trial-data`; do not start a live synchronization merely to test code-review instructions.

Verify the existing release path and affected browser/API behavior when a deployment is in scope. For data or credential migrations, reconcile IDs, history, completed-week results, access boundaries and recoverability before retiring old writers. Do not expose plaintext in logs, screenshots, PR descriptions or public artifacts. Preserve historical evidence without presenting old validation as proof of a new revision.
