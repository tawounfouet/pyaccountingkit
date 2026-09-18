# Release 0.4.0 — Stable Promotion Plan

## 1. Objective

Promote the qualified `0.4.0rc1` baseline to stable `0.4.0` without introducing new
subledger, settlement, reconciliation or financial-analysis semantics.

The stable release is a promotion of already-qualified behavior, not a feature lot.

```text
0.4.0rc1
   |
   | zero new business-domain code
   v
version + manifests + release documentation
   |
   v
canonical CI + package + Security requalification
   |
   v
0.4.0
```

## 2. Baseline

- Base version: `0.4.0rc1`
- Base merge: `c47d9cb29961fb2a5e4bcc0696d073b0839b940c`
- Branch: `release/0.4.0`
- Target version: `0.4.0`
- Scope: stable promotion of LOT-18 through LOT-20 and the 0.4 cross-lot RC qualification

LOT-21 / `0.5.x` work is explicitly excluded.

## 3. Stable gate inherited from the roadmap

The `0.4.0` stable line requires all of the following to remain green together:

- settlement allocation property suite;
- stale/double-allocation concurrency rejection;
- subledger/control-account reconciliation golden evidence;
- AR/AP cross-lot integration through DueItem, Settlement, Allocation, OpenItem and Aging;
- financial-analysis golden evidence for EBE, EBITDA, CAF, FRNG, BFR, Net Treasury and ratios;
- deterministic trend and AnalysisSnapshot replay;
- Corporate Finance boundary guard;
- complete retained `0.3.x` import/reporting integration and replay qualification;
- Python 3.11 / 3.12 / 3.13 canonical CI;
- Ruff, canonical formatting and strict mypy;
- wheel/sdist package verification;
- dependency audit and static security analysis.

`0.4.0rc1` established executable evidence for these gates. Stable promotion must rerun them on
the exact final `0.4.0` metadata HEAD.

## 4. Non-negotiable promotion rules

1. No production domain or application behavior changes belong in this branch.
2. No public API is declared frozen merely because the package reaches `0.4.0`; the project remains pre-1.0.
3. No accounting, regulatory or Corporate Finance compatibility claim may be broadened during promotion.
4. Allocation remains distinct from General Ledger posting.
5. Aging remains distinct from impairment.
6. Financial Analysis remains read-only derived evidence.
7. No test, type, lint, package or Security gate may be weakened to obtain the stable release.
8. If a final gate exposes a real defect, stable promotion stops and the defect is fixed explicitly before retrying.

## 5. Required changes

Only release metadata/documentation changes are expected:

- `pyproject.toml`: `0.4.0rc1` -> `0.4.0`;
- `PUBLIC_API_MANIFEST.json`: stable package version while retaining pre-1.0 API status;
- `PUBLIC_ERROR_CODES.json`: version alignment only;
- `ADAPTER_CONTRACT_MANIFEST.json`: version alignment only;
- `REGULATORY_COMPATIBILITY_MATRIX.json`: version alignment and stable qualification wording without broader claims;
- `README.md`: stable 0.4.0 status and qualification boundary;
- `CHANGELOG.md`: stable 0.4.0 release entry summarizing LOT-18 through LOT-20;
- plans index: mark the stable promotion as the active release step.

No file under `src/pyaccountingkit/domain/` should change.

## 6. Qualification sequence

The exact final stable HEAD must pass:

```text
[ ] repository hygiene
[ ] architecture safety
[ ] manifest coherence
[ ] CI workflow contract
[ ] Ruff lint
[ ] Ruff format
[ ] strict mypy
[ ] unit/property/contract
[ ] integration
[ ] golden
[ ] replay
[ ] concurrency
[ ] Python 3.11
[ ] Python 3.12
[ ] Python 3.13
[ ] wheel/sdist package verification
[ ] canonical CI gate
[ ] dependency audit
[ ] Bandit static analysis
```

The canonical CI matrix already executes the release evidence. Stable promotion does not add a
parallel test architecture.

## 7. Compatibility boundary

Stable `0.4.0` means the LOT-18/19/20 release line is qualified under the repository's current
contracts. It does not mean:

- public API freeze before 1.0;
- Django/PostgreSQL or SQLAlchemy/PostgreSQL adapter qualification;
- exhaustive statutory or regulator filing certification;
- a Corporate Finance engine;
- LOT-21 Public API Facade completion.

## 8. Exit criterion

The release may be merged only when the final `0.4.0` HEAD is green on canonical CI, package and
Security and all root manifests/documentation are version-coherent.

After merge, `main` becomes the stable `0.4.0` baseline. Only then may LOT-21 /
`0.5.0a1` begin.
