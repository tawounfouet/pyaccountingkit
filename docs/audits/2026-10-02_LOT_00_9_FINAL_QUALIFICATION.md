# LOT-00.9 - Final Qualification

> Project: PyAccountingKit  
> Historical lot: `LOT-00 - Repository Bootstrap & Architecture Safety Net`  
> Historical release target: `0.0.1`  
> Repository line qualified here: `0.7.0b1 / LOT-27`  
> Validation date: 2026-10-02

## 1. Purpose

LOT-00.9 closes the remediation sequence by reconciling the historical Repository Bootstrap plan
with the repository that actually exists today.

The qualification does **not** rewind PyAccountingKit to `0.0.1`. The historical target remains
documentation of the bootstrap milestone; the current repository remains on `0.7.0b1`.

The final decision is deliberately fail-closed:

```text
repository controls      PASS
canonical CI             PASS
security                  PASS
package qualification    PASS
resource governance      PASS
release hardening        PASS

GitHub main protection   NOT ENFORCED

LOT-00.9                  BLOCKED_EXTERNAL_CONTROL
LOT-00 overall            BLOCKED_EXTERNAL_CONTROL
```

## 2. Post-LOT-00.8 baseline

The starting `main` state for this final qualification was:

```text
0507087d6d9187892240b514728c7cb895610683
version: 0.7.0b1
```

That exact post-merge main commit was independently exercised by GitHub Actions:

```text
CI #532
run id 37027268622
status PASS
Canonical CI gate PASS

Security #535
run id 37027269205
status PASS
Dependency audit PASS
Static security analysis PASS
```

This proves that LOT-00.8 was not only green as a pull request but remained green after landing on
the default branch.

## 3. Remediation closure ledger

The machine-readable record:

```text
docs/audits/LOT_00_REMEDIATION_STATUS.json
```

pins the completed remediation sequence:

```text
LOT-00.1  Documentation Traceability Cleanup   COMPLETE
LOT-00.2  Version & Metadata Alignment         COMPLETE
LOT-00.3  Repository & Scaffold Cleanup        COMPLETE
LOT-00.4  Engineering Safety                   COMPLETE
LOT-00.5  Bootstrap Test Suite                 COMPLETE
LOT-00.6  CI Hardening                         COMPLETE
LOT-00.7  Release Hardening                    COMPLETE
LOT-00.8  Resources & Governance               COMPLETE
LOT-00.9  Final Qualification                  BLOCKED_EXTERNAL_CONTROL
```

The first two sublots share the historical remediation merge
`64e4db862959956ae0cb64c2a7b1fc9c1436f6fd`. Later sublots retain their individual merge
commits and versioned audit documents.

## 4. Executable truthfulness gate

Added:

```text
scripts/validate_lot00_remediation_status.py
tests/unit/test_lot00_remediation_status.py
```

The validator checks:

- exact coverage of `LOT-00.1 → LOT-00.9`;
- immutable `COMPLETE` status for LOT-00.1 through LOT-00.8;
- valid merge SHAs and existing audit evidence;
- PASS repository-control baseline;
- PASS CI/Security baseline evidence;
- required branch-protection policy;
- explicit open blocker while protection is observed false;
- absence of invented tag/publication/stable-release claims;
- presence of the repository governance, CI, release and package-hardening artifacts.

Normal consistency validation is expected to pass:

```bash
python scripts/validate_lot00_remediation_status.py
```

Current expected result:

```text
LOT-00 remediation status validation: PASS
Overall status: BLOCKED_EXTERNAL_CONTROL
LOT-00 final acceptance: pending external control
```

The explicit final-acceptance command is stricter:

```bash
python scripts/validate_lot00_remediation_status.py --require-complete
```

While branch protection is not enforced it intentionally returns exit code `2` and reports:

```text
MAIN_BRANCH_PROTECTION_UNENFORCED
```

That non-zero result is the correct current outcome; it is not bypassed or converted into a false
PASS.

## 5. Pull-request qualification of the mechanism

Validated implementation head before this audit document:

```text
89ea5021cb5f10edb1cc10dcadbe4d724a054504
```

GitHub Actions:

```text
CI #534
run id 37037945429

Quality gates                              PASS
LOT-00 remediation status                 PASS
Package qualification                     PASS
Python 3.11 matrix                         PASS
Python 3.12 matrix                         PASS
Python 3.13 matrix                         PASS
Django/PostgreSQL qualification            PASS
SQLAlchemy/PostgreSQL qualification        PASS
Regulatory capability qualification        PASS
CFA FRA consumer/cutover/retirement gates PASS
Canonical CI gate                          PASS
```

Python 3.12 executed:

```text
922 passed
4 skipped
```

The four skips are the generic-matrix PostgreSQL adapter exclusions; those paths are exercised by
their dedicated PostgreSQL jobs.

Security:

```text
Security #537
run id 37037945335

Dependency audit          PASS
Static security analysis  PASS
Security workflow         PASS
```

## 6. External GitHub control observation

GitHub branch metadata for `main` currently reports:

```text
protected: false
protection.enabled: false
required status-check enforcement: off
```

The desired server-side policy is already documented in `GOVERNANCE.md`:

- require pull requests before merge;
- require `Canonical CI gate`;
- require the Security checks;
- block force pushes;
- block deletion of `main`;
- keep squash merge as the normal integration path.

The connected GitHub capability used for this implementation exposes read access to this state but
does not expose a branch-protection/ruleset write operation. Therefore the repository must not
claim that this control was enabled by LOT-00.9.

## 7. Release/publication inventory

At qualification time GitHub reports:

```text
tags: []
releases: []
```

LOT-00.9 creates none of the following:

- Git tag;
- GitHub Release;
- PyPI publication;
- `0.7.0` stable promotion;
- retroactive `0.0.1` publication.

The final qualification is repository governance, not a release event.

## 8. Documentation reconciliation

`PLAN-00_REPOSITORY_BOOTSTRAP_0.0.1.md` now preserves `0.0.1` as the historical target while
recording the actual remediation state at `0.7.0b1`.

`docs/plans/README.md` no longer describes PLAN-00 merely as an initial G0 foundation; it exposes
the current external closure blocker.

`CHANGELOG.md` records the final-qualification mechanism under `Unreleased`.

## 9. Completion procedure after the external control is enabled

After `main` branch protection or an equivalent ruleset is enabled:

1. independently re-read GitHub branch/ruleset state;
2. verify PR-required merging;
3. verify required `Canonical CI gate` and Security checks;
4. verify force pushes are blocked;
5. verify branch deletion is blocked;
6. update `LOT_00_REMEDIATION_STATUS.json`:
   - `observed_protected=true`;
   - close `MAIN_BRANCH_PROTECTION_UNENFORCED`;
   - set `LOT-00.9.status=COMPLETE`;
   - set `overall_status=COMPLETE`;
7. run:
   ```bash
   python scripts/validate_lot00_remediation_status.py --require-complete
   ```
8. require canonical CI and Security green again on the exact reviewed head.

Only then may LOT-00 be declared fully closed.

## 10. Decision

Repository-side final qualification is implemented and qualified.

The final acceptance condition is **not** satisfied because the required GitHub server-side
protection is not currently enforced.

**Decision: LOT-00.9 = BLOCKED_EXTERNAL_CONTROL.**

**Decision: LOT-00 remains OPEN only on `MAIN_BRANCH_PROTECTION_UNENFORCED`.**

This is a deliberate fail-closed result, not an implementation failure.
