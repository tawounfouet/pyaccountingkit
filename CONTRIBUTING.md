# Contributing to pyaccountingkit

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quality gates

```bash
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/
pytest tests/unit tests/property tests/contract
```

## Conventional commits

We follow [Conventional Commits](https://www.conventionalcommits.org/).

## Architecture

The project follows a hexagonal architecture. See the `docs/` folder for the
detailed architecture documents and `AGENTS.md` guidance.
