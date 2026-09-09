#!/usr/bin/env bash
set -euo pipefail
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[pdf,dev]"
pytest -q
regdata standard-list
