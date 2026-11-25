# Application Architecture Charter

Version: 2026.11.2

Effective: November 25, 2026

Status: Binding engineering principles; infrastructure preserved; software choices reviewable

## 1. Authority and purpose

Apply consistent engineering principles across separate applications. The owner's November 25 correction supersedes the earlier immutable technology-family and mandatory migration direction: languages and frameworks may change when justified; existing infrastructure should stay as it is. Each product keeps its own repository, data ownership, brand, authorization and deployment history.

Preserve the goal of common languages, frameworks and reusable contracts across applications where their retained infrastructure supports them. Compare a shared software choice before adding a divergent stack, and document justified differences. Existing differences are a review input, not automatic rewrite authorization.

Retain each existing application's actual hosting, database, identity, storage, scheduled-job and integration services as the review baseline. Preserve its current plan and cost objective. A provider name alone is not the boundary: replacing Firestore with Cloud SQL, Supabase Auth with another identity system, or a current job service with Cloud Tasks is an infrastructure change even within the same cloud.

An infrastructure migration requires a separate, concrete cost/benefit case and an explicit owner decision for that scope before provisioning or cutover. Compare retaining or improving the present setup with the proposed move; include current usage and plan, recurring baseline and growth costs, free-tier eligibility/limits, egress, backups, logging/builds, migration effort, recovery and operational burden. Distinguish measured bills, modeled estimates and unknowns. Trial credits do not prove an ongoing cost. Never infer that every service in a cloud is free because the current deployment is free. Reuse prior specific authorization; do not add confirmation steps to ordinary compatible maintenance.

Language/framework changes are permitted within the authorized task when supported by a documented problem, a simpler alternative comparison, deployment compatibility, measured or bounded cost impact and proportionate verification. Preserve consistency inside each app and reuse shared contracts/patterns where they fit. Language flexibility is not blanket authorization for a rewrite, a new permanent runtime or a service migration. If a proposed language cannot run on the existing deployment, it needs the infrastructure decision first.

## 2. Technology selection and infrastructure baseline

| Layer | Current policy |
|---|---|
| Existing backend and frontend | Keep the deployed implementation supported; review its structure and behavior directly. A different language alone is not a defect. |
| Languages and frameworks | Evidence-driven choices. C#/ASP.NET Core and strict TypeScript/React remain available reference choices; neither creates an automatic porting requirement. Use supported versions and exact lockfiles. |
| Browser contracts | Explicit runtime-validated APIs; prefer OpenAPI and generated TypeScript contracts where they fit the existing interface. Preserve compatibility. |
| HTTP conventions | Prefer same-origin APIs where the existing host supports them; retain established routes and authentication behavior during bounded refactors. Use structured, safe errors and explicit authorization. |
| Database | Preserve the current database service and source of truth. PostgreSQL is a relational option, not a requirement to replace another working store. |
| Hosting, identity, storage, jobs, secrets and observability | Retain current services and provider boundaries. Improve code and configuration within the authorized scope; service replacements require the cost case and owner decision in section 1. |
| UI system | Reuse the product's components and brand tokens; adopt accessible primitives and stricter typing when beneficial without a compulsory redesign or framework upgrade. |
| Source, build and release | Keep separate product repositories and existing working build/deployment paths. Use reproducible checks in the repository's established CI. |
| Infrastructure definitions | Keep existing definitions as the baseline. Review any authorized change against actual resources and costs; no compulsory tooling migration. |
| Tests | Use the actual stack's test tools and meaningful existing gates. Examples include xUnit for .NET, Vitest/Testing Library for React, database integration checks and Playwright for critical browser journeys. |
| Public publishing and platform code | Preserve WordPress and native/game boundaries where they serve the product. Use platform-appropriate languages. |

For a new application, select the smallest coherent stack that fits the intended existing infrastructure and cost objective. Record the choice once in its adoption record and follow it until a justified change. Reuse working service capacity only with appropriate isolation and verified quotas; do not create or combine infrastructure by assumption. Add packages only when a real feature needs them.

## 3. Application topology

Prefer a cohesive modular application per product, with clear rule and data ownership and one release lineage. Keep the existing repository and deployed topology as the baseline. Organize business capabilities into modules; do not turn every module into a service or compiled project, and do not force multiple existing stores into one database merely to conform.

Prefer serving the custom browser interface and API together when compatible with the current host. Preserve existing split deployments unless an approved change demonstrates benefit. Add a worker deployment only for a real need for separate credentials, scaling, resource limits or failure isolation, subject to the infrastructure decision rule. Use least-privilege identities for each existing execution mode.

Keep directories for feature modules, integration adapters, persistence/migrations, job handlers, frontend, tests, and deployment definitions. Begin with a small number of projects; add boundaries when they isolate a real responsibility. Do not create a generic enterprise scaffold.

Do not add microservices, Kubernetes, a service mesh, an additional cloud or frontend host, Redis, GraphQL, event sourcing, CQRS, MediatR, AutoMapper, or generic repositories as defaults. A new layer must own a real rule or isolate a real dependency. Existing infrastructure is not a review failure merely because it differs from this default. Where EF Core is used, avoid wrappers that repeat its CRUD operations.

Share libraries only for a stable contract used by multiple actual consumers. Do not create a universal business platform or combine product databases speculatively. Preserve separate credentials, permissions, migrations and recovery ownership. Proposed shared infrastructure must satisfy the cost and owner-decision rule.

## 4. Business rules and component communication

Keep authoritative calculations, permissions, scoring, state transitions, publication decisions, and integration commands on the server. HTTP endpoints, background handlers, and MCP tools must invoke the same application use cases. Do not create a parallel business backend for AI tools.

Let the frontend display authoritative state and submit commands. Client validation improves feedback but does not replace server validation. Do not maintain independent financial or scoring formulas in TypeScript.

Prefer generating browser types/clients from the authoritative OpenAPI definition for custom HTTP APIs. Retain a coherent equivalent contract where the platform already provides one. Keep generated files reproducible and check for drift. Use explicit request/response models rather than exposing persistence entities. Validate incoming data at runtime, reject unexpected fields where the contract requires it, and version breaking changes.

For every changed boundary specify:

- The authoritative owner, identifiers, and mappings to external systems.
- Field semantics, required/optional/null behavior, units, dates, and currencies.
- Authentication and object/action-level authorization.
- Expected revision, error codes, retry eligibility, timeouts, and idempotency key.
- Consumer compatibility, data sensitivity, and verification of the assembled path.

Use Problem Details responses with safe messages and a trace ID. Return explicit validation, authentication, authorization, missing-record, version-conflict, and rate-limit outcomes. Preserve public contracts during migration; do not convert a conflict into a silent overwrite.

## 5. Data and financial integrity

Use the existing database's transaction, concurrency, uniqueness and validation capabilities to protect invariants. For PostgreSQL, enforce appropriate foreign keys, uniqueness and check constraints. For other stores, implement and verify equivalent required behavior with supported mechanisms. Each business module owns its records; cross-product writes use explicit application operations, never unrestricted access to another product's records.

Use exact decimal arithmetic or documented integer minor units for money and financial rates in the chosen runtime and store. In C#/PostgreSQL, use decimal and explicit numeric precision/scale. Carry currency and rounding rules. Serialize precision-sensitive amounts as documented decimal strings or integer minor units; do not rely on JavaScript floating-point values as financial authority.

Store timestamps as UTC instants and preserve the relevant business timezone and local date when a workflow needs them. Make season, week, accounting cutoff, schedule and DST semantics explicit. Preserve immutable source snapshots, calculation/rule versions, and material historical results.

QuickBooks owns issued accounting records and recorded payments; WordPress owns actual saved/publication state. Local app records own intended workflow and retain remote IDs, revisions, observation times, and reconciliation status. Treat a replica or cached observation as such.

Run migrations as a controlled release step, not from every autoscaling web instance. Test schema changes against representative data. Use expand/contract changes for compatibility and retain a verified recovery path. Never migrate by silently discarding unknown fields or resetting IDs.

## 6. Jobs, schedules and external effects

Do not run critical work in an in-memory queue or an unattended background loop inside a request container. Persist intent and progress.

When a committed business change requires durable external work, persist its intent atomically with the business change using the current store's supported transaction mechanism. Use the existing delivery/scheduling facilities and a bounded recovery path. A queue transports work; the application ledger owns its business state. Add a queue or outbox only where the failure semantics require it, and apply the infrastructure decision rule to a new service.

Record operation ID, actor/service identity, object ID, expected version, idempotency key, payload hash, attempts, timestamps, external identifier, progress, and observed outcome. Apply bounded leases/concurrency and retry transient errors with backoff. Preserve terminal failure and ambiguous-outcome states with a safe recovery action.

Assume duplicate delivery and possible reordering. Do not claim exactly-once remote execution. Use stable identities, unique constraints, provider idempotency where available, and downstream reconciliation. After an uncertain create/publish/payment response, read the destination before creating again.

Keep one logical producer for each scheduled occurrence. An application scheduler, GitHub workflow and ChatGPT automation must not independently create the same business item. Coordinate or retire the previous producer during adoption.

Checkpoint long work within the existing execution facilities. Verify current platform time/concurrency limits before implementation; do not freeze a remembered limit into code. A new batch/job service needs the infrastructure decision even if it shares the current provider.

## 7. Identity, security and privacy

Preserve the existing identity provider and enforce product permissions and memberships at the authoritative server or platform access boundary. Use secure HttpOnly cookies where appropriate to the existing session model, with SameSite and CSRF controls for cookie-authenticated operations. Protect token-based flows appropriately. Verify session expiry, refresh, logout, revocation and access after relevant changes. A common code standard does not require moving user identities.

Keep human sessions, cloud service identity, provider OAuth grants, and scoped tool/MCP identity distinct. Common application sign-in does not remove WordPress, QuickBooks, Yahoo or OpenAI authorization requirements. Keep one coordinated refresh path per external connection and expose reauthentication only when required.

Use narrowly scoped service identities and the current approved secret-storage mechanism. Do not expose integration secrets, service credentials, refresh tokens or raw private data to the browser, logs, repository, prompts, or public CI artifacts. Test both permitted and denied access. Keep private administration out of public search and protect it with authorization rather than robots directives.

An existing private application remains private. The shared standard does not authorize adding multi-tenancy, customer portals, external users, or additional data sharing.

## 8. Interface, design and public search

Keep a coherent frontend within each application and reuse interaction patterns while preserving each product's approved logo, colors, tone, and useful detail. Use tables for comparison, compact legible grouping, predictable navigation, clear statuses, accessible controls, and useful drill-down.

Use shared primitives and design tokens rather than copied CSS and independently invented dashboards. Inspect rendered desktop/mobile states and actual interactions. Verify loading, empty, error, stale and permission states, and show the cause and remedy behind operational status labels.

Keep public marketing/content in the WordPress boundary. Preserve established URLs and publication IDs; use deliberate redirects for changes. Verify discoverability, canonical/sitemap/robots behavior, truthful structured data, media, useful content and actual analytics. Do not expose private app routes for SEO or treat a plugin score as a business outcome.

## 9. Verification and releases

Use exact dependency lockfiles, supported patched runtimes, reproducible builds, secret-safe configuration and versioned deployment definitions. Run the changed application's applicable formatting/lint, compilation/type checks, contract checks, focused domain tests, database/authorization checks and relevant browser journeys. Do not add a second toolchain just to match a reference stack.

Test important failure paths: duplicate request, timeout after remote success, crash after database commit, worker interruption, expired credentials, conflicting edit and stale frontend/API contract. Test financial/history invariants with source-derived fixtures, not invented expected values that copy the implementation.

Record the built/tested artifact, deployed revision, environment, migration result and observed affected workflow. Separate implemented, tested, deployed and externally verified states. A successful build is not release evidence.

Use independent QA for consequential changes. Add a regression safeguard for recurring failures when meaningful. Do not weaken existing checks or replace tests merely to introduce the new standard.

## 10. Expert operating model and efficiency

Use one delivery orchestrator with focused architecture/integration, backend, data/domain, frontend/design, security, reliability, editorial, SEO, efficiency and QA expertise. Activate only relevant roles. Set shared contracts before parallel implementation and assign each editable artifact one owner.

The orchestrator integrates contributions and owns the final user outcome. Specialists must return actual changes, evidence, assumptions, unresolved issues and precise handoff actions. An independent reviewer challenges both correctness and unnecessary complexity.

Keep deterministic queues, schedules, calculations and reconciliation in application code/data systems. Skills and temporary subagents guide work; they are not always-running production staff.

Measure relevant latency, database work, job delay/retry rate, memory, model cost, bundle size and operator effort before claiming improvement. Reject pass-through abstraction, speculative generality, duplicate state owners and unnecessary deployments. Do not use arbitrary line-count or coverage targets as substitutes for review.

## 11. Platform-specific boundaries

| Boundary | Implementation guidance |
|---|---|
| WordPress | PHP/theme/plugin code only where the CMS requires it; application workflow stays behind the shared API/integration contract |
| WoW addon | Lua for the supported game client; versioned local exchange format; respect actual platform capabilities |
| Windows native companion | Use the existing supported native implementation and packaging; C#/.NET and required PowerShell remain suitable options. Preserve separately authorized native migration work and verify it. |
| Frontend build and tooling | Use the application's established tools and reproducible lockfiles; avoid an additional backend or runtime without a concrete need. |
| Existing backends, adapters and scripts | Supported Python, JavaScript/TypeScript and provider-specific implementations remain valid baselines. Replacement requires evidence and authorized scope; maintenance is not a promise to rewrite. |
| Skill and analysis utilities | Language appropriate to the tool/runtime, such as a Decimal-based Python analysis utility; no production application architectural exception is implied |

A local addon/desktop app does not need a cloud database, web identity or a cloud service merely to conform. A public website does not need a custom application if WordPress serves the requirement. Document each boundary's purpose and owner; require an exit condition only when a migration is actually selected.

## 12. Adoption and maintenance

Each application must carry an adoption record: current stack and infrastructure, governing branch, source-of-truth document, preserved invariants, current verify commands, accepted software choices, and any separately authorized migration with its cost decision and evidence. Label unselected options as proposals, not pending obligations.

Apply the engineering principles to new and existing applications. Begin reviews by classifying what to keep, repair, refactor, remove or investigate. A rewrite must earn its place through evidence. When a bounded implementation migration is selected and authorized, define the operation/contract and source of truth, maintain one authoritative writer, reconcile IDs, counts, financial totals, history, permissions and remote effects, and verify rollback before retiring the old path.

Do not equate a standards document with a completed migration. Do not rewrite every app, change live authentication, or provision billable infrastructure as an incidental documentation change. Implement the authorized migration scope as concrete work and record its actual status.

Maintain supported patches and compatible version upgrades with proportionate verification. Record justified language/framework changes and their integration/cost effects within the authorized scope; do not continually reopen settled choices for fashion or a microbenchmark. Preserve existing infrastructure unless the owner chooses a concrete, priced change. The common foundation is consistent engineering and operating discipline, with deliberate software choices that fit the app.

## Primary implementation references

Refresh version-specific guidance at implementation time:

- .NET support: https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core
- ASP.NET Core OpenAPI: https://learn.microsoft.com/en-us/aspnet/core/fundamentals/openapi/aspnetcore-openapi?view=aspnetcore-10.0
- ASP.NET Core validation: https://learn.microsoft.com/en-us/aspnet/core/release-notes/aspnetcore-10.0?view=aspnetcore-10.0
- React versions: https://react.dev/versions
- Vite 8: https://vite.dev/blog/announcing-vite8
- PostgreSQL numeric types: https://www.postgresql.org/docs/current/datatype-numeric.html
- Cloud SQL versions: https://docs.cloud.google.com/sql/docs/postgres/db-versions
- .NET on Cloud Run: https://docs.cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-dotnet-service
- Cloud Tasks and Cloud Run: https://docs.cloud.google.com/run/docs/triggering/using-tasks
- Cloud Tasks delivery behavior: https://docs.cloud.google.com/tasks/docs/common-pitfalls
- Firebase server sessions: https://firebase.google.com/docs/auth/admin/manage-cookies
