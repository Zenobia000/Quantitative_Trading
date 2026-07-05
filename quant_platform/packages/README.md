# packages/

Shared, dependency-inward libraries (ADR-R05). Domain never imports framework/DB/broker.

- `domain/` — pure logic (from `research/domain/`; import-linter-enforced pure).
- `application/` — use cases (from `research/application/`).
- `adapters/` — IO/persistence seams (from `research/adapters/` + `data/db_kernel`).
- `infrastructure/` — config/wiring (from `config/{settings,universe}` — deferred here in W5.2 because strategies/api import it module-level; `data/{db_kernel,runs_writer,parquet_writer}`).
- `contracts/` — cross-service published language (already at golden `packages/contracts/`, W1.2a).
