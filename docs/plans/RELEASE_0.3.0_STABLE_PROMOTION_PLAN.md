# Release 0.3.0 — Stable Promotion Plan

## 1. Objective

Promote the qualified `0.3.0rc1` baseline to stable `0.3.0` without introducing new accounting, import, reporting or regulatory semantics.

The stable release is a promotion of already-qualified behavior, not a feature lot.

```text
0.3.0rc1
   |
   | no domain/API behavior change
   v
metadata + documentation alignment
   |
   v
canonical CI + package + Security requalification
   |
   v
0.3.0
```

## 2. Baseline

- Base version: `0.3.0rc1`
- Base merge: `75bf1b9b827992822727b0fc1ac587a4102434ad`
- Branch: `release/0.3.0`
- Target version: `0.3.0`
- Scope: stable promotion of LOT-14 through LOT-17 and the cross-lot RC qualification

LOT-18 / `0.4.x` work is explicitly excluded.

## 3. Stable gate inherited from the roadmap

The `0.3.0` stable line requires all of the following to remain green together:

- FEC contract/golden/rollback/idempotency/concurrency qualification;
- financial-statement golden qualification;
- regulatory mapping safety;
- report replay qualification;
- mandatory cross-lot integration from source evidence to reporting evidence;
- Python 3.11 / 3.12 / 3.13 canonical CI;
- package verification;
- dependency audit and static security analysis.

`0.3.0rc1` established executable evidence for these gates. Stable promotion must rerun them on the exact final `0.3.0` metadata HEAD.

## 4. Non-negotiable promotion rules

1. No production domain or application behavior changes belong in this branch.
2. No public API is declared frozen merely because the package reaches `0.3.0`; the project remains pre-1.0.
3. No regulatory compatibility claim may be broadened during promotion.
4. PCG/FEC cross-lot qualification remains distinct from SYSCOHADA LOT-17 golden/replay qualification.
5. No test, type, lint, package or security gate may be weakened to obtain a stable release.
6. If a final gate exposes a real defect, stable promotion stops and the defect is fixed explicitly before retrying.

## 5. Required changes

Only release metadata/documentation changes are expected:

- `pyproject.toml`: `0.3.0rc1` -> `0.3.0`;
- `PUBLIC_API_MANIFEST.json`: target stable package version while retaining pre-1.0 API status;
- `PUBLIC_ERROR_CODES.json`: version alignment only unless an actual error-code change is required (none expected);
- `ADAPTER_CONTRACT_MANIFEST.json`: version alignment and stable qualification wording;
- `REGULATORY_COMPATIBILITY_MATRIX.json`: version alignment without broadening compatibility claims;
- `README.md`: stable 0.3.0 status and canonical release qualification workflow;
- `CHANGELOG.md`: stable 0.3.0 release entry summarizing the complete 0.3.x line.

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

The canonical CI matrix already includes integration/golden/replay/concurrency. The stable promotion therefore does not add another parallel test architecture.

## 7. Compatibility boundary

Stable `0.3.0` means the imports/reporting release line is qualified under the repository's current contracts. It does not mean:

- public API freeze before 1.0;
- production database adapter qualification;
- exhaustive legal/statutory filing certification;
- DGFiP authority certification of generated filings;
- exhaustive official PCG or SYSCOHADA templates;
- LOT-18 subledger functionality.

## 8. Exit criterion

The release may be merged only when the final `0.3.0` HEAD is green on canonical CI, package and Security and all root manifests/documentation are version-coherent.

After merge, `main` becomes the stable `0.3.0` baseline. Only then should LOT-18 / `0.4.0a1` begin.
