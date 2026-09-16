"""Immutable regulatory-report projections built from sealed financial reports."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.reporting.reference_reporting_model import (
    ReferenceReportingValueType,
)


@dataclass(frozen=True, slots=True)
class RegulatoryNodeValue:
    """One projected regulatory node with explicit statement-line provenance."""

    node_id: str
    code: str
    label: str
    value_type: ReferenceReportingValueType
    amount: Money | None
    comparative_amount: Money | None
    source_statement_lines: tuple[str, ...]
    mapping_ids: tuple[str, ...]
    mapping_provenances: tuple[str, ...]
    human_validation_required: bool
    account_hints_executable: bool


@dataclass(frozen=True, slots=True)
class RegulatoryReport:
    """Deterministic regulatory projection; never an accounting source of truth."""

    accounting_entity_id: EntityId
    profile_id: str
    profile_version: str
    profile_checksum: str
    framework: str
    jurisdiction: str
    edition: str
    reference_snapshot_id: str
    reference_snapshot_checksum: str
    reference_model_id: str
    reference_model_checksum: str
    source_report_snapshot_id: str
    source_report_checksum: str
    regulatory_mapping_set_id: str
    regulatory_mapping_set_version: str
    regulatory_mapping_set_checksum: str
    as_of: date
    nodes: tuple[RegulatoryNodeValue, ...]
    checksum: str

    @classmethod
    def build(
        cls,
        *,
        accounting_entity_id: EntityId,
        profile_id: str,
        profile_version: str,
        profile_checksum: str,
        framework: str,
        jurisdiction: str,
        edition: str,
        reference_snapshot_id: str,
        reference_snapshot_checksum: str,
        reference_model_id: str,
        reference_model_checksum: str,
        source_report_snapshot_id: str,
        source_report_checksum: str,
        regulatory_mapping_set_id: str,
        regulatory_mapping_set_version: str,
        regulatory_mapping_set_checksum: str,
        as_of: date,
        nodes: tuple[RegulatoryNodeValue, ...],
    ) -> RegulatoryReport:
        checksum = cls._checksum(
            accounting_entity_id=accounting_entity_id,
            profile_id=profile_id,
            profile_version=profile_version,
            profile_checksum=profile_checksum,
            framework=framework,
            jurisdiction=jurisdiction,
            edition=edition,
            reference_snapshot_id=reference_snapshot_id,
            reference_snapshot_checksum=reference_snapshot_checksum,
            reference_model_id=reference_model_id,
            reference_model_checksum=reference_model_checksum,
            source_report_snapshot_id=source_report_snapshot_id,
            source_report_checksum=source_report_checksum,
            regulatory_mapping_set_id=regulatory_mapping_set_id,
            regulatory_mapping_set_version=regulatory_mapping_set_version,
            regulatory_mapping_set_checksum=regulatory_mapping_set_checksum,
            as_of=as_of,
            nodes=nodes,
        )
        return cls(
            accounting_entity_id=accounting_entity_id,
            profile_id=profile_id,
            profile_version=profile_version,
            profile_checksum=profile_checksum,
            framework=framework,
            jurisdiction=jurisdiction,
            edition=edition,
            reference_snapshot_id=reference_snapshot_id,
            reference_snapshot_checksum=reference_snapshot_checksum,
            reference_model_id=reference_model_id,
            reference_model_checksum=reference_model_checksum,
            source_report_snapshot_id=source_report_snapshot_id,
            source_report_checksum=source_report_checksum,
            regulatory_mapping_set_id=regulatory_mapping_set_id,
            regulatory_mapping_set_version=regulatory_mapping_set_version,
            regulatory_mapping_set_checksum=regulatory_mapping_set_checksum,
            as_of=as_of,
            nodes=nodes,
            checksum=checksum,
        )

    def node(self, code: str) -> RegulatoryNodeValue:
        for node in self.nodes:
            if node.code == code:
                return node
        raise KeyError(code)

    @staticmethod
    def _checksum(
        *,
        accounting_entity_id: EntityId,
        profile_id: str,
        profile_version: str,
        profile_checksum: str,
        framework: str,
        jurisdiction: str,
        edition: str,
        reference_snapshot_id: str,
        reference_snapshot_checksum: str,
        reference_model_id: str,
        reference_model_checksum: str,
        source_report_snapshot_id: str,
        source_report_checksum: str,
        regulatory_mapping_set_id: str,
        regulatory_mapping_set_version: str,
        regulatory_mapping_set_checksum: str,
        as_of: date,
        nodes: tuple[RegulatoryNodeValue, ...],
    ) -> str:
        payload = {
            "accounting_entity_id": str(accounting_entity_id),
            "profile_id": profile_id,
            "profile_version": profile_version,
            "profile_checksum": profile_checksum,
            "framework": framework,
            "jurisdiction": jurisdiction,
            "edition": edition,
            "reference_snapshot_id": reference_snapshot_id,
            "reference_snapshot_checksum": reference_snapshot_checksum,
            "reference_model_id": reference_model_id,
            "reference_model_checksum": reference_model_checksum,
            "source_report_snapshot_id": source_report_snapshot_id,
            "source_report_checksum": source_report_checksum,
            "regulatory_mapping_set_id": regulatory_mapping_set_id,
            "regulatory_mapping_set_version": regulatory_mapping_set_version,
            "regulatory_mapping_set_checksum": regulatory_mapping_set_checksum,
            "as_of": as_of.isoformat(),
            "nodes": [
                {
                    "node_id": node.node_id,
                    "code": node.code,
                    "value_type": node.value_type.value,
                    "amount": str(node.amount.amount) if node.amount is not None else None,
                    "currency": (
                        str(node.amount.currency.code) if node.amount is not None else None
                    ),
                    "comparative_amount": (
                        str(node.comparative_amount.amount)
                        if node.comparative_amount is not None
                        else None
                    ),
                    "source_statement_lines": list(node.source_statement_lines),
                    "mapping_ids": list(node.mapping_ids),
                    "mapping_provenances": list(node.mapping_provenances),
                    "human_validation_required": node.human_validation_required,
                    "account_hints_executable": node.account_hints_executable,
                }
                for node in nodes
            ],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


__all__ = ["RegulatoryNodeValue", "RegulatoryReport"]
