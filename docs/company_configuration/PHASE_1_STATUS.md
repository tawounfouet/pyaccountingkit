# Phase 1 - Implementation status

Date: 2026-10-29

| Gate | Status | Evidence |
|---|---|---|
| G0 - Audit/baseline | PENDING REVIEW | `evidence/L00/repository_baseline.md`; historical repository/package reconciliation still open; issue #1 |
| G1 - Domain kernel | IN PROGRESS | L01 typed VOs, `LegalEntity` aggregate and property tests; issue #2 |
| G2 - Technical foundations | IN PROGRESS / NOT APPROVED | L02-01 memory proof, L02-02 PostgreSQL proof and L02-03 delivery + denial candidate; issue #5 |

## Exact-SHA qualified checkpoints

- L01 implementation `a4d8d7e572d2d72fde1878b095ba6de4c057c173`: [CI #10](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40838129260), **82 tests** and Ruff on Python 3.11/3.12.
- L02-01 implementation `dea2cbd4c1a85ece13df663e6bb47a19cbeb6fc8`: [CI #14](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40839316434), **94 tests** and Ruff green.
- L02-02 implementation `fb207bc1570b5efb19a4bf8d34629f430cab26f2`: [PostgreSQL CI #40841545574](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40841545574) **9 DB tests** each on Python 3.11/3.12; Ruff green. Documentation head `6254a3f553b9c13bc0553a886e79dc3355227d73` passed [PG CI #40841749873](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40841749873) and [Python CI #40841750168](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40841750168).
- L02-03 candidate: Outbox delivery/lease/retry/dead-letter and opt-in durable verified-principal denial audit. **CI pending on this new increment.** See `evidence/L02_increment_03_security_outbox.md`.

## Non-claims

No G0/G1/G2 gate approved; no release; no complete PCG/IFRS/SYSCOHADA norm engine, real IAM, secure tenant-bound DB connections, C10 E2E, published configuration governance or Ledger posting. Outbox events are at-least-once, not exactly-once. PostgreSQL remains provisional pending ADRs and independent review.
