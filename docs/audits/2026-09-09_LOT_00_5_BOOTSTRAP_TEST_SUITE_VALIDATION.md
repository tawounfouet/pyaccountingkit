# LOT-00.5 - Bootstrap Test Suite Validation

> Project: PyAccountingKit  
> Milestone: `0.0.1` Repository Bootstrap  
> Lot: `LOT-00.5 - Bootstrap Test Suite`  
> Validation date: 2026-09-09

## 1. Scope

LOT-00.5 closes the zero-test debt left intentionally by LOT-00.3 and LOT-00.4. It adds executable tests for the repository bootstrap itself without introducing accounting-domain behavior.

The tested scope covers:

- package and runtime version coherence;
- installed distribution metadata;
- zero mandatory runtime dependencies;
- PEP 561 `py.typed` availability;
- explicit minimal package-root public surface;
- root manifest schema, version and bootstrap-emptiness contracts;
- architecture boundary enforcement;
- negative architecture tests proving forbidden imports are detected;
- negative bootstrap-scaffold tests proving premature executable business code is detected;
- engineering-safety CLI smoke tests;
- manifest version-drift rejection;
- wheel/sdist contract checks, including repository-content leak rejection.

No `Money`, `Currency`, `JournalEntry`, posting, ledger, reporting, persistence or adapter behavior is implemented by this lot.

## 2. Test inventory

The final Bootstrap suite contains **25 real tests**:

| Area | Tests |
| --- | ---: |
| Architecture safety | 4 |
| Bootstrap manifests | 5 |
| Package/runtime metadata | 5 |
| Engineering safety tooling | 5 |
| Package artifact contracts | 6 |
| **Total** | **25** |

These tests are assertions against real bootstrap contracts. No dummy `assert True` tests are used.

## 3. Cross-version CI evidence

The regular CI matrix completed successfully on the final validated implementation head:

```text
Python 3.11  PASS - 25 tests
Python 3.12  PASS - 25 tests
Python 3.13  PASS - 25 tests
```

The former Pytest result:

```text
collected 0 items
exit code 5
```

is therefore closed by LOT-00.5.

## 4. Static quality evidence

The final validated implementation head passed:

```text
Ruff lint       PASS
Ruff format     PASS
MyPy strict     PASS
Security        PASS
```

## 5. Full engineering-safety qualification

`python scripts/qualify_release.py` now runs with tests enabled by default in CI.

The final qualification passed all eight gates:

```text
Repository hygiene      PASS
Architecture safety     PASS
Manifest coherence      PASS
Ruff lint               PASS
Ruff format             PASS
Strict type checking    PASS
Package verification    PASS
Bootstrap test suite    PASS

Release qualification   PASS
Project version         0.0.1
Gates passed             8
Aggregate gate time     18.01s
```

The Bootstrap suite executed within the qualifier and reported:

```text
25 passed
```

## 6. Package evidence retained from full qualification

The package gate built and qualified:

```text
pyaccountingkit-0.0.1-py3-none-any.whl  PASS
pyaccountingkit-0.0.1.tar.gz            PASS
twine check                             PASS
isolated wheel installation             PASS
isolated runtime import                 PASS
mandatory runtime dependencies          0
```

The fast package unit tests do not replace this real package qualification. They test failure/acceptance contracts cheaply in each Python matrix job, while `engineering-safety` performs the actual isolated build and install once.

## 7. Negative-test evidence

LOT-00.5 does not only test the happy path. It proves that the safety tooling rejects invalid states, including:

- `import django` injected into the isolated `core` layer;
- an executable `Money` class injected into a `0.0.1` domain scaffold;
- a premature business function exposed from the package root;
- a manifest version deliberately drifted from `0.0.1`;
- repository-only content injected into a synthetic wheel;
- missing expected distribution artifacts.

This establishes that the gates are capable of failing for relevant violations rather than merely reporting the current repository as valid.

## 8. Public-surface contract

At `0.0.1`, the package root explicitly declares:

```python
__all__ = ["__version__"]
```

The `importlib.metadata` helper is private, and no accounting-domain symbol is exposed as a bootstrap public API.

## 9. Skip-test policy after LOT-00.5

`--skip-tests` remains available only as a focused diagnostic option.

A qualification performed with tests skipped is explicitly not a full release qualification. The CI `engineering-safety` job no longer uses this option.

## 10. Exit decision

LOT-00.5 satisfies its exit criteria:

- real Bootstrap tests exist;
- Pytest collects and executes 25 tests;
- Python 3.11, 3.12 and 3.13 are green;
- architecture positive and negative tests are active;
- manifest and version contracts are active;
- package artifact contracts are active;
- full engineering-safety qualification passes with tests enabled;
- Security is green;
- no accounting behavior was introduced.

**Decision: LOT-00.5 COMPLETE.**

The next remediation lot is `LOT-00.6 - CI Hardening`, focused on consolidating required CI gates and eliminating duplicated or weak pipeline semantics before release hardening.
