#!/usr/bin/env python3
"""Generate ADAPTER_CONTRACT_MANIFEST.json deterministically from contract metadata."""

from __future__ import annotations

import json

from manifest_generation import parse_check_flag, project_version, write_or_check

from pyaccountingkit.public.protocols import (
    ADAPTER_CONTRACT_VERSION,
    SUPPORTED_ADAPTER_CONTRACT_VERSIONS,
)

_FILENAME = "ADAPTER_CONTRACT_MANIFEST.json"
_LEGACY_CONTRACTS: dict[str, object] = json.loads(r"""{
  "unit_of_work": {
    "port": "UnitOfWorkProtocol",
    "reference_adapter": "InMemoryUnitOfWork",
    "qualified_behaviors": [
      "atomic_commit_rollback",
      "transaction_local_state",
      "optimistic_revision_conflict",
      "idempotency_conflict",
      "audit_outbox_atomicity"
    ],
    "production_qualification": true,
    "production_adapters": [
      "DjangoUnitOfWork"
    ],
    "qualification": "0.5.0b1-django-postgresql-qualified"
  },
  "company_chart_resolution": {
    "port": "CompanyChartResolverProtocol",
    "reference_adapter": "InMemoryVersionedCompanyChartResolver",
    "scope": [
      "entity_id",
      "accounting_date"
    ],
    "fail_closed": true
  },
  "account_role_resolution": {
    "port": "AccountRoleResolverProtocol",
    "reference_adapter": "InMemoryAccountRoleResolver",
    "scope": [
      "entity_id",
      "accounting_date",
      "company_chart_version"
    ],
    "fail_closed": true
  },
  "control_account_resolution": {
    "port": "ControlAccountResolverProtocol",
    "reference_adapter": "InMemoryControlAccountResolver",
    "scope": [
      "entity_id",
      "subledger_id",
      "accounting_date",
      "party_type",
      "currency"
    ],
    "chart_resolution": "CompanyChartResolverProtocol",
    "selection": "most-specific-fail-closed",
    "validates_account": [
      "present",
      "active",
      "postable",
      "entity-scoped"
    ],
    "trace": [
      "binding_id",
      "chart_id",
      "chart_version",
      "reference_snapshot_id"
    ],
    "qualification": "LOT-18-alpha-reused-by-LOT-19"
  },
  "accounting_references": {
    "port": "AccountingReferenceProviderProtocol",
    "status": "qualified_reference_contract"
  },
  "django_postgresql": {
    "adapter_contract_version": "1",
    "package": "pyaccountingkit.adapters.django",
    "package_extra": "django",
    "django_version": ">=5.2,<6",
    "database": "PostgreSQL 16",
    "unit_of_work": "DjangoUnitOfWork",
    "unit_of_work_factory": "DjangoUnitOfWorkFactory",
    "migration_baseline": "0001_initial",
    "public_api_orm_leakage": false,
    "qualified_behaviors": [
      "fresh_migration",
      "model_migration_coherence",
      "repository_round_trip",
      "atomic_commit_rollback",
      "optimistic_revision_conflict",
      "idempotency_conflict",
      "audit_outbox_atomicity",
      "double_reversal_serialization",
      "posting_close_serialization"
    ],
    "qualification": "0.5.0b1-production-qualified"
  },
  "accounting_import": {
    "ports": [
      "AccountingImportParser",
      "AccountingImportNormalizer",
      "ImportPeriodResolver"
    ],
    "source_format_neutral": true,
    "posting_path": "PostingOrchestrator",
    "specialized_adapters": [
      "FECAdapter"
    ],
    "stable_release_qualification": "source-to-evidence-cross-lot",
    "fec_fr": {
      "adapter": "FECAdapter",
      "adapter_version": "0.3.0a2",
      "format": "French FEC 18-column text export",
      "raw_preservation": true,
      "source_checksum": "sha256",
      "source_entry_identity": "JournalCode:EcritureNum",
      "duplicate_strategy": "warn-only-row-hash",
      "transaction_modes": [
        "ALL_OR_NOTHING",
        "PER_ITEM",
        "CHUNKED_ATOMIC"
      ],
      "posting_path": "PostingOrchestrator",
      "qualification": "0.3.0-stable-cross-lot-qualified"
    }
  },
  "reference_reporting_model": {
    "port": "ReferenceReportingModelProviderProtocol",
    "reference_adapter": "InMemoryReferenceReportingModelProvider",
    "coordinates": [
      "reference_snapshot_id",
      "framework",
      "edition",
      "model_code"
    ],
    "resolution": "exact-only",
    "fail_closed": true,
    "qualification": "0.3.0-stable-cross-lot-qualified"
  },
  "regulatory_renderer": {
    "port": "RegulatoryRendererProtocol",
    "reference_adapter": "CanonicalJSONRegulatoryRenderer",
    "input": "precomputed-RegulatoryReport",
    "recalculates_accounting": false,
    "deterministic_payload": true,
    "qualification": "0.3.0-stable-cross-lot-qualified"
  }
}""")


def build_payload() -> dict[str, object]:
    contracts = dict(_LEGACY_CONTRACTS)
    contracts["contract"] = {
        "current_version": str(ADAPTER_CONTRACT_VERSION),
        "supported_versions": [str(item) for item in SUPPORTED_ADAPTER_CONTRACT_VERSIONS],
        "extension_api": [
            "AccountingReferenceProviderProtocol",
            "RegulatoryExporterProtocol",
            "RegulatoryRendererProtocol",
            "UnitOfWorkFactoryProtocol",
            "UnitOfWorkProtocol",
        ],
        "production_adapters": ["django_postgresql"],
        "qualification": "LOT-23-django-postgresql-beta",
    }
    return {"version": project_version(), "adapter_contracts": contracts}


def main() -> int:
    check = parse_check_flag(__doc__ or "")
    return write_or_check(filename=_FILENAME, payload=build_payload(), check=check)


if __name__ == "__main__":
    raise SystemExit(main())
