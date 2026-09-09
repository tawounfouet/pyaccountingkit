# LOT-00.6 - CI Hardening Validation

> Project: PyAccountingKit  
> Milestone: `0.0.1` Repository Bootstrap  
> Lot: `LOT-00.6 - CI Hardening`  
> Validation date: 2026-09-09

## 1. Objective

LOT-00.6 turns the previously green but redundant CI into a canonical pipeline with explicit responsibilities, bounded execution, least-privilege permissions and one final aggregate status.

No accounting-domain behavior is introduced by this lot.

## 2. Previous CI topology

Before LOT-00.6, `.github/workflows/ci.yml` exposed separate `lint`, `typecheck`, `engineering-safety` and `test` jobs.

The `engineering-safety` job executed the complete `scripts/qualify_release.py`, which repeated Ruff, MyPy and Pytest work already performed by other CI jobs. This made the pipeline green but semantically redundant and made it harder to identify one canonical required check.

## 3. Canonical CI topology

LOT-00.6 replaces the previous topology with four explicit responsibilities:

```text
quality ─────┐
             │
test matrix ─┼──> ci-gate
             │
package ─────┘
```

### `quality`

Runs the static engineering gates only:

```text
Repository hygiene
Architecture safety
Manifest coherence
CI workflow contract
Ruff lint
Ruff format
Strict MyPy
```

The workflow invokes:

```text
python scripts/qualify_release.py --skip-tests --skip-package
```

This keeps the local full release qualifier intact while avoiding duplicate test and package work inside CI.

### `test`

Runs the Bootstrap suite independently on every supported Python version:

```text
Python 3.11
Python 3.12
Python 3.13
```

The matrix uses `fail-fast: false`, so a failure on one interpreter does not suppress evidence from the other supported versions.

### `package`

Runs package verification exactly once:

```text
python scripts/verify_package.py
```

This includes wheel/sdist build, metadata checks, `twine check`, isolated wheel installation and isolated import verification.

### `ci-gate`

Runs only after `quality`, the complete `test` matrix and `package` have terminated.

It uses `if: ${{ always() }}` and explicitly requires all three dependency results to equal `success`. This gives the repository one stable aggregate CI status suitable for future required-check configuration.

## 4. Workflow execution hardening

Both CI and Security now use:

- `permissions: contents: read`;
- explicit workflow concurrency groups;
- `cancel-in-progress: true` for superseded runs;
- `PIP_DISABLE_PIP_VERSION_CHECK=1`;
- `PYTHONUNBUFFERED=1`;
- explicit job timeouts;
- `python -m pip` / `python -m pytest` command forms;
- pip caching keyed by `pyproject.toml`.

A subsequent CI run demonstrated a real cache hit for Python 3.12, confirming that the cache configuration is operational rather than decorative.

## 5. GitHub Actions runtime baseline

The workflows were upgraded from the Node-20 generations used previously:

```text
actions/checkout@v4
actions/setup-python@v5
```

to the stable releases verified during implementation:

```text
actions/checkout@v7
actions/setup-python@v7
```

At implementation time, GitHub reported `actions/checkout v7.0.1` and `actions/setup-python v7.0.0` as their latest stable releases.

## 6. Executable CI workflow contract

LOT-00.6 adds:

```text
scripts/validate_ci.py
```

The validator protects both `.github/workflows/ci.yml` and `.github/workflows/security.yml`.

It rejects, among other things:

- reintroduction of legacy `lint`, `typecheck` or `engineering-safety` job IDs;
- a redundant full `python scripts/qualify_release.py` invocation inside canonical CI;
- an incomplete Python 3.11/3.12/3.13 matrix;
- missing `fail-fast: false`;
- missing `quality`, `test`, `package` or `ci-gate` jobs;
- a broken `needs: [quality, test, package]` aggregate dependency;
- missing least-privilege permissions;
- missing concurrency cancellation;
- missing pip caching;
- regression to `actions/checkout@v4` or `actions/setup-python@v5`.

The validator is itself part of `scripts/qualify_release.py` as the `CI workflow contract` gate.

## 7. Test-suite evolution

Four real workflow-contract tests were added:

```text
test_current_workflows_satisfy_canonical_contract
test_ci_contract_rejects_redundant_full_qualifier
test_ci_contract_requires_complete_python_matrix
test_security_contract_rejects_legacy_action_generations
```

The Bootstrap suite therefore evolves from 25 tests after LOT-00.5 to **29 tests** after LOT-00.6.

Validated CI result:

```text
Python 3.11  PASS - 29 tests
Python 3.12  PASS - 29 tests
Python 3.13  PASS - 29 tests
```

A Python 3.12 job reported:

```text
collected 29 items
29 passed
```

## 8. Canonical CI validation evidence

Validated implementation head before this evidence-only commit:

```text
bdc13a5345164c843793a5aab850f34e2354ffda
```

GitHub Actions CI run `#22` completed with:

```text
Quality gates           PASS
Tests - Python 3.11     PASS
Tests - Python 3.12     PASS
Tests - Python 3.13     PASS
Package qualification   PASS
Canonical CI gate       PASS
CI workflow             PASS
```

The final `Canonical CI gate` was created only after all upstream jobs had completed, then passed its explicit dependency assertions.

## 9. Security validation evidence

The hardened Security workflow completed successfully on the same implementation head:

```text
Dependency audit          PASS
Static security analysis PASS
Security workflow         PASS
```

Both jobs executed with `contents: read`, `checkout@v7`, `setup-python@v7`, cache support and explicit timeouts.

## 10. Non-duplication decision

CI no longer executes the complete release qualifier in parallel with separate test/package jobs.

The intended split is now:

```text
CI quality job  -> focused static qualifier
CI test job     -> supported Python matrix
CI package job  -> one package qualification
Local/release   -> full qualify_release.py when a complete release gate is needed
```

This preserves one source of engineering gate logic while avoiding repeated expensive work in ordinary PR CI.

## 11. Out of scope

LOT-00.6 deliberately does not:

- alter the tag or PyPI publishing workflow;
- publish or tag `v0.0.1`;
- configure release Trusted Publishing;
- introduce artifact signing or attestations;
- change resource/licensing governance;
- implement accounting-domain behavior.

Those concerns remain assigned to later remediation lots, especially `LOT-00.7 - Release Hardening` and `LOT-00.8 - Resources & Legal Governance`.

## 12. Exit decision

LOT-00.6 satisfies its exit criteria:

- canonical CI responsibilities are separated;
- duplicate full qualification has been removed from CI;
- Python 3.11/3.12/3.13 all pass 29 tests;
- package verification executes once and passes;
- Quality gates pass;
- Security passes;
- the final aggregate `Canonical CI gate` passes;
- pip cache is operational;
- workflow contracts are executable and negative-tested;
- modern stable GitHub runtime actions are used;
- no accounting behavior was introduced.

**Decision: LOT-00.6 COMPLETE, subject to the final CI/Security run on the evidence commit itself.**

The next remediation lot is `LOT-00.7 - Release Hardening`.
