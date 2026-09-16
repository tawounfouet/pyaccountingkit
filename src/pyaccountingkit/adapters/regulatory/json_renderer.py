"""Canonical JSON renderer for already-computed regulatory reports."""

from __future__ import annotations

import json

from pyaccountingkit.domain.reporting.regulatory_export import RegulatoryExportDefinition
from pyaccountingkit.domain.reporting.regulatory_report import RegulatoryReport


class CanonicalJSONRegulatoryRenderer:
    """Reference renderer: deterministic serialization only, no accounting logic."""

    renderer_id = "canonical-json-v1"

    def render(
        self,
        report: RegulatoryReport,
        definition: RegulatoryExportDefinition,
    ) -> bytes:
        payload = {
            "schema_version": definition.schema_version,
            "profile": {
                "id": report.profile_id,
                "version": report.profile_version,
                "framework": report.framework,
                "jurisdiction": report.jurisdiction,
                "edition": report.edition,
            },
            "reference": {
                "snapshot_id": report.reference_snapshot_id,
                "snapshot_checksum": report.reference_snapshot_checksum,
                "model_id": report.reference_model_id,
                "model_checksum": report.reference_model_checksum,
            },
            "source_report": {
                "snapshot_id": report.source_report_snapshot_id,
                "checksum": report.source_report_checksum,
            },
            "as_of": report.as_of.isoformat(),
            "report_checksum": report.checksum,
            "nodes": [
                {
                    "node_id": node.node_id,
                    "code": node.code,
                    "label": node.label,
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
                    "human_validation_required": node.human_validation_required,
                }
                for node in report.nodes
            ],
        }
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")


__all__ = ["CanonicalJSONRegulatoryRenderer"]
