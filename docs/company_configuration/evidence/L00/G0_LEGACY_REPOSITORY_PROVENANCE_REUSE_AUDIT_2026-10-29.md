> **SUPERSEDED G0 SEQUENCING RECOMMENDATION — 2026-10-29 product-owner decision.** The historical repository and all technical findings below remain valid evidence. However, the instruction to *block the recent repository's standalone Foundation until historical reconciliation* is **no longer applicable**. The project owner chose to finish G0/G1/G2 **in the recent repository first**, with historical interoperability deferred to a separate workstream. See [standalone ADR-CC-00A](https://github.com/tawounfouet/pyaccountingkit/blob/chore/company-config-foundation-standalone-consolidation/docs/company_configuration/evidence/L00/ADR_CC_00A_STANDALONE_FOUNDATION_SCOPE.md) and [main integration candidate PR #27](https://github.com/tawounfouet/pyaccountingkit/pull/27). Technical security and in-repo architecture gates are **still not signed off**.

# G0 critical finding — historical PyAccountingKit source tree and reuse decision

**Observed:** 2026-10-29 · **Status:** VERIFIED EXISTENCE / ARCHITECTURAL CONFLICT · **Gate: G0 NO-GO pending decision**

This is a cross-repository read-only inspection, **not a test execution**, migration, authorization to merge, or final architectural decision.

## 1. Two repositories exist

| Axis | New Company Configuration repository | Historical PyAccountingKit repository |
|---|---|---|
| Repository | [tawounfouet/pyaccountingkit](https://github.com/tawounfouet/pyaccountingkit) | [tawounfouet/pyaccountingkit_old](https://github.com/tawounfouet/pyaccountingkit_old) |
| Observed `main` SHA | `cb746be7ae95146d2bd50ce1aac049ea6da2d15e` | `10b0a87076e66824d69cd24eafdbcb272cf1cd1d` |
| Default-branch content | Bootstrap `README.md` only | Complete package, application, ports, adapters, resources, documentation and tests |
| Repository size reported by GitHub | 459 KB (includes open development branches) | 105,776 KB |
| `pyproject.toml` project name | `pyaccountingkit` (on PR #3, not `main`) | `pyaccountingkit` |
| Package version in checked `pyproject.toml` | `0.0.0` (on PR #3) | `0.7.0rc2` |
| Packaging | setuptools scaffold, `src/pyaccountingkit` | Hatchling, `src/pyaccountingkit` |
| Company Configuration module | Draft stack #3–#25 under `src/pyaccountingkit/company_configuration` | No `company_configuration` directory in the inspected `src/pyaccountingkit` root listing |

The old repository's `main` Git history contains a 0.7.0rc2 REM-10 qualification commit. The README refers to earlier 0.5.0 stable compatibility, but **this audit did not independently verify published releases or artifacts**; GitHub releases API returned an empty collection. Do not equate a package version string with a published release.

**G0 consequence:** The new repository's pre-bootstrap `NO_INITIAL_COMMIT` observation is true *only for that repository*, not for the PyAccountingKit project. The historical-code-location step in [issue #1](https://github.com/tawounfouet/pyaccountingkit/issues/1) must now cite the actual old repository and assign a reconciliation owner. A clean-room rebuild may be an explicit future decision, but is NOT an uncontested starting assumption.

## 2. Verified existing capabilities: preliminary REUSE/REFACTOR assessment

| Domain / capability | Historical path or proof | New candidate | Recommendation, pending review |
|---|---|---|---|
| Accounting identity | `core/identifiers.py`, `core/entity_scope.py`, `domain/identity/entity.py` | Company/LegalEntity/Book UUID wrappers; new `LegalEntity` | **REFACTOR / ADAPT**: keep existing public identifiers and entity contracts stable; introduce explicit CompanyConfiguration identity boundary |
| Error hierarchy | `core/errors.py` rooted in `AccountingError(Exception)`, public error-code manifest | New `company_configuration/domain/shared/errors.py` rooted in `DomainError(ValueError)` | **REUSE/ADAPT** canonical error translation; do not create a second public exception taxonomy accidentally |
| Transaction and repository ports | `ports/unit_of_work.py`, `ports/repositories.py`, `ports/audit.py`, `ports/outbox.py` | L02 repository/UoW/audit/outbox | **REUSE WHERE COMPATIBLE**, compose a bounded-context-local port as needed; prevent duplicate global abstractions |
| Company charts | `domain/charts/company_chart.py`, `domain/charts/company_account.py` scaffold, chart/application adapters | L05 company chart and mappings targeted | **REUSE/REFACTOR**, inventory statuses, versioning and effects before new L05 |
| Periods | `domain/periods/accounting_period.py` | New `EffectiveInterval` with half-open bounds; L06 | **CONTRACT CONFLICT**: historical `AccountingPeriod.contains` uses inclusive `end_date`; new proposed interval uses `[start,end)`. No implicit reinterpretation |
| Clock / time | `core/clock.py` provides injectable `ClockProtocol`, UTC system/frozen clocks | New `KnowledgeInterval` | **REUSE CLOCK**, preserve UTC semantics; new PR #3 DST correction must still be reconciled |
| Ledger / subledgers / reporting | `domain/journals`, `domain/ledger`, `domain/subledgers`, `application/reporting`, etc. | Company Configuration deliberately does not post | **REUSE, preserve ownership**. Do not rebuild ledger functionality in Company Configuration |
| Public API/contracts | `public/`, `PUBLIC_API_MANIFEST.json`, `PUBLIC_ERROR_CODES.json`, `SNAPSHOT_SCHEMA_MANIFEST.json` | Early scaffold has no equivalent legacy API compatibility proof | **FREEZE compatibility baseline**; plan manifest diff and contract tests |
| PostgreSQL adapters | `adapters/django`, `adapters/sqlalchemy`, tests/integration | New Company Configuration PostgreSQL migrations 0001–0013 | **REVIEW migration topology**: different bounded contexts might coexist, but not without deployment/connection ownership analysis |

All paths above were observed on the historical repository's `main` at the recorded SHA; the assessment is preliminary and based on source excerpts and directory metadata, not a full behavior-equivalence or regression test.

## 3. Concrete semantic collisions

### 3.1 Identifiers

Historical `EntityId` is a `typing.NewType('EntityId', str)` with an ID factory. New `LegalEntityId` is a frozen UUID wrapper. These types are **not interchangeable**. A migration must specify mapping, persistence encoding, external API translation, existing record identity and replay compatibility.

### 3.2 Accounting entity versus LegalEntity

Historical `AccountingEntity` is a legal accounting unit that owns journals, charts and ledgers. New `LegalEntity` is a proposed organization configuration identity and scope aggregate. Their overlap and separation must be explicitly resolved with an anti-corruption adapter rather than implicitly equating IDs or ownership.

### 3.3 Period boundary

The historical `AccountingPeriod.contains` returns `start_date <= business_date <= end_date` (inclusive final day). Proposed `EffectiveInterval.contains` returns `start <= day < end`. Converting historical periods to half-open intervals requires a **typed and tested boundary adapter**, not modifying stored dates or silently swapping semantics.

### 3.4 Exceptions / public manifests

The historical errors derive from `AccountingError(Exception)` and have an established public manifest. The new local `DomainError(ValueError)` and typed codes might be legitimate **internal** contracts, but should not silently alter public consumers' exception matching.

### 3.5 Packaging and release provenance

Both trees use the same distribution name and import namespace. Publishing the new scaffold's `0.0.0` into the original package channel or replacing the historical package source would risk a destructive compatibility reset. No packaging, PyPI, tags, publishing, retagging or repository renaming was performed here.

## 4. Candidate integration strategies — architectural decision required

**A — Preferred candidate: extend the historical code lineage.** Treat `pyaccountingkit_old` as the existing implementation baseline, first inspect its tagged/release history and current tests, then port **only** bounded-context-specific Company Configuration additions and keep existing `core`, `ports`, `public` and adapters backwards compatible. Choose repository naming/default branch and transfer strategy through a reviewed ADR. Preserve commits/history and verify the post-integration exact SHA.

**B — Separate deployable package.** If Company Configuration should be independently versioned, give it a unique distribution/import namespace and explicit integration contracts rather than a second distribution named `pyaccountingkit`. This changes the monorepo plan and needs justification.

**C — Explicit clean-room replacement (NOT recommended by default).** Would require an inventory of every old public behavior, migration, contract, historical version and consumer and a signed deprecation/migration plan. A new empty repo alone does not justify it.

**Never** force-push old history over new, import both package trees blindly, overwrite historical `main`, or merge all 20 drafts while this decision remains open.

## 5. Updated G0 acceptance tasks

- [x] Historical source repository **identified** and exact `main` SHA captured.
- [x] Historical core/ports/domain/adapter/public inventories sampled.
- [x] Collision between versions and distribution/import names documented.
- [x] At least five concrete semantic collision/reuse areas mapped.
- [ ] Audit historical releases, tags, publishing lineage and consumer dependencies independently.
- [ ] Compare targeted exports and contracts against `PUBLIC_API_MANIFEST.json` and `PUBLIC_ERROR_CODES.json`.
- [ ] Establish architecture compatibility matrix for 0.7.0rc2 and new Company Configuration modules.
- [ ] Select approved target repository, integration topology, package name and history preservation strategy.
- [ ] Qualify clean checkout and tests on the **historical** exact SHA; benchmark and migration rehearsal if required.
- [ ] Assign independent reviewer, approve or reject revised ADRs and record G0 `GO / NO_GO` on an exact integration SHA.

**Current verdict: G0 NO-GO pending explicit source-lineage resolution.** G1's current code-level CI may be green, but the **package/API integration part of G1 is not qualified**. G2 and all current draft PRs remain unmerged.

## Source references

- [Original repository root](https://github.com/tawounfouet/pyaccountingkit_old/tree/main)
- [Historical pyproject](https://github.com/tawounfouet/pyaccountingkit_old/blob/10b0a87076e66824d69cd24eafdbcb272cf1cd1d/pyproject.toml)
- [Historical identity](https://github.com/tawounfouet/pyaccountingkit_old/blob/10b0a87076e66824d69cd24eafdbcb272cf1cd1d/src/pyaccountingkit/core/identifiers.py)
- [Historical UoW](https://github.com/tawounfouet/pyaccountingkit_old/blob/10b0a87076e66824d69cd24eafdbcb272cf1cd1d/src/pyaccountingkit/ports/unit_of_work.py)
- [Historical periods](https://github.com/tawounfouet/pyaccountingkit_old/blob/10b0a87076e66824d69cd24eafdbcb272cf1cd1d/src/pyaccountingkit/domain/periods/accounting_period.py)
- [New foundation PR #3](https://github.com/tawounfouet/pyaccountingkit/pull/3)
- [Gate audit PR #26](https://github.com/tawounfouet/pyaccountingkit/pull/26)


## 6. Compatibility proof started on the historical lineage (2026-10-29)

A deliberately narrow and **unmerged** proof-of-concept has been opened against the actual accounting implementation:

- [Historical PR #96 — Company Configuration compatibility spike](https://github.com/tawounfouet/pyaccountingkit_old/pull/96).
- Branch: `spike/company-config-foundation-compat-g0-20261029`, directly based on historical `main` `10b0a87076e66824d69cd24eafdbcb272cf1cd1d`.
- Initial head for CI: `d8b3ff8e074689e2f6e83c5b14c9580ec1e4517f`.
- Added only a **private integration boundary**, contract tests and an audit note. No existing public facade, historical domain, UoW, period model, schema, migration or version was modified.
- Identity bridge requires explicit tenant/company/legal UUID → historical `EntityId` binding; rejects duplicate identity aliasing and any unknown or foreign scope. The evidence reference is not automatically trusted as IAM authorization.
- Period adapter converts the historical inclusive final accounting date to the proposed exclusive successor date; rejects `date.max`, preventing a false successful translation.
- Root export manifest regression check ensures no accidental facade expansion.

**These tests validate only a candidate compatibility shape, not the whole Company Configuration domain or production IAM/ABAC.** The historical CI is the relevant qualification system; check the exact PR head's tests, quality, package and security workflows before any promotion. G0 remains **NO-GO until the project-owner and independent architecture review decide the integration source of truth, upgrade path and evidence acceptance**.

Proposed sequencing: (1) review this cross-repository proof; (2) approve a canonical integration/anti-corruption ADR; (3) preserve the historical public API and versioned release lineage; (4) selectively port new Company Configuration domain and L02 modules behind the approved boundary with migration and contract tests; (5) qualify exact merged SHA and gate decisions. Do not merge either draft stack as-is.
