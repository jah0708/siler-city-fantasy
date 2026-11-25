# Siler City Fantasy engineering instructions

## Authority and current baseline

Read [the Application Architecture Charter](docs/engineering/APPLICATION_STANDARD.md), [adoption](docs/engineering/ADOPTION.md) and [code review and verification](docs/engineering/CODE_REVIEW.md) before implementation or architecture changes. New and replacement components follow the fixed target; documented existing components remain supported migration boundaries.

Read [Yahoo integration](docs/yahoo-integration.md) and [the member-site instructions](prototypes/yahoo-login/README.md) before provider, sign-in, data or publication work. The current member site uses Yahoo sign-in and server-side access checks in `prototypes/yahoo-login` on Vercel; the old GitHub Pages address redirects there. Python/GitHub Actions retain the scheduled importer and encrypted archive/export. Historical shared-password instructions are not the active access model.

## Delivery and review

Use a bounded branch and PR against `main`. Preserve unrelated work and compare the current remote revision before writing. Define affected data/API contracts, expected behavior and acceptance criteria; use one delivery owner and one writer per artifact. Activate relevant domain, security, interface and efficiency expertise, then independent QA for consequential work. These responsibilities apply without requiring personal ChatGPT skills in the review environment.

Preserve the existing Python privacy/scoring, Yahoo-member-service and browser suites. Follow the commands and environment limits in [CODE_REVIEW.md](docs/engineering/CODE_REVIEW.md); use synthetic fixtures. Fix material findings and recheck the actual proposed revision. Distinguish source changes, passing checks, deployed code, refreshed ciphertext and observed member behavior.

## Code Review Rules

- Protect private league data in this public repository. Reject plaintext member records, secrets or private artifacts and any path that returns decrypted records without a valid session scoped to verified membership in the configured season-specific Yahoo league. Preserve PKCE/state/nonce/signature validation, cookie/origin protections and private response caching. Safe migrations maintain equivalent access controls and key recovery; they do not restore the retired shared-password fallback.
- Preserve authoritative historical scoring, season-specific rules, completed-week cutoffs, provisional results, seeds/consolation and fallback lineage. Flag invented history, live values presented as settled, or UI calculations that diverge from the authoritative result. Require source-backed expected values and the affected regression checks.
- Preserve the last valid complete archive on partial provider failures and keep archive, token-chain and delivery-key ownership distinct. Avoid duplicate import/export producers, unsafe secret rotation and plaintext publication. Challenge extra services, state copies or dependencies with a concrete operational need; retain approved maintenance exceptions rather than forcing an unrelated migration.
