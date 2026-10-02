# Contributing to pyaccountingkit

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quality gates

```bash
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
mypy src/
python scripts/validate_resource_governance.py
pytest tests/unit tests/property tests/contract
```

## Conventional commits

We follow [Conventional Commits](https://www.conventionalcommits.org/).

## Architecture

The project follows a hexagonal architecture. See the `docs/` folder for the
detailed architecture documents and `AGENTS.md` guidance.


## Resource and provenance changes

Treat `resources/` as governed evidence, not as an informal file drop.

A pull request that adds or changes a direct resource bundle must:

- update `RESOURCE_GOVERNANCE.json`;
- review the bundle's provenance and rights status;
- refresh the pinned Git tree SHA;
- preserve or refresh bundle-local source checksums and manifests;
- update `THIRD_PARTY_NOTICES.md` when the authority/rights boundary changes;
- keep the bundle out of the wheel and out of mandatory runtime dependencies.

Do not commit production accounting records, personal data, credentials, secrets or confidential
client material to `resources/` or `data/samples/`.
