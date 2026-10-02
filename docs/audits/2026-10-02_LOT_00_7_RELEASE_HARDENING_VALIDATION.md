# LOT-00.7 - Release Hardening Validation

> Project: PyAccountingKit  
> Remediation lot: `LOT-00.7 - Release Hardening`  
> Repository line at implementation: `0.7.0b1`  
> Validation date: 2026-10-02

## 1. Context

The original Repository Bootstrap remediation sequence deferred release hardening until the
repository had executable CI and test gates.

By the time this lot was resumed, `main` had advanced to `0.7.0b1` / LOT-27. The remediation
therefore hardened the current release mechanism without rewinding package metadata or claiming a
historical `0.0.1` release.

No tag and no package publication were performed by this lot.

## 2. Risk closed

The previous workflow accepted any `v*` tag and immediately:

1. checked out the tagged source;
2. built distributions;
3. published to PyPI;
4. created a GitHub Release.

It did not enforce exact tag/version equality, main-branch ancestry, repository qualification,
build-once artifact identity, checksums, or re-verification before publication.

## 3. Hardened release topology

The release pipeline is now:

```text
tag v*
  |
  v
preflight
  |- exact v<pyproject version>
  |- full commit SHA
  |- tagged commit reachable from origin/main
  |- fail-closed release qualification
  |
  v
build
  |- wheel + sdist built exactly once
  |- package verification
  |- RELEASE_QUALIFICATION_MANIFEST.json
  |- SHA256SUMS
  |- sealed GitHub Actions artifact
  |
  v
publish-pypi
  |- download sealed bundle
  |- recompute identity + SHA-256
  |- OIDC / Trusted Publishing only
  |
  v
github-release
  |- waits for successful PyPI publication
  |- downloads the same sealed bundle
  |- recomputes identity + SHA-256 again
  |- attaches wheel, sdist, checksums and qualification manifest
```

## 4. Release identity rules

`scripts/prepare_release.py` fails closed unless:

- the project name is `pyaccountingkit`;
- the version is a supported `X.Y.Z`, `aN`, `bN` or `rcN` version;
- the Git tag is exactly `v<version>`;
- the commit SHA is a full lowercase 40-character SHA;
- during the real tag workflow, the tagged commit is reachable from `origin/main`.

The current package line `0.7.0b1` is therefore expected to use `v0.7.0b1`; no such tag is
created by this lot.

## 5. Build-once and artifact integrity

The release build creates exactly one wheel and one sdist through the existing package verifier.

The sealed bundle has two namespaces:

```text
release-bundle/
  dist/
    pyaccountingkit-<version>-*.whl
    pyaccountingkit-<version>.tar.gz
  metadata/
    SHA256SUMS
    RELEASE_QUALIFICATION_MANIFEST.json
```

Both publication jobs recalculate:

- expected tag/version/SHA identity;
- wheel SHA-256 and byte size;
- sdist SHA-256 and byte size;
- exact `SHA256SUMS` contents.

Any byte mutation after the build job therefore blocks the next publication boundary.

## 6. Authentication and permissions

PyPI publication uses a dedicated `pypi` GitHub environment with:

```text
contents: read
id-token: write
```

No PyPI password, token, `skip-existing`, alternate repository URL or direct Twine upload is
allowed by the executable workflow contract.

GitHub Release receives `contents: write` only in its own final job.

## 7. Action baseline

The release workflow was aligned to the current stable action releases checked during this lot:

```text
actions/checkout@v7.0.1
actions/setup-python@v7.0.0
actions/upload-artifact@v7.0.1
actions/download-artifact@v8.0.1
pypa/gh-action-pypi-publish@v1.14.2
softprops/action-gh-release@v3.0.3
```

The exact versions are part of `scripts/validate_ci.py` and must be changed through a reviewed PR
rather than drifting silently.

## 8. Executable contract tests

The CI workflow validator now covers `release.yml` in addition to `ci.yml` and
`security.yml`.

New negative tests prove rejection of:

- publication without `qualify_release.py --release-candidate`;
- secret/password-based PyPI authentication;
- rebuilding distributions after the sealed build boundary;
- tag/version mismatch;
- malformed commit SHA;
- post-build distribution tampering;
- checksum-file tampering.

Prerelease classification is tested for alpha, beta and RC versions, with stable releases kept
non-prerelease.

## 9. Validation evidence

Validated implementation head before this audit document:

```text
f3c492360312c853db25b60cebad89858012c12b
```

GitHub Actions CI run:

```text
run #523
run id 37023302944

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
907 passed
4 skipped
```

The four skips are the real PostgreSQL adapter tests disabled in the generic matrix; those adapter
paths are exercised by their dedicated PostgreSQL service jobs.

The extended `release/*` qualification job was correctly `SKIPPED` because this PR is not a
release branch.

Security run:

```text
run #526
run id 37023303600

Dependency audit          PASS
Static security analysis  PASS
```

## 10. Publication non-evidence

This lot does **not** claim:

- that `v0.7.0b1` exists;
- that PyPI Trusted Publishing has already been exercised successfully for this project;
- that a PyPI project/environment configuration has been externally verified;
- that a GitHub Release has been created;
- that `0.7.0` is stable.

Those facts can only be established by a later real release event.

## 11. Exit decision

The release mechanism is now fail-closed at repository level:

- release identity is validated;
- strongest repository qualification precedes build;
- distributions are built once;
- artifact checksums are generated;
- publication boundaries reverify the same bytes;
- PyPI uses OIDC-only workflow credentials;
- GitHub Release cannot precede successful PyPI publication;
- release workflow invariants are protected by normal PR CI.

**Decision: LOT-00.7 COMPLETE as repository release hardening.**

The next remediation lot is `LOT-00.8 - Resources & Governance`.
