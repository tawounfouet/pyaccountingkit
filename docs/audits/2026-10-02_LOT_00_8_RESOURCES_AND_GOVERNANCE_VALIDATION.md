# LOT-00.8 - Resources & Governance Validation

> Project: PyAccountingKit  
> Remediation lot: `LOT-00.8 - Resources & Governance`  
> Repository line at implementation: `0.7.0b1 / LOT-27`  
> Validation date: 2026-10-02

## 1. Objective

Close the repository-level governance gap around embedded resource snapshots, third-party or
regulatory source material, source-distribution packaging and contribution/review rules.

This lot does not alter accounting or regulatory runtime behavior.

## 2. Resource inventory discovered

The repository contains two direct governed resource bundles.

### CFA FRA Sprint-7 behavioral oracle

```text
path: resources/cfa_fra_django_mvp_sprint_7
manifest project: cfa_fra_django_mvp_sprint_7
manifest version: 0.8.0
Git tree: 07d4880534d2e2239e19fd4ef4139de70b56773a
tracked blobs: 265
tracked bytes: 776,730
PDF files: 0
```

Role:

```text
BEHAVIORAL_ORACLE
```

It remains a frozen migration/parity reference, not a runtime dependency.

### Regulatory Accounting Data Framework snapshot

```text
path: resources/regulatory-accounting-data-framework
manifest project: regulatory-accounting-data-framework
manifest version: 0.7.1
Git tree: f6f05c8f2fe8397e4ebb80707ebeed6497e53e98
tracked blobs: 299
tracked bytes: 134,162,396
PDF files: 12
PDF bytes: 104,647,884
```

This bundle includes source material associated with ANC, OHADA, COBAC/CEMAC and an ORCOM
practitioner reference, in addition to derived datasets/transcriptions.

No single uniform license is declared by the embedded bundle. The repository therefore records
the rights state as:

```text
MIXED_OR_UNASSERTED_REVIEW_REQUIRED
```

This status is intentionally conservative. It does not claim that official or practitioner
documents are MIT-licensed merely because they are present in a repository whose project code uses
MIT.

## 3. Canonical governance registry

Added:

```text
RESOURCE_GOVERNANCE.json
```

For every direct `resources/*` directory, the registry now records:

- bundle identity;
- path;
- role;
- pinned Git tree SHA;
- bundle-local manifest identity/version;
- third-party-source flag;
- rights status;
- redistribution status;
- package inclusion policy;
- runtime dependency policy;
- immutable-snapshot policy.

A new direct resource directory without a governance entry is a CI failure.

Any byte change to a governed resource bundle changes its Git tree SHA and therefore requires an
explicit registry update in the same reviewed change.

## 4. Rights and provenance boundary

Added:

```text
THIRD_PARTY_NOTICES.md
resources/README.md
```

The repository now states explicitly that the root MIT license must not be interpreted as silently
relicensing third-party, regulatory or practitioner source documents.

Derived transcriptions do not implicitly change the rights attached to their source documents.

External repackaging of material whose rights are mixed or unasserted requires a separate review.

## 5. Executable resource governance

Added:

```text
scripts/validate_resource_governance.py
```

The gate validates:

- registry schema;
- exact coverage of direct resource directories;
- unique bundle IDs and paths;
- pinned Git tree SHA;
- embedded manifest project/version identity;
- explicit rights status;
- third-party bundle fail-closed rights status;
- package exclusion;
- runtime-dependency exclusion;
- immutable-in-place policy;
- required governance files.

The gate is now part of:

```text
scripts/qualify_release.py
```

and therefore executes inside the canonical `Quality gates` CI job.

## 6. Packaging boundary

Before this lot, the wheel verifier already rejected `resources/`, but the source-distribution
contract did not explicitly forbid repository evidence.

The first implementation attempt proved that `data/cache/.gitkeep`,
`data/generated/.gitkeep` and `data/local/.gitkeep` still leaked into the sdist.

The final Hatch configuration now excludes recursively:

```text
/resources/**
/data/**
```

The package verifier rejects either tree if it reappears inside a future sdist.

`THIRD_PARTY_NOTICES.md` is required in the sdist so the source package preserves the repository's
rights boundary even though the governed resource payloads themselves are absent.

## 7. Negative tests

The test suite now proves rejection of:

- unregistered resource directories;
- resource-tree fingerprint drift;
- false project-MIT treatment of a third-party source bundle;
- resource package inclusion;
- resource runtime dependency;
- embedded resource manifest version drift;
- governed resource leakage into an sdist;
- missing recursive Hatch resource/data exclusions.

An older hand-built sdist fixture was updated to include the newly required
`THIRD_PARTY_NOTICES.md`; the verifier contract was not weakened.

## 8. Repository governance artifacts

Added:

```text
GOVERNANCE.md
.github/CODEOWNERS
.github/pull_request_template.md
```

The repository now documents:

- the expected branch -> PR -> CI -> security -> merge path;
- high-governance release/supply-chain changes;
- resource/provenance/rights review;
- public contract manifest governance;
- preferred squash merge policy;
- expected server-side protection for `main`.

`CONTRIBUTING.md` and `README.md` were aligned with the new resource and licensing boundary.

## 9. Validation evidence

Validated functional head:

```text
620851c86098bc06b28b39a183e3f98086d3f34b
```

GitHub Actions CI:

```text
run #530
run id 37026413601

Quality gates                              PASS
Resource governance                       PASS
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
916 passed
4 skipped
```

The four generic-matrix skips are the PostgreSQL adapter tests exercised by their dedicated real
PostgreSQL jobs.

Security:

```text
run #533
run id 37026414036

Dependency audit          PASS
Static security analysis  PASS
Security workflow         PASS
```

## 10. External GitHub enforcement

The repository files now define the desired branch-governance contract, but server-side protection
is a separate GitHub setting.

At the time of this lot, `main` is reported by GitHub as:

```text
protected: false
```

The connected GitHub capability available to this implementation can read that state but does not
expose a branch-protection/ruleset write operation.

Therefore this lot makes **no false claim** that branch protection was enabled.

Required LOT-00.9 verification:

- confirm or enable PR-required protection for `main`;
- require the canonical CI gate;
- require security checks;
- block force pushes;
- block deletion of `main`;
- confirm merge-policy settings.

## 11. Non-goals and non-evidence

This lot does not claim:

- ownership or redistribution rights for regulatory/practitioner source documents;
- that every embedded source has one common license;
- that GitHub branch protection is active;
- that a package release was published;
- that `0.7.0` is stable.

No governed resource snapshot content was modified by this lot.

## 12. Exit decision

Repository-side resource and governance controls are complete:

- resource inventory is explicit;
- resource snapshot identity is pinned;
- rights uncertainty is explicit and fail-closed;
- package and runtime inclusion are forbidden;
- wheel/sdist boundaries are executable;
- contribution/review governance is documented;
- canonical CI and Security are green.

**Decision: LOT-00.8 COMPLETE for repository-side governance.**

The remaining server-side branch-protection control is explicit evidence for
`LOT-00.9 - Final Qualification`, not a hidden assumption.
