# Third-Party and Resource Notices

This file records provenance and rights boundaries for repository resources. It is **not** a
license grant and does not replace the terms attached to an original source.

## PyAccountingKit project license

Project-authored PyAccountingKit software and documentation are distributed under the root
`LICENSE` file (MIT).

The presence of a third-party, regulatory, practitioner, or externally authored source under
`resources/` does **not** mean that PyAccountingKit relicenses that source under MIT. Original
source terms, notices, attribution requirements, database rights, copyright, and other applicable
rights continue to govern those materials.

## CFA FRA Sprint-7 behavioral oracle

Path:

```text
resources/cfa_fra_django_mvp_sprint_7/
```

Governance identity:

```text
project: cfa_fra_django_mvp_sprint_7
version: 0.8.0
tree: 07d4880534d2e2239e19fd4ef4139de70b56773a
```

This snapshot is retained as a frozen behavioral oracle for parity, migration and regression
evidence. It has no separate license declaration inside the snapshot. PyAccountingKit therefore
does not make an additional licensing claim for that embedded snapshot in this notice.

The snapshot is repository evidence only. It is not included in the PyAccountingKit wheel and is
not a runtime dependency.

## Regulatory Accounting Data Framework snapshot

Path:

```text
resources/regulatory-accounting-data-framework/
```

Governance identity:

```text
project: regulatory-accounting-data-framework
version: 0.7.1
tree: f6f05c8f2fe8397e4ebb80707ebeed6497e53e98
```

This snapshot contains structured data, derived transcriptions and source documents associated
with several regulatory or practitioner authorities. Its standard manifests identify source
roles, authorities and SHA-256 checksums. Authorities represented in the current snapshot include:

- Autorité des normes comptables (ANC);
- OHADA;
- COBAC / CEMAC;
- an ORCOM practitioner reference used by the non-profit comparison dataset.

The snapshot does not declare one uniform license covering all source documents. Its rights status
is therefore intentionally recorded as `MIXED_OR_UNASSERTED_REVIEW_REQUIRED`.

No contributor should assume that:

- an official document is automatically MIT-licensed;
- a derived transcription changes the rights attached to its source;
- repository availability grants permission for separate redistribution or commercial repackaging;
- a regulatory source can be silently replaced while preserving the same provenance identity.

Before externally repackaging any source material from this bundle, review the original source
terms and applicable rights.

## Packaging boundary

Neither resource bundle belongs in the PyAccountingKit distribution artifact.

The repository quality gates require:

```text
wheel: no resources/
wheel: no data/
resource registry: current
resource tree fingerprints: current
resource bundle manifests: current
```

## Adding or updating resources

Any change under `resources/<bundle>/` must update `RESOURCE_GOVERNANCE.json` in the same pull
request and must preserve or refresh the source-specific checksum/provenance metadata maintained by
that bundle.

Do not add production accounting data, personal data, credentials, secrets or confidential client
material to `resources/`.
