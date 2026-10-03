'''Tests for the fail-closed G5 stable-release validator.'''

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts' / 'validate_stable_gate.py'


def _load_module() -> ModuleType:
    name = 'pyaccountingkit_stable_gate_test'
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _qualification(status: str, executable: bool) -> dict[str, object]:
    return {
        'status': status,
        'executable': executable,
        'auto_inference_allowed': False,
    }


def _fixture(root: Path, *, blocker: bool = False, version: str = '0.7.0') -> None:
    (root / 'pyproject.toml').write_text(
        f'[project]\nname = "pyaccountingkit"\nversion = "{version}"\n',
        encoding='utf-8',
    )

    documents = {
        'README.md': f'PyAccountingKit **{version}**\n',
        'CHANGELOG.md': f'## [{version}] - 2026-10-03\n',
        'docs/plans/LOT-27_REGULATORY_PRODUCTION_QUALIFICATION_PLAN.md': (
            f'**Current slice:** `{version}`\n'
        ),
        'docs/plans/RELEASE_0.7.0_STABLE_PROMOTION_PLAN.md': 'Migration impact: none\n',
        'docs/audits/2026-10-03_LOT_27_RC1_QUALIFICATION.md': '# RC1\n',
    }
    for relative, body in documents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding='utf-8')

    _write_json(
        root / 'docs/audits/LOT_00_REMEDIATION_STATUS.json',
        {
            'overall_status': 'BLOCKED_EXTERNAL_CONTROL' if blocker else 'COMPLETE',
            'sublots': [
                {
                    'id': 'LOT-00.9',
                    'status': 'BLOCKED_EXTERNAL_CONTROL' if blocker else 'COMPLETE',
                }
            ],
            'external_controls': {
                'main_branch': {'observed_protected': not blocker},
            },
            'blockers': (
                [
                    {
                        'id': 'MAIN_BRANCH_PROTECTION_UNENFORCED',
                        'status': 'OPEN',
                    }
                ]
                if blocker
                else []
            ),
        },
    )

    _write_json(
        root / 'PUBLIC_API_MANIFEST.json',
        {
            'version': version,
            'public_api': {'stability': 'pre-1.0-stable-release'},
        },
    )
    for name in (
        'PUBLIC_ERROR_CODES.json',
        'ADAPTER_CONTRACT_MANIFEST.json',
        'SNAPSHOT_SCHEMA_MANIFEST.json',
    ):
        _write_json(root / name, {'version': version})

    _write_json(
        root / 'REGULATORY_COMPATIBILITY_MATRIX.json',
        {
            'version': version,
            'regulatory_frameworks': [
                {
                    'standard_ref': 'cemac-pcemf:2010',
                    'capabilities': {
                        'CROSSWALKS': _qualification('NOT_ASSERTED', False),
                    },
                },
                {
                    'standard_ref': 'fr-nonprofit:2026',
                    'capabilities': {
                        'REPORTING_STRUCTURE': _qualification('PRODUCTION_QUALIFIED', True),
                        'REPORTING_ACCOUNT_MAPPINGS': _qualification('REVIEW_REQUIRED', False),
                    },
                },
                {
                    'standard_ref': 'fr-pcg:2026',
                    'capabilities': {
                        'REPORTING_STRUCTURE': _qualification('PRODUCTION_QUALIFIED', True),
                        'REPORTING_ACCOUNT_MAPPINGS': _qualification('REVIEW_REQUIRED', False),
                    },
                },
                {
                    'standard_ref': 'ohada-ebnl:2023',
                    'capabilities': {
                        'REPORTING_STRUCTURE': _qualification('DISCOVERED', False),
                        'CROSSWALKS': _qualification('REVIEW_REQUIRED', False),
                    },
                },
                {
                    'standard_ref': 'ohada-syscohada:2017',
                    'capabilities': {
                        'REPORTING_STRUCTURE': _qualification('PRODUCTION_QUALIFIED', True),
                        'REPORTING_ACCOUNT_MAPPINGS': _qualification('REVIEW_REQUIRED', False),
                    },
                },
            ],
        },
    )


def test_clean_stable_fixture_passes(tmp_path: Path) -> None:
    module = _load_module()
    _fixture(tmp_path)

    assert module.stable_gate_violations(root=tmp_path) == []


def test_open_external_blocker_fails_g5(tmp_path: Path) -> None:
    module = _load_module()
    _fixture(tmp_path, blocker=True)

    violations = module.stable_gate_violations(root=tmp_path)

    assert any('0 BLOCKER' in item for item in violations)
    assert any('main branch protection' in item for item in violations)


def test_prerelease_identity_cannot_pass_stable_gate(tmp_path: Path) -> None:
    module = _load_module()
    _fixture(tmp_path, version='0.7.0rc1')

    violations = module.stable_gate_violations(root=tmp_path)

    assert any('exact stable target 0.7.0' in item for item in violations)


def test_review_required_mapping_cannot_become_executable(tmp_path: Path) -> None:
    module = _load_module()
    _fixture(tmp_path)
    path = tmp_path / 'REGULATORY_COMPATIBILITY_MATRIX.json'
    payload = json.loads(path.read_text(encoding='utf-8'))
    pcg = next(
        item
        for item in payload['regulatory_frameworks']
        if item['standard_ref'] == 'fr-pcg:2026'
    )
    pcg['capabilities']['REPORTING_ACCOUNT_MAPPINGS']['executable'] = True
    _write_json(path, payload)

    violations = module.stable_gate_violations(root=tmp_path)

    assert any('REVIEW_REQUIRED must remain non-executable' in item for item in violations)
