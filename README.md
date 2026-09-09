# pyaccountingkit

A Python toolkit for double-entry accounting. It implements a hexagonal
architecture with a rich domain model, ports & adapters, and strict
accounting invariants.

## Status

Early scaffolding. Public API is not yet stable.

## Documentation

See the `docs/` folder for requirements, architecture, and design documents.

## Install

```bash
pip install -e .
```

## Development

```bash
pip install -e ".[dev]"
ruff check src/ tests/
mypy src/
pytest
```

## License

MIT
