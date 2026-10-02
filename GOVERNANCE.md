# PyAccountingKit Governance

This document defines repository-side governance for PyAccountingKit.

## Maintainer responsibility

The repository owner and current default code owner is:

```text
@tawounfouet
```

CODEOWNERS is an ownership and review-routing mechanism. It does not replace GitHub branch
protection or repository rulesets.

## Change path

Normal changes should follow:

```text
branch
  -> pull request
  -> canonical CI
  -> security checks
  -> reviewed merge
```

Direct mutation of release evidence, protected snapshots, regulatory source bundles or published
manifests is not an accepted normal workflow.

## Required repository checks

Before merging a change intended for `main`, the repository expects:

```text
Canonical CI gate
Dependency audit
Static security analysis
```

The canonical CI gate already aggregates the applicable quality, Python, package, PostgreSQL,
regulatory and CFA FRA gates.

## High-governance changes

The following changes require explicit review of their dedicated contracts:

### Release and supply chain

Paths:

```text
.github/workflows/release.yml
scripts/prepare_release.py
scripts/verify_package.py
```

Requirements:

- preserve fail-closed release qualification;
- preserve exact tag/version identity;
- preserve build-once publication;
- preserve OIDC-only PyPI publication;
- preserve release artifact integrity checks.

### Resource and provenance changes

Paths:

```text
resources/
RESOURCE_GOVERNANCE.json
THIRD_PARTY_NOTICES.md
```

Requirements:

- provenance review;
- rights-status review;
- tree fingerprint update;
- bundle-local checksum/manifest review;
- no production, confidential or personal data;
- no package/runtime inclusion of repository evidence.

### Public contracts

Paths include:

```text
PUBLIC_API_MANIFEST.json
PUBLIC_ERROR_CODES.json
ADAPTER_CONTRACT_MANIFEST.json
REGULATORY_COMPATIBILITY_MATRIX.json
```

Generated or reviewed contract files must not be edited to conceal an implementation drift.

## Resource immutability

A resource bundle is pinned by its Git tree SHA. If any byte under a governed resource directory
changes, `scripts/validate_resource_governance.py` requires a reviewed fingerprint update.

This does not establish copyright ownership or redistribution permission. Rights status is a
separate field and must remain explicit.

## Merge policy

Preferred merge method:

```text
squash
```

A merge should preserve one reviewable repository state per pull request. Force-pushes and branch
deletion of `main` should be disabled by repository settings.

## Release policy

A release tag must be created from a commit reachable from `main` and must equal the canonical
package version:

```text
v<pyproject.toml version>
```

The release workflow, not a local workstation, is the publication authority.

## External GitHub enforcement

Repository files can define the intended governance contract but cannot themselves activate
GitHub branch protection.

Target server-side settings for `main` are:

- require pull requests before merge;
- require the canonical CI and security checks;
- block force pushes;
- block branch deletion;
- require conversations to be resolved where applicable;
- preserve squash merge as the normal integration path.

The current server-side enforcement state must be verified independently before final
qualification. Repository documentation must not claim that branch protection is active merely
because CODEOWNERS or this document exists.
