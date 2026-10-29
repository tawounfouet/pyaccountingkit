# FND-C07 — Standalone Foundation integration decision

**Current result: HOLD / DO NOT MERGE.** This is an observed gate state, **not** an independent reviewer decision or an assertion of code failure.

- Recent repo: `tawounfouet/pyaccountingkit`; historical `pyaccountingkit_old` integration deferred.
- Single main integration candidate: [draft PR #33](https://github.com/tawounfouet/pyaccountingkit/pull/33), observed `272d85f319219597abec845929038573b4712203`.
- `main` was bootstrap `cb746be7ae95146d2bd50ce1aac049ea6da2d15e`; PR draft/unmerged and **no submitted code reviews** observed at review preparation.
- Four exact-PR-head CI workflows passed: Python [#40955190292](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40955190292), PostgreSQL [#40955190201](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40955190201), migration/restore [#40955190187](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40955190187) and wheel/sdist [#40955190309](https://github.com/tawounfouet/pyaccountingkit/actions/runs/40955190309), Python 3.11/3.12.
- Selected lineage: `#27 → #28 → #29 → #31 → #33`. Do not merge the stacked PRs separately in addition to #33 or import divergent PR #21 migration.

## Required GO gates before any main merge

| Gate | Current | Responsible reviewer and proof |
|---|---|---|
| G0 — Architecture and baseline | **PENDING_REVIEW** | [G0 dossier](G0_DECISION.md), exact-SHA independent architecture review |
| G1 — Domain Kernel | **PENDING_REVIEW** | [G1 dossier](G1_DECISION.md), independent domain review |
| G2 — Technical Foundations | **PENDING_REVIEW** | [G2 dossier](G2_DECISION.md), independent security/ops review for explicitly bounded **development** acceptance |
| PR #33 source review | **NO SUBMITTED APPROVAL OBSERVED** | Authorized reviewer of final exact head and no blocking comments |
| CI on review head | **PASS on observed PR #33 SHA**, recheck after any subsequent commit | Four green workflows, no skipped mandatory SQL qualification |
| Post-merge exact `main` SHA | **NOT APPLICABLE YET** | Must run full suite after explicit approved merge |
| Stable publication / historical API parity / production IAM | **OUT OF SCOPE** | Separate workstreams, NOT secretly accepted by a Foundation GO |

The dossier branch itself adds governance records. If adopted into PR #33, the candidate SHA changes and **all formal reviews/evidence must refer to the new head**.

## Reviewer actions

1. Review the scope and ADRs. If a decision is still missing, mark **NO_GO** or **PENDING_REVIEW** explicitly with a blocker; do not create a GO through automation.
2. Independently review G0, G1 and G2 on the **same candidate SHA**; record reviewer identities, dates, exceptions and attributable GitHub review / decision URLs.
3. Require signed/verified actual deployment assurances for any privileged production claim. Without them, limit the acceptance to documented **standalone development-only** scope.
4. After all gates are accepted, authorize a controlled merge of the **single** PR #33 with an explicit change record.
5. Re-run complete Python/PG/migration/artifact CI on `main` and record its exact SHA. Do not claim Foundation DONE before this evidence and closure entry.

## Reserved sign-off record

- Merge authorization: **NOT GRANTED**
- Approver: **UNASSIGNED**
- Approval date: **NOT RECORDED**
- Gate reviews (G0/G1/G2): **MISSING**
- Candidate SHA finally reviewed: **NOT RECORDED**
- Final merged main SHA: **NOT MERGED**
- Post-merge exact-main CI: **NOT RUN**
- Release status: **NO RELEASE**
