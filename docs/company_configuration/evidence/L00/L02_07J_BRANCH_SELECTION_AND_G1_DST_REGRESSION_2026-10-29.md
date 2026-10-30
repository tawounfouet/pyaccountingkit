# L02-07j alternate PR comparison and G1 DST-fold regression

**Date:** 2026-10-29. **Status:** TECHNICAL RECOMMENDATION / OPEN ARCHITECTURE DECISION, not a gate or merge authorization.

## 1. Sources inspected

- [PR #21](https://github.com/tawounfouet/pyaccountingkit/pull/21), head `a85a9db589b00ecee54bef25ef2ac3f32280117b`, based on signed workload boundary.
- [PR #22](https://github.com/tawounfouet/pyaccountingkit/pull/22), head `68ec07dfc6e0d9de3d95a8feb386c39b7108919f`, same base.
- GitHub comparison: branches **diverged** at `229135024cc1763ebfd7549cf07291db38173ffd`; #22 has two unique commits and #21 three unique commits in the opposite direction.
- Read source: their full SQL migration 0011, revocation processor/repository and PostgreSQL tests. PR #23–#25 have **#22** as their ancestry.

## 2. Semantic comparison

| Feature | PR #21 alternate | PR #22 selected-by-downstream |
|---|---|---|
| Receipt primary key | `revocation_id` | `request_id`, with UNIQUE `event_id` |
| Revocation before fence issue | SQL requires fence; rejects absent request | **TOMBSTONED**, blocks future fence issue |
| Serialization | `SELECT ... FOR UPDATE` on existing fence | Request-scoped advisory transaction lock + fence row lock + BEFORE INSERT tombstone guard |
| Revoke active fence | `APPLIED` | `REVOKED` |
| Already revoked | `ALREADY_REVOKED` | `ALREADY_REVOKED` |
| Revocation too late | `TOO_LATE` | `ALREADY_CONSUMED` |
| Signed event scope | Includes `approval_id`, `revoked_at` | Includes issuer, signer key ID, event ID, request, role, operation, tenant, signed digest |
| Read/ACK contract | Provider batch poll + acknowledge | Trusted `read(event_id)` then `acknowledge(receipt)` |
| SQL caller checking | Python receiver checks `session_user == cc_iam_revocation` | SQL GRANT restricts function, but repository does not itself check `session_user` |
| SQL trust | Signed claims verified in application, not SQL | Same limitation |
| Subsequent compatibility | Not integrated downstream | #23–#25 use the #22 schema/semantics |

## 3. Recommendation and rationale

**Prefer PR #22's lineage** for future integration, subject to independent review. A revocation received before the permission was issued must block later issuance. PR #22 explicitly persists such a tombstone and serializes its transaction with the issuance trigger; PR #21's absent-fence case cannot enforce this safeguard. Replacing #22 with #21 would regress behavior and break later migrations/ACK outbox integrations.

**Do not merge both migration 0011 variants.** They create the same logical receipt/function names with different schemas/function signatures and incompatible replay/status contracts. An in-place rewrite of an applied migration is prohibited; use a new forward-only migration after a reviewed decision if a capability must be restored.

## 4. Items worth retaining from #21 / unresolved controls

1. `approval_id` binding and explicit `revoked_at` in #21: assess whether the signed external IAM event semantics should carry a permit approval reference or provider revocation timestamp. An independent revocation request might correctly supersede any approval, so do not require `approval_id` without threat analysis.
2. The explicit `session_user` check in #21 adds defense in depth absent from #22's repository adapter. The #22 SQL grants remain the authoritative privilege boundary; a compromised receiver SQL credential still can submit claimed attributes directly.
3. #21's batch poll interface differs from #22's per-event read contract. Check whether the provider API and current #23–#25 durable ACK worker cover all needed operational delivery requirements.
4. #22 keys the durable receipt by request ID and rejects a distinct event ID for the same request. Confirm provider guarantees and incident-recovery consequences before declaring that model universally correct.
5. Neither candidate proves a live IAM source, key-custody policy, workload binding, online revocation, immutable external audit or production failover. G2 security #9 remains open.

**Next review action:** independently sign the choice; mark #21 **superseded, not merged** only after its non-overlapping capabilities are explicitly triaged. The comparison alone is not authorization to close/remove #21.

## 5. G1 security-relevant temporal correction delivered on PR #3

Inspection of the L01 domain kernel found a reproducible temporal ordering error in `KnowledgeInterval`: Python compares aware datetimes sharing the same `ZoneInfo` object using local wall-clock ordering, ignoring `fold`. During Paris's 2026 autumn DST rollback, `2026-10-25 02:50 fold=0` precedes `2026-10-25 02:10 fold=1` on the UTC timeline, but direct `end <= start` returns `True`, falsely rejecting a valid interval. Membership and overlap had the same risk.

**Fix on PR #3 branch:**
- `aaccf9fa25e716302e2c7b8c98871c54b67e4287`: compare `KnowledgeInterval` instants after UTC conversion in constructor, `contains`, and `overlaps`. The `EffectiveInterval` date-only semantics are unchanged.
- `885410195ac2e08bfd9f2854114c146af07ca614`: two DST-fold regression tests for ordering, membership, half-open boundary and symmetric overlap.
- [GitHub Actions Python CI #40941832315](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40941832315) and [#40941822140](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40941822140) both report success on **Python 3.11 and 3.12** for the exact test-commit SHA. This is verified CI metadata, not an independently reproduced full test run.

**G1 is still NOT APPROVED.** The historical `pyaccountingkit_old` codebase now requires explicit namespace, identity and error contract reconciliation (see adjacent G0 report). The fix was made on the unmerged PR #3 feature branch only; the later stacked branches have not been rebased onto this new head. Do not claim the fix already propagates to PR #25.

## 6. Non-claims

No feature-stack merge, issue closure, G0/G1/G2 approval, stable release or production IAM security acceptance was performed in this assessment.
