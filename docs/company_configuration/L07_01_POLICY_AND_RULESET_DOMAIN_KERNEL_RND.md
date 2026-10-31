# L07-01 — Policy & Ruleset Draft Kernel / Strict Candidate Preview (R&D)

**Date:** 2026-10-31  
**State:** ISOLATED R&D CANDIDATE; PR exact-head CI and governance pending.  
**Base:** main@acdee98ca2736d79e17174f510ac767defd90db8; NOT stacked on unmerged L03/L04/L05/L06 PRs.

**Source trace:** Requirements 01 §4.5 (POL-001..004), Invariants 07 §3.5 (INV-POL-01..05; BR-POL-01/02), Use Cases 08 CMD-15/16, Contracts 10 C10-Q06, Company Configuration Roadmap L07/G7. **The separate source 15_COMPANY_CONFIGURATION_ACCOUNTING_POLICIES_AND_RULESETS.md was not among supplied local files and was not found in the inspected repository; do not claim complete source-15 coverage.**

## Delivered

- Typed UUID identities PolicyCandidateId / RulesetCandidateId / PolicyAssignmentCandidateId; immutable PolicyCode, RulesetCode, PolicyTopic.
- Pure draft PolicyCandidateDraft and RulesetCandidateDraft with claimed entity scope, effective intervals, claimed framework references, revision and source provenance.
- Book-specific PolicyAssignmentCandidate with explicit policy/ruleset IDs, topic, effective and timezone-aware knowledge intervals.
- Pure preview_policy_candidate(scope, topic, as_of, known_at, complete tuple catalogs): exactly one active applicable candidate, or typed missing/conflict error.
- Whole-catalog fail-closed validation: duplicate IDs, overlapping effective policy/ruleset codes, invalid foreign inactive objects, missing references, wrong topics/framework *claims*, out-of-range dependencies and future overlapping bitemporal book/topic assignments.
- Frozen PolicyCandidatePreview with eligible_for_posting=False. No ordering fallback, latest-version fallback, implicit priority or inheritance.
- 21 local pytest cases including negative, temporal and order-invariance checks. GitHub Actions must separately qualify exact HEAD.

## Boundaries

POL-001 (candidate only): book-scoped association; NO real published policy.  
POL-002 (candidate only): typed ruleset + framework claim; NO independently verified Normative Layer binding.  
POL-003 (local partial): fail-closed topic conflict; NO governed global priority strategy.  
POL-004 (NOT IMPLEMENTED): group/entity/book inheritance and approved overrides.  
INV-POL-01/04/05 (live NOT PROVEN): signed publication, legal normative compatibility and authoritative dependencies missing.

The scope and framework refs are caller-supplied. The book is not verified as a published L04 book; no L05 chart, L06 posting guard, C10-Q06 live endpoint, SQL transaction, IAM signature, Outbox, financial computation, arbitrary rule interpreter, eval, PostingPlan or Ledger posting. This is NOT an accepted policy engine.

## Software-design learning conventions

DDD draft Entities with typed identities, Value Objects, pure Domain Service, Specification-style fail-closed selection, SOLID single responsibility, separation of Business/Accounting/Reporting Truth, Clean/Hexagonal isolation from infrastructure. No arbitrary executable rules.

## Next R&D and production prerequisites

1. L07-02: versioned candidate policy/ruleset bundles and content-integrity manifest (checksum not signature).
2. L07-03: independently approved policy cardinality, precedence/inheritance/exception ADR.
3. L07-04: safe bounded declarative DSL, explicitly mapping roadmap ADR-CC-07 to RULESET language (NOT CAL posting authority).
4. L07-05: candidate signed governance/SoD and published configuration contracts, subject to external authority.
5. L07-06+: C10-Q06 true producer, consumer compatibility, durable SQL, multi-book replay and E2E, independent approval.

All gates remain unchanged: G0/G1/G2 PENDING_REVIEW; G3 HOLD_SECURITY (#71); G4/G5/G6/G7 NOT_APPROVED. Do NOT merge/release or infer a GO from green R&D CI.
