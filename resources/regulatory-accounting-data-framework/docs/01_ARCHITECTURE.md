# Architecture générale

Le framework distingue : **source documentaire**, **dérivation structurelle**, **connaissance réglementaire enrichie** et **connaissance métier**.

```text
Official source
    ↓
Source record
    ↓
Structured node
    ├── Annotation evidence
    ├── Statement mapping
    ├── Prudential component
    └── Crosswalk candidate
             ↓
        Human review
             ↓
       Business application
```

## Standard / édition / extension

- `AccountingStandard` : identité stable du corpus.
- `Edition` : snapshot réglementaire.
- `StandardExtension` : adaptation sectorielle d'un standard de base.

## Capabilities

Les couches sont activées par capacités : `chart_of_accounts`, `structure`, `posting_guidance`, `financial_reporting`, `prudential`, `disclosures`, `consolidation`, `sector_adaptations`, `crosswalk`, `business_enrichment`.
