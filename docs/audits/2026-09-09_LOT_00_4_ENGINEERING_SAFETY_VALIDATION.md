# LOT-00.4 - Engineering Safety Validation

> Project: PyAccountingKit  
> Milestone: `0.0.1` Repository Bootstrap  
> Lot: `LOT-00.4 - Engineering Safety`  
> Validation date: `2026-09-09`

## 1. Scope

LOT-00.4 converts the bootstrap safety scripts from placeholders into executable, blocking engineering gates. It introduces no accounting-domain behavior and does not create fake tests to hide the missing bootstrap test suite.

The implemented gates are:

- repository hygiene;
- architecture boundary validation;
- root manifest/version coherence;
- Ruff lint and formatting;
- strict MyPy validation;
- wheel/sdist build and package qualification;
- orchestration through a release qualification command.

Real bootstrap tests remain owned by `LOT-00.5 - Bootstrap Test Suite`.

## 2. Implemented safety scripts

### `scripts/check_hygiene.sh`

The repository hygiene gate now rejects or validates:

- tracked Python/cache/build artifacts (`__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `dist/`, `build/`, `.egg-info`, compiled Python files, coverage artifacts and `.DS_Store`);
- tracked local `.env` files except documented sample/example variants;
- residual ChatGPT/file-search provenance markers in product documentation/source/test/example content;
- merge-conflict markers in code and configuration files;
- malformed or missing root JSON manifests;
- Python syntax errors in `scripts/` and `src/pyaccountingkit/`.

### `scripts/validate_architecture.py`

The architecture gate performs AST-based checks and enforces:

- isolation of `core`, `domain` and `ports` from infrastructure/framework imports;
- no dependency from isolated layers on adapters, integrations, application or public layers;
- the special `0.0.1` invariant that non-root package modules remain documentation-only architectural scaffolds;
- no premature business class/function surface from the root package.

### `scripts/verify_package.py`

The package gate now:

- builds wheel and sdist through `python -m build`;
- executes `twine check` on both artifacts;
- validates wheel metadata (`Name`, `Version`);
- requires `pyaccountingkit/__init__.py` and `pyaccountingkit/py.typed` in the wheel;
- rejects repository-only content such as `tests/`, `docs/`, `resources/` or `data/` from the wheel;
- verifies reproducibility-critical files in the sdist;
- creates a clean virtual environment;
- installs the wheel with `--no-deps`;
- verifies the installed package import and runtime version;
- enforces zero mandatory runtime dependencies for bootstrap `0.0.1`.

### `scripts/qualify_release.py`

The qualification orchestrator now runs, in order:

1. repository hygiene;
2. architecture safety;
3. manifest coherence;
4. Ruff lint;
5. Ruff formatting;
6. strict MyPy validation;
7. package verification;
8. Pytest, unless explicitly skipped.

`--skip-tests` exists only as a temporary LOT-00.4 diagnostic/CI escape hatch until LOT-00.5 creates real bootstrap tests. The command explicitly reports that a qualification with tests skipped is not the final release qualification.

## 3. CI integration

`.github/workflows/ci.yml` now:

- includes `scripts/` in Ruff lint and formatting checks;
- retains strict MyPy validation;
- adds an `engineering-safety` job;
- runs `python scripts/qualify_release.py --skip-tests` in that job;
- leaves the existing Python 3.11/3.12/3.13 Pytest matrix unchanged and therefore visibly red until LOT-00.5 introduces real tests.

The development extra now includes `build` and `twine`; mandatory project dependencies remain empty.

## 4. Final CI evidence

Validation was executed on branch head:

```text
7e41b01adb3954616178b865071e6e42a558486f
```

The final `engineering-safety` run produced:

```text
Repository hygiene:     PASS
Architecture safety:    PASS
Manifest coherence:     PASS
Ruff lint:              PASS
Ruff format:            PASS
Strict type checking:   PASS
Package verification:   PASS

Release qualification: PASS
Project version:        0.0.1
Gates passed:           7
Aggregate gate time:    17.25s
```

Architecture evidence:

```text
Architecture validation: PASS
Project version: 0.0.1
Source modules inspected: 234
Isolated layers: core, domain, ports
```

Package evidence:

```text
Successfully built pyaccountingkit-0.0.1.tar.gz
Successfully built pyaccountingkit-0.0.1-py3-none-any.whl

twine check wheel: PASS
twine check sdist: PASS
Package verification: PASS
Runtime dependencies: 0
```

Static quality evidence:

```text
ruff check src/ tests/ scripts/          PASS
ruff format --check src/ tests/ scripts/ PASS
mypy src/                                PASS
```

Security workflow:

```text
Security: PASS
```

## 5. Test-suite status

The regular Pytest matrix still fails because LOT-00.3 intentionally removed 43 empty files named `test_*.py` and LOT-00.5 has not yet introduced the real bootstrap suite.

Current state:

```text
pytest -> collected 0 items -> exit code 5
```

This failure is intentionally visible. LOT-00.4 does not add dummy assertions and does not redefine Pytest exit code 5 as success.

Consequently:

- engineering safety qualification is green;
- full release qualification remains incomplete until LOT-00.5;
- the global CI workflow remains red solely because the real bootstrap test suite is still missing.

## 6. Exit decision

LOT-00.4 is complete when all engineering gates independent of the future bootstrap tests are executable and green.

Final decision:

- repository hygiene gate: **DONE**;
- architecture gate: **DONE**;
- manifest/version gate: **DONE**;
- lint/format gate: **DONE**;
- type-safety gate: **DONE**;
- package build/install gate: **DONE**;
- CI engineering-safety integration: **DONE**;
- accounting functionality added: **0**;
- fake tests added: **0**.

The next natural lot is `LOT-00.5 - Bootstrap Test Suite`.