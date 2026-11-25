# Application Architecture Charter

Version: 2026.11.1  
Effective: November 24, 2026  
Status: Binding portfolio foundation

## 1. Authority and purpose

Use this foundation for new custom applications and for deliberately migrated portions of existing applications. The owner has selected a consistent long-term architecture after independent architecture and efficiency review. This is a technology-family decision, not a suggestion to reconsider at the start of each task.

Only explicit owner direction may change a core language, framework family, database family, cloud, identity provider, job system, or the scope of a platform exception. Agents may propose a concrete case, but may not substitute their preferred stack. Security patches and validated supported-version upgrades within the selected families are required maintenance. Exact build dependencies must remain reproducible.

A shared foundation does not combine separate products, private records, brand identities, or authorizations. Apply a common architecture to distinct applications with explicit data and integration boundaries.

## 2. Fixed technology choices

| Layer | Standard |
|---|---|
| Authoritative application language | C# on supported .NET LTS; initial baseline .NET 10 |
| API and application framework | ASP.NET Core; feature-oriented Minimal API endpoints and application use cases |
| Browser language | TypeScript with strict checking |
| Custom frontend | React 19, Vite 8, React Router for application routing |
| UI system | Tailwind CSS 4; accessible Radix primitives behind owned reusable components and brand-specific design tokens |
| Relational application data | PostgreSQL; initial managed baseline PostgreSQL 18 on Cloud SQL |
| Data access | Entity Framework Core with Npgsql; versioned migrations and explicit relational constraints |
| API contracts | ASP.NET Core OpenAPI; generated TypeScript client/types using openapi-typescript/openapi-fetch |
| HTTP conventions | Same-origin JSON APIs under /api/v1; Problem Details errors and explicit authorization |
| User identity | Google Cloud Identity Platform / Firebase Authentication; server-managed secure sessions |
| API and web hosting | Google Cloud Run; serve built React assets and API from the same origin |
| Background delivery | Cloud Tasks; durable application job ledger and transactional outbox where a database change causes external work |
| Recurring triggers | Cloud Scheduler; one logical producer per workflow |
| Long batch work | Cloud Run Jobs when work exceeds an HTTP task's practical execution limits |
| File/object storage | Google Cloud Storage; metadata and ownership in PostgreSQL |
| Secrets and service identities | Secret Manager and scoped Google Cloud service accounts |
| Logs, metrics, traces | Cloud Logging/Monitoring with OpenTelemetry-compatible instrumentation |
| Source and CI | GitHub; GitHub Actions for reproducible build/test/release checks |
| Infrastructure definitions | Versioned Terraform for new/migrated infrastructure; plans reviewed against actual state |
| Dependency management | NuGet lockfiles for .NET; npm and committed lockfiles for frontend/tooling |
| Tests for new application code | xUnit for backend; PostgreSQL integration tests with Testcontainers; Vitest/Testing Library for frontend; Playwright for critical user journeys |
| Public publishing | WordPress within the explicit CMS boundary; do not add another application backend through the CMS |

Use packages only when the feature needs them. A fixed selection removes repeated framework choice; it does not require every application to instantiate every service or dependency.

## 3. Application topology

Use one modular monolith per product: one repository, a cohesive application, an authoritative operational database, and one release lineage. Organize business capabilities into modules; do not turn every module into a service or compiled project.

Serve the custom browser interface and API together. Start with one web deployment. Add a worker deployment from the same release artifact when background work needs separate credentials, scaling, resource limits, or failure isolation. Use separate configuration and least-privilege identities for web and worker modes.

Keep directories for feature modules, integration adapters, persistence/migrations, job handlers, frontend, tests, and deployment definitions. Begin with a small number of projects; add boundaries when they isolate a real responsibility. Do not create a generic enterprise scaffold.

Do not add microservices, Kubernetes, a service mesh, a second cloud, a separate frontend host, Redis, GraphQL, event sourcing, CQRS, MediatR, AutoMapper, or generic repositories as defaults. A new layer must own a real rule or isolate a real dependency. EF Core does not need a wrapper that repeats its CRUD operations.

Share libraries only for a stable contract used by multiple actual consumers. Do not create a universal business platform or combine product databases speculatively. Small products may share managed database infrastructure while retaining separate databases, roles, credentials, migrations, and backup/recovery ownership.

## 4. Business rules and component communication

Keep authoritative calculations, permissions, scoring, state transitions, publication decisions, and integration commands on the server. HTTP endpoints, background handlers, and MCP tools must invoke the same application use cases. Do not create a parallel business backend for AI tools.

Let the frontend display authoritative state and submit commands. Client validation improves feedback but does not replace server validation. Do not maintain independent financial or scoring formulas in TypeScript.

Generate the browser contract from the backend OpenAPI definition. Keep generated files reproducible and check for drift. Use explicit request/response DTOs rather than exposing persistence entities. Validate incoming data at runtime, reject unexpected fields where the contract requires it, and version breaking changes.

For every changed boundary specify:

- The authoritative owner, identifiers, and mappings to external systems.
- Field semantics, required/optional/null behavior, units, dates, and currencies.
- Authentication and object/action-level authorization.
- Expected revision, error codes, retry eligibility, timeouts, and idempotency key.
- Consumer compatibility, data sensitivity, and verification of the assembled path.

Use Problem Details responses with safe messages and a trace ID. Return explicit validation, authentication, authorization, missing-record, version-conflict, and rate-limit outcomes. Preserve public contracts during migration; do not convert a conflict into a silent overwrite.

## 5. Data and financial integrity

Use PostgreSQL transactions, foreign keys, uniqueness constraints, and check constraints for invariants that belong in the database. Each business module owns its records; cross-product writes use explicit application operations, never unrestricted access to another product's tables.

Use C# decimal and explicit PostgreSQL numeric precision/scale for money and financial rates. Carry currency and rounding rules. Serialize precision-sensitive amounts as documented decimal strings or integer minor units; do not rely on JavaScript floating-point values as financial authority.

Store timestamps as UTC instants and preserve the relevant business timezone and local date when a workflow needs them. Make season, week, accounting cutoff, schedule and DST semantics explicit. Preserve immutable source snapshots, calculation/rule versions, and material historical results.

QuickBooks owns issued accounting records and recorded payments; WordPress owns actual saved/publication state. Local app records own intended workflow and retain remote IDs, revisions, observation times, and reconciliation status. Treat a replica or cached observation as such.

Run migrations as a controlled release step, not from every autoscaling web instance. Test schema changes against representative data. Use expand/contract changes for compatibility and retain a verified recovery path. Never migrate by silently discarding unknown fields or resetting IDs.

## 6. Jobs, schedules and external effects

Do not run critical work in an in-memory queue or an unattended background loop inside a request container. Persist intent and progress.

When a committed business change requires external work, commit its job/outbox record in the same PostgreSQL transaction. A dispatcher delivers it through Cloud Tasks; a bounded scheduled sweep repairs interrupted dispatch. The managed queue transports work; the application ledger owns its business state.

Record operation ID, actor/service identity, object ID, expected version, idempotency key, payload hash, attempts, timestamps, external identifier, progress, and observed outcome. Apply bounded leases/concurrency and retry transient errors with backoff. Preserve terminal failure and ambiguous-outcome states with a safe recovery action.

Assume duplicate delivery and possible reordering. Do not claim exactly-once remote execution. Use stable identities, unique constraints, provider idempotency where available, and downstream reconciliation. After an uncertain create/publish/payment response, read the destination before creating again.

Keep one logical producer for each scheduled occurrence. An application scheduler, GitHub workflow and ChatGPT automation must not independently create the same business item. Coordinate or retire the previous producer during adoption.

Checkpoint long work and use Cloud Run Jobs when appropriate. Verify current platform time/concurrency limits before implementation; do not freeze a remembered limit into code.

## 7. Identity, security and privacy

Use Identity Platform/Firebase Authentication for human identity, with product permissions and memberships enforced on the server. Use secure HttpOnly sessions, appropriate SameSite settings and CSRF protection. Verify session expiry, refresh, logout, revocation and access after deployment.

Keep human sessions, cloud service identity, provider OAuth grants, and scoped tool/MCP identity distinct. Common application sign-in does not remove WordPress, QuickBooks, Yahoo or OpenAI authorization requirements. Keep one coordinated refresh path per external connection and expose reauthentication only when required.

Use narrowly scoped service identities and Secret Manager. Do not expose integration secrets, service credentials, refresh tokens or raw private data to the browser, logs, repository, prompts, or public CI artifacts. Test both permitted and denied access. Keep private administration out of public search and protect it with authorization rather than robots directives.

An existing private application remains private. The shared standard does not authorize adding multi-tenancy, customer portals, external users, or additional data sharing.

## 8. Interface, design and public search

Keep one frontend implementation family and reusable interaction patterns while preserving each product's approved logo, colors, tone, and useful detail. Use tables for comparison, compact legible grouping, predictable navigation, clear statuses, accessible controls, and useful drill-down.

Use shared primitives and design tokens rather than copied CSS and independently invented dashboards. Inspect rendered desktop/mobile states and actual interactions. Verify loading, empty, error, stale and permission states, and show the cause and remedy behind operational status labels.

Keep public marketing/content in the WordPress boundary. Preserve established URLs and publication IDs; use deliberate redirects for changes. Verify discoverability, canonical/sitemap/robots behavior, truthful structured data, media, useful content and actual analytics. Do not expose private app routes for SEO or treat a plugin score as a business outcome.

## 9. Verification and releases

Use exact dependency lockfiles, supported patched runtimes, reproducible builds, secret-safe configuration and versioned infrastructure. Check formatting/lint, C# and TypeScript compilation, generated contract drift, focused domain tests, database/authorization tests and relevant browser journeys.

Test important failure paths: duplicate request, timeout after remote success, crash after database commit, worker interruption, expired credentials, conflicting edit and stale frontend/API contract. Test financial/history invariants with source-derived fixtures, not invented expected values that copy the implementation.

Record the built/tested artifact, deployed revision, environment, migration result and observed affected workflow. Separate implemented, tested, deployed and externally verified states. A successful build is not release evidence.

Use independent QA for consequential changes. Add a regression safeguard for recurring failures when meaningful. Do not weaken existing checks or replace tests merely to introduce the new standard.

## 10. Expert operating model and efficiency

Use one delivery orchestrator with focused architecture/integration, backend, data/domain, frontend/design, security, reliability, editorial, SEO, efficiency and QA expertise. Activate only relevant roles. Set shared contracts before parallel implementation and assign each editable artifact one owner.

The orchestrator integrates contributions and owns the final user outcome. Specialists must return actual changes, evidence, assumptions, unresolved issues and precise handoff actions. An independent reviewer challenges both correctness and unnecessary complexity.

Keep deterministic queues, schedules, calculations and reconciliation in application code/data systems. Skills and temporary subagents guide work; they are not always-running production staff.

Measure relevant latency, database work, job delay/retry rate, memory, model cost, bundle size and operator effort before claiming improvement. Reject pass-through abstraction, speculative generality, duplicate state owners and unnecessary deployments. Do not use arbitrary line-count or coverage targets as substitutes for review.

## 11. Bounded platform exceptions

| Boundary | Permitted technology and constraint |
|---|---|
| WordPress | PHP/theme/plugin code only where the CMS requires it; application workflow stays behind the shared API/integration contract |
| WoW addon | Lua for the supported game client; versioned local exchange format; respect actual platform capabilities |
| Windows native companion | C#/.NET for native implementation; PowerShell for installation/build where required; existing native compatibility runtimes remain documented until verified migration |
| Frontend build and tooling | Node/npm and TypeScript/JavaScript build configuration; this does not authorize a separate Node application backend |
| Existing adapters and scripts | Existing Python/JavaScript or provider-specific adapters may be maintained inside a named migration boundary until a verified replacement; no new general-purpose backend family |
| Skill and analysis utilities | Language appropriate to the tool/runtime, such as a Decimal-based Python analysis utility; no production application architectural exception is implied |

A local addon/desktop app does not need Cloud SQL, web identity or a cloud service just to conform. A public website does not need a custom application if WordPress serves the requirement. Each exception has an exact purpose, owner and exit condition where transitional.

## 12. Adoption and maintenance

Each application must carry an adoption record: current stack, target, governing branch, source-of-truth document, preserved invariants, current verify commands, bounded exceptions, migration milestones and completed evidence.

Apply the new foundation to new applications. For existing apps, preserve behavior while moving complete vertical capabilities through verified boundaries. First define the operation/contract and source of truth, then migrate implementation and data with one authoritative writer. Reconcile IDs, counts, financial totals, status/history, permissions and remote side effects; verify rollback. Retire superseded jobs/storage/code once the replacement is proven.

Do not equate a standards document with a completed migration. Do not rewrite every app, change live authentication, or provision billable infrastructure as an incidental documentation change. Implement the authorized migration scope as concrete work and record its actual status.

Keep architecture families fixed. Maintain supported patches and compatible version upgrades with tests; plan major version upgrades within the same family using a compatibility review. Any proposed new family or broadened exception requires explicit owner direction. Agents cannot treat a local preference or a new trend as permission to change the foundation.

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
