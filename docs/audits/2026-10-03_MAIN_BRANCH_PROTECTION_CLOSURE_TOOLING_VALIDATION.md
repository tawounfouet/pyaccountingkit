# Main Branch Protection Closure Tooling Validation

> Project: PyAccountingKit  
> Date: 2026-10-03  
> Context: LOT-00.9 external blocker closure  
> Current blocker: `MAIN_BRANCH_PROTECTION_UNENFORCED`

## 1. Objective

Provide an executable, reviewable and fail-closed path to resolve the only remaining LOT-00
external control without pretending that GitHub branch protection has already been enabled.

The tooling does **not** change accounting behavior, package version, release state or regulatory
qualification.

## 2. Administrative boundary

The connected GitHub integration available during this implementation exposes branch-protection
state only in read mode. It does not expose an administration write operation.

Therefore the repository now contains a dedicated administration script that can be run only with
an explicit GitHub credential having repository `Administration: write` permission.

The normal GitHub Actions token is not used for this operation.

## 3. Canonical protection policy

`scripts/configure_main_branch_protection.py` applies and verifies:

```text
repository                         tawounfouet/pyaccountingkit
branch                             main
strict status checks               required
required check                     Canonical CI gate
required check                     Dependency audit
required check                     Static security analysis
pull request before merge          required
required approving reviews         0
admin enforcement                  enabled
force pushes                       disabled
branch deletion                    disabled
conversation resolution            required
linear history                     required
```

The zero-review setting is intentional for the current single-maintainer repository. It preserves
the pull-request and automated-gate boundary without creating a self-approval deadlock.

## 4. Commands

Apply:

```bash
export PYAK_GITHUB_ADMIN_TOKEN="<fine-grained-token>"
python scripts/configure_main_branch_protection.py apply
```

Verify later:

```bash
python scripts/configure_main_branch_protection.py check
```

Promote LOT-00 only after the live check passes:

```bash
python scripts/configure_main_branch_protection.py promote-status
python scripts/validate_lot00_remediation_status.py --require-complete
```

## 5. Fail-closed status promotion

The status promotion refuses to run unless the live protection response proves every required
server-side control.

A successful promotion changes only the LOT-00 closure evidence:

```text
observed_protected                            true
MAIN_BRANCH_PROTECTION_UNENFORCED             CLOSED
LOT-00.9                                      COMPLETE
LOT-00 overall                                COMPLETE
```

Release claims remain unchanged and false:

```text
tag created                                   false
GitHub Release created                        false
PyPI publication claimed                      false
stable 0.7.0 claimed                          false
```

## 6. Negative tests

The unit suite verifies rejection of:

- missing `Canonical CI gate`;
- enabled force pushes;
- enabled branch deletion;
- disabled admin enforcement;
- missing pull-request requirement;
- status promotion from a non-compliant protection payload.

It also verifies that successful status promotion closes only the external blocker and leaves every
release/publication claim false.

## 7. GitHub API contract

The implementation targets the versioned GitHub branch-protection REST API:

```text
X-GitHub-Api-Version: 2026-03-10
PUT /repos/{owner}/{repo}/branches/{branch}/protection
GET /repos/{owner}/{repo}/branches/{branch}/protection
```

The script requires:

```text
PYAK_GITHUB_ADMIN_TOKEN
```

and deliberately fails if it is absent.

## 8. Functional qualification

Validated implementation head before this audit document:

```text
ca0c2006fa921601021d1b155e1df2a3b4c7addc
```

GitHub Actions CI:

```text
CI #540
run id 37106345180

Quality gates                              PASS
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
931 passed
4 skipped
```

Security:

```text
Security #543
run id 37106345178

Dependency audit          PASS
Static security analysis  PASS
Security workflow         PASS
```

## 9. External-control truthfulness

This tooling validation does **not** claim that branch protection is enabled.

Until an authorized administrator executes the apply/check flow and GitHub returns a compliant live
protection response:

```text
LOT-00.9       BLOCKED_EXTERNAL_CONTROL
LOT-00 overall BLOCKED_EXTERNAL_CONTROL
```

remains the only valid state.

## 10. Decision

The administrative closure tooling is implemented and qualified.

**Decision: closure tooling COMPLETE.**

**Decision: MAIN_BRANCH_PROTECTION_UNENFORCED remains OPEN until live GitHub administration is
performed and independently verified.**
