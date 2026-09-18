# LOT-22 — Extension API, Manifests & Compatibility Contracts

**Target:** `0.5.0a2`  
**Baseline:** LOT-21 / `0.5.0a1` at `fae059c074d08369cec94de19b6347bfaf83e72e`

## Objective

Publish a separate, versioned adapter-author extension API without widening the ordinary
`AccountingApplication` user surface and without implementing the Django/PostgreSQL or
SQLAlchemy/PostgreSQL adapters reserved for LOT-23/24.

## Extension surface

```text
pyaccountingkit.public.protocols
├── AdapterContractVersion
├── ADAPTER_CONTRACT_VERSION
├── RuntimeCapabilities
├── runtime_capabilities
├── require_adapter_contract
├── UnitOfWorkProtocol
├── UnitOfWorkFactoryProtocol
├── AccountingReferenceProviderProtocol
├── RegulatoryRendererProtocol
└── RegulatoryExporterProtocol
```

The package root does not export these adapter-author symbols.

## Adapter contract v1

The initial public adapter contract version is `1`.

Compatibility is fail-closed:

```text
adapter supported versions
        |
        v
contains framework contract v1?
    | yes       | no
    v           v
  accept   AdapterContractMismatchError
```

A contract-version mismatch is not inferred from implementation details or dependency versions.

## Runtime capabilities

Runtime capability detection:

- uses `importlib.util.find_spec`;
- never imports Django or SQLAlchemy merely to detect them;
- exposes the current adapter-contract version;
- exposes whether `py.typed` is packaged;
- is immutable and framework-neutral.

Missing optional integrations raise `OptionalDependencyMissingError` when explicitly required.

## Deterministic manifests

LOT-22 turns the existing generator stubs into executable contracts:

```text
scripts/generate_public_api_manifest.py --check
scripts/generate_error_codes_manifest.py --check
scripts/generate_adapter_contract_manifest.py --check
```

Generation is canonical JSON with sorted keys and stable indentation. `--check` fails if the
committed artifact differs byte-for-byte from the generated representation.

The release qualifier runs all three checks as part of Quality gates.

## Boundaries

LOT-22 does not:

- add or qualify Django/PostgreSQL persistence;
- add or qualify SQLAlchemy/PostgreSQL persistence;
- expose ORM objects through public protocols;
- change accounting-domain semantics;
- freeze the whole Python API before LOT-29;
- declare any production adapter.

## DoD

```text
[ ] extension API separate from user API
[ ] public protocol symbol list explicit
[ ] adapter contract version = 1
[ ] runtime capabilities immutable and no-import
[ ] manifest generation deterministic
[ ] manifest --check integrated into canonical Quality gate
[ ] optional extras do not affect core import
[ ] adapter mismatch produces typed error
[ ] py.typed remains packaged
[ ] retained LOT-21 GAPI and 0.4 qualification green
[ ] Python 3.11/3.12/3.13, Ruff, mypy, package, Security green
```
