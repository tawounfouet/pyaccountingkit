## Scope

Describe the change and the release/lot it belongs to.

## Evidence

- [ ] Canonical CI is green for the final head.
- [ ] Security checks are green for the final head.
- [ ] User-visible/versioned contract changes are documented.

## Architecture / accounting

- [ ] No forbidden framework dependency was introduced into the domain.
- [ ] Accounting or regulatory behavior changes include appropriate tests/evidence.
- [ ] Public contract manifests were refreshed when applicable.

## Resources / provenance

Check this section when `resources/`, source datasets or governed evidence changed.

- [ ] `RESOURCE_GOVERNANCE.json` was updated.
- [ ] The resource Git tree fingerprint was refreshed.
- [ ] Provenance and source checksums were reviewed.
- [ ] Rights/licensing status was reviewed without assuming the project MIT license applies.
- [ ] No production, confidential, credential-bearing or personal data was committed.
- [ ] Repository resources remain excluded from wheel and sdist artifacts.

## Release / supply chain

Check this section when release or packaging files changed.

- [ ] Tag/version fail-closed behavior is preserved.
- [ ] Release qualification still precedes build/publication.
- [ ] Distributions are built once and reverified before publication.
- [ ] PyPI authentication remains OIDC/Trusted Publishing only.
