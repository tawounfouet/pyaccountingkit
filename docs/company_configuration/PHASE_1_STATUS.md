# Phase 1 - Implementation status

Date: 2026-10-29

| Gate | Status | Evidence |
|---|---|---|
| G0 - Audit/baseline | PENDING REVIEW | `evidence/L00/repository_baseline.md`; historical repository/package reconciliation still open; issue #1 |
| G1 - Domain kernel | IN PROGRESS | L01 typed VOs, `LegalEntity` aggregate and property tests; issue #2 |
| G2 - Technical foundations | IN PROGRESS / NOT APPROVED | L02-01 memory, L02-02 PostgreSQL, L02-03 Outbox/denial, L02-04 Inbox candidate; issue #5 |

## Previously verified exact-SHA checkpoints

- L01 `a4d8d7e572d2d72fde1878b095ba6de4c057c173`: [CI #10](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40838129260), 82 tests and Ruff on Python 3.11/3.12.
- L02-01 `dea2cbd4c1a85ece13df663e6bb47a19cbeb6fc8`: [CI #14](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40839316434), 94 tests and Ruff green.
- L02-02 `fb207bc1570b5efb19a4bf8d34629f430cab26f2`: [PostgreSQL CI #40841545574](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40841545574), 9 DB tests per Python version; Ruff green.
- L02-03 `13c6f7b3af823d9f0a5db38ba1834001f306dc47`: [PostgreSQL CI #40844094545](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40844094545), 17 DB tests per version; [Python CI #40844094557](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40844094557), 99 passed + 2 skipped per version; Ruff green. Documentation head `816dbec99edbc84426f509b7e67436b3a832f0a6` passed two workflows.

## Current candidate

- L02-04: PostgreSQL Inbox, deduplication per producer/event identity, single transaction with an illustrative read-model effect, concurrent replay tests, malicious replay refusal, limited SQL role and **explicit negative evidence that session-tenant spoofing remains unresolved**.
- **CI evidence pending on L02-04 exact SHA.** See `evidence/L02_increment_04_transactional_inbox.md`.

## Non-claims

G0/G1/G2 are **not signed off**. No stable release, real IAM, independently secure tenant-bound SQL connections, C10 contract E2E, authoritative published configuration governance, standardized norm engine, or Ledger posting. Producer delivery is at-least-once. SQL effects of the demo handler are atomic and idempotent only under the documented trust and database boundaries.
