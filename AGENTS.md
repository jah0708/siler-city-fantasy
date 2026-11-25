# Repository engineering instructions

Read [the Application Architecture Charter](docs/engineering/APPLICATION_STANDARD.md) and [this application's adoption record](docs/engineering/ADOPTION.md) before implementation or architecture changes. New and replacement components follow the selected target. The current static site and Python updater remain the managed baseline until verified replacement.

Read [Yahoo integration](docs/yahoo-integration.md) before provider synchronization, privacy or publication changes. Preserve historical scoring, current-week boundaries, seeds/consolation, fallback records and freshness indicators.

This repository is public. Never commit decrypted league records, private member information, passwords, OAuth material or private information from another application. Use synthetic test data and evidence.

Preserve the existing Python privacy/scoring suite and browser checks. Do not replace working encryption or publish plaintext as an incidental standards change. Distinguish policy adoption, migration and verified hosted release.
