# Repository Resources

`resources/` contains **evidence and source snapshots**, not PyAccountingKit runtime package data.

The canonical governance registry is:

```text
RESOURCE_GOVERNANCE.json
```

Rights and attribution boundaries are documented in:

```text
THIRD_PARTY_NOTICES.md
```

## Current bundles

| Bundle | Role | Runtime dependency | Wheel inclusion | Rights status |
|---|---|---:|---:|---|
| `cfa_fra_django_mvp_sprint_7` | frozen behavioral oracle | no | forbidden | no separate license declaration |
| `regulatory-accounting-data-framework` | regulatory source/data snapshot | no | forbidden | mixed or unasserted; review required |

## Governance rules

1. Resource bundles are immutable snapshots. Do not silently edit them in place.
2. A bundle change requires its pinned Git tree SHA to be refreshed in
   `RESOURCE_GOVERNANCE.json`.
3. Bundle-local manifests and source checksums remain the source-specific provenance record.
4. The root MIT license does not override third-party or regulatory source terms.
5. Resource bundles must never be imported as mandatory PyAccountingKit runtime dependencies.
6. Resource bundles must never be included in the wheel.
7. Production, confidential, credential-bearing or personal data is forbidden.
8. A new direct child directory under `resources/` must receive a registry entry before CI passes.

The validation command is:

```bash
python scripts/validate_resource_governance.py
```
