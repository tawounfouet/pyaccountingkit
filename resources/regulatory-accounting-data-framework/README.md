# Regulatory Accounting Data Framework

**Version 0.7.0 — OHADA EBNL**

Framework Python multi-référentiels pour transformer des documents comptables réglementaires en données **fidèles, traçables, reproductibles, testables, versionnables et auditables**.

```text
DOCUMENT OFFICIEL
      ↓
V0 RAW / SOURCE RECORDS
      ↓
V1 STRUCTURE
      ├──→ ANNOTATIONS / ACCOUNT KNOWLEDGE
      ├──→ FINANCIAL REPORTING
      ├──→ PRUDENTIAL
      ├──→ DISCLOSURES / CONSOLIDATION
      └──→ CROSSWALK
                   ↓
            BUSINESS ENRICHMENT
                   ↓
          HUMAN / ACCOUNTING REVIEW
                   ↓
         EXECUTABLE ACCOUNTING
```

Le framework généralise la méthode éprouvée sur PCEMF/AMIFOND sans imposer les mêmes phases à tous les standards. Chaque édition déclare ses **capabilities** dans un `manifest.yaml`.

## Standards préconfigurés

- `fr-pcg:2026`
- `cemac-pcemf:2010`
- `ohada-syscohada:2017`
- `fr-bank:2025`
- `fr-insurance:2025`
- `fr-nonprofit:2026`
- `fr-social-housing:2026`
- `fr-asset-management:2026`
- `fr-consolidated:2026`

Les PDF ne sont pas embarqués. Les manifests déclarent les fichiers attendus.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[pdf,dev]"
```

## CLI

```bash
regdata standard-list
regdata manifest-validate standards/fr-pcg/2026/manifest.yaml
regdata source-verify fr-pcg:2026
```

À partir d'un Markdown déjà converti :

```bash
regdata build-raw-from-markdown fr-pcg:2026 examples/sample_pcg_markdown.md sample-pcg datasets/raw/sample.json
regdata build-structure fr-pcg:2026 datasets/raw/sample.json datasets/structured/sample.json
regdata graph-validate datasets/structured/sample.json
pytest -q
```

## Règles clés

- le PDF officiel reste la source primaire ;
- aucune inférence silencieuse ;
- aucune correction silencieuse ;
- aucun code réglementaire paddé comme clé ;
- chaque enrichissement porte sa provenance ;
- un score crosswalk n'est pas une approbation ;
- aucune posting rule candidate ne devient exécutable sans revue.

Voir `docs/` pour l'architecture, la méthodologie, la migration AMIFOND/PCEMF et la roadmap.


## Migration PCEMF / AMIFOND — v0.2.0

La release 0.2.0 sait maintenant valider et migrer un ancien dépôt `regulatory-data` :

```bash
regdata pcemf-legacy-validate ../regulatory-data
regdata pcemf-legacy-validate ../regulatory-data --strict
regdata pcemf-migrate ../regulatory-data .
```

Le migrateur ne transforme pas les datasets historiques : il les copie byte-for-byte et génère un sidecar de migration avec SHA-256.

Voir :

- `standards/cemac-pcemf/2010/legacy_contract.yaml`
- `docs/08_RELEASE_0.2.0_PCEMF_MIGRATION.md`
- `docs/09_PCEMF_MIGRATION_RUNBOOK.md`


## PCG 2026 — release 0.3.0

Le framework embarque maintenant un second standard réellement construit depuis ses sources.

```bash
regdata pcg-build
regdata pcg-validate
regdata pcg-rag-search "1209 acomptes dividendes"
```

Datasets :

```text
datasets/raw/pcg_2026_v0_raw.json
datasets/structured/pcg_2026_v1_structure.json
datasets/annotated/pcg_2026_article_registry.json
datasets/annotated/pcg_2026_v2_account_functioning.json
datasets/annotated/pcg_2026_doctrine_ir.json
datasets/reporting/pcg_2026_v3_reporting.json
rag/indexes/pcg-recueil-2026-v1.json
```

Build actuel :

```json
{
  "articles": {
    "articles": 572,
    "unique_article_refs": 531
  },
  "doctrine": {
    "IR1": 41,
    "IR2": 35,
    "IR3": 199,
    "IR4": 40,
    "IR5": 3,
    "linked_to_article": 318,
    "total": 318
  },
  "rag": {
    "average_tokens": 110.62,
    "chunks": 1797,
    "pages_with_chunks": 665,
    "terms": 9273
  },
  "reporting": {
    "accounts_reverse_indexed": 763,
    "mapping_components": 190,
    "observations": 4,
    "statement_lines": 158,
    "statement_templates": 4
  },
  "v0": {
    "account_ranges": 1,
    "accounts": 768,
    "classes": 7,
    "groups": 60,
    "minimum_plan_account_entries": 366,
    "optional_account_entries": 403,
    "records_total": 836
  },
  "v1": {
    "account_nodes": 768,
    "class_nodes": 7,
    "graph_nodes": 836,
    "group_nodes": 60,
    "minimum_account_or_group_nodes": 426,
    "optional_account_nodes": 402,
    "range_nodes": 1
  },
  "v2": {
    "annotations": 58,
    "debit_credit_evidence_fragments": 188,
    "with_account_family_scope": 53,
    "with_class_scope": 5
  }
}
```

### Build PCG 0.3.0 final validé

```json
{
  "articles": {
    "articles": 572,
    "unique_article_refs": 531
  },
  "doctrine": {
    "IR1": 41,
    "IR2": 35,
    "IR3": 199,
    "IR4": 40,
    "IR5": 3,
    "linked_to_article": 318,
    "total": 318
  },
  "rag": {
    "average_tokens": 110.62,
    "chunks": 1797,
    "pages_with_chunks": 665,
    "terms": 9273
  },
  "reporting": {
    "accounts_reverse_indexed": 765,
    "mapping_components": 190,
    "observations": 0,
    "statement_lines": 158,
    "statement_templates": 4
  },
  "v0": {
    "account_ranges": 1,
    "accounts": 768,
    "classes": 7,
    "group_bundles": 1,
    "groups": 61,
    "minimum_plan_account_entries": 366,
    "optional_account_entries": 403,
    "records_total": 837
  },
  "v1": {
    "account_nodes": 768,
    "class_nodes": 7,
    "graph_nodes": 837,
    "group_bundle_nodes": 1,
    "group_nodes": 61,
    "minimum_account_or_group_nodes": 427,
    "optional_account_nodes": 402,
    "range_nodes": 1
  },
  "v2": {
    "annotations": 58,
    "debit_credit_evidence_fragments": 188,
    "with_account_family_scope": 53,
    "with_class_scope": 5
  }
}
```


## FR Non-Profit 2026 — release 0.4.0

```bash
regdata nonprofit-build
regdata nonprofit-validate
regdata nonprofit-rag-search "fonds dédiés générosité du public"
```

Le standard est un overlay de `fr-pcg:2026`, pas une copie.

Build :

```json
{
  "articles": {
    "articles": 142,
    "unique_article_refs": 137
  },
  "disclosures": {
    "general_annex": 14,
    "public_generosity": 22,
    "requirements": 36
  },
  "doctrine": {
    "IR1": 16,
    "IR2": 13,
    "IR3": 78,
    "IR4": 4,
    "IR5": 1,
    "linked_to_article": 111,
    "total": 112
  },
  "effective_plan": {
    "effective_accounts_or_groups": 901,
    "extension_additions": 73,
    "extension_overrides": 43,
    "inherited": 785
  },
  "functioning": {
    "account_refs_covered": 7,
    "annotations": 7
  },
  "orcom": {
    "occurrences": 855,
    "unique_codes": 853
  },
  "orcom_comparison": {
    "duplicate_code_meaning_in_practitioner_reference": 2,
    "label_match": 683,
    "label_variation": 142,
    "missing_from_practitioner_reference": 74,
    "practitioner_extra_not_in_canonical_effective_plan": 26
  },
  "overlay": {
    "label_or_semantic_override": 26,
    "same_semantics_label": 17,
    "specific_addition": 73
  },
  "rag": {
    "average_tokens": 111.07,
    "chunks": 559,
    "pages_with_chunks": 236,
    "terms": 4319
  },
  "reporting": {
    "lines_with_account_hints": 33,
    "statement_lines": 160,
    "statement_templates": 4
  },
  "specific_accounts": {
    "entries": 116,
    "unique_codes": 116
  }
}
```

## OHADA / CEMAC — 0.5.0

```bash
regdata family-list
regdata family-show ohada-accounting
regdata relation-list
regdata concept-list
regdata ohada-foundation-build
regdata ohada-foundation-validate
```

Members:

```text
ohada-syscohada:2017
ohada-ebnl:2023
cemac-pcemf:2010
```

## SYSCOHADA 2017 — 0.6.0
```bash
regdata syscohada-build
regdata syscohada-validate
regdata syscohada-rag-search "amortissement par unités d œuvre"
regdata syscohada-application-show 127
```
```json
{
  "applications": {
    "account_mentions": 2236,
    "applications": 142,
    "heading_observations": 3,
    "local_subdivision_mentions": 392,
    "part_distribution": {
      "DEUXIEME": 102,
      "PREMIERE": 24,
      "QUATRIEME": 15,
      "TROISIEME": 1
    },
    "resolved_accounts_reverse_indexed": 553
  },
  "consolidation": {
    "applications": 15,
    "first_application": 128,
    "last_application": 142
  },
  "guide": {
    "applications": 142,
    "chapters": 56,
    "parts": 4,
    "sections": 33
  },
  "rag": {
    "average_tokens": 107.41,
    "chunks": 621,
    "pages_with_chunks": 437,
    "terms": 5686
  },
  "v0": {
    "classes": 9,
    "groups": 85,
    "main_accounts": 432,
    "source_entries": 1403,
    "sub_accounts": 886,
    "unique_codes": 1403
  },
  "v1": {
    "account_nodes": 1403,
    "class_nodes": 9,
    "depth_distribution": {
      "1": 85,
      "2": 432,
      "3": 886
    },
    "graph_nodes": 1412,
    "group_nodes": 85,
    "leaf_nodes": 1108,
    "unique_atomic_codes": 1403
  },
  "v2": {
    "accounts_reverse_indexed": 553,
    "applications": 142,
    "chapters": 56,
    "consolidation_applications": 15,
    "current_operation_applications": 24,
    "financial_statement_applications": 1,
    "sections": 33,
    "specific_operation_applications": 102,
    "topics": 89
  },
  "v3": {
    "balance_model_lines": 48,
    "cashflow_model_lines": 23,
    "income_model_lines": 34,
    "narrative_rules": 10,
    "notes": 46,
    "source_observations": 2,
    "statement_types": 4
  }
}
```

## OHADA EBNL — 0.7.0

```bash
regdata ebnl-build
regdata ebnl-validate
regdata ebnl-account-show 4555
regdata ebnl-rag-search "contributions volontaires en nature"
```

```json
{
  "rag": {
    "average_tokens": 100.1,
    "chunks": 63,
    "pages_with_chunks": 29,
    "terms": 1802
  },
  "syscohada_delta": {
    "ambiguous_ebnl_source_code": 1,
    "ebnl_only_code": 165,
    "same_code_label_variation": 338,
    "same_code_same_normalized_label": 544,
    "syscohada_only_code": 521
  },
  "v0": {
    "account_occurrences": 1049,
    "account_occurrences_by_class": {
      "1": 76,
      "2": 269,
      "3": 40,
      "4": 214,
      "5": 65,
      "6": 252,
      "7": 88,
      "8": 38,
      "9": 7
    },
    "class_scopes": 2,
    "classes": 9,
    "duplicate_source_codes": 1,
    "groups": 84,
    "unique_account_codes": 1048,
    "visual_line_corrections": 23
  },
  "v1": {
    "account_occurrence_nodes": 1049,
    "ambiguous_account_occurrence_nodes": 2,
    "class_nodes": 9,
    "class_scope_nodes": 2,
    "graph_nodes": 1144,
    "group_nodes": 84,
    "leaf_nodes": 882,
    "non_prefix_source_parent_nodes": 25,
    "unique_account_codes": 1048
  }
}
```

### Build EBNL 0.7.0 final validé

```json
{
  "rag": {
    "average_tokens": 100.1,
    "chunks": 63,
    "pages_with_chunks": 29,
    "terms": 1802
  },
  "syscohada_delta": {
    "ambiguous_ebnl_source_code": 1,
    "ebnl_only_code": 165,
    "same_code_label_variation": 338,
    "same_code_same_normalized_label": 545,
    "syscohada_only_code": 520
  },
  "v0": {
    "account_occurrences": 1050,
    "account_occurrences_by_class": {
      "1": 76,
      "2": 269,
      "3": 40,
      "4": 214,
      "5": 66,
      "6": 252,
      "7": 88,
      "8": 38,
      "9": 7
    },
    "class_scopes": 2,
    "classes": 9,
    "duplicate_source_codes": 1,
    "groups": 84,
    "unique_account_codes": 1049,
    "visual_line_corrections": 23
  },
  "v1": {
    "account_occurrence_nodes": 1050,
    "ambiguous_account_occurrence_nodes": 2,
    "class_nodes": 9,
    "class_scope_nodes": 2,
    "graph_nodes": 1145,
    "group_nodes": 84,
    "leaf_nodes": 880,
    "non_prefix_source_parent_nodes": 7,
    "unique_account_codes": 1049
  }
}
```


## OHADA EBNL Complete — 0.7.1

The complete 438-page official SYCEBNL Act is now the primary normative source. The 0.7 chart extract is retained as a secondary V0/V1 validation source.

```bash
regdata ebnl-build
regdata ebnl-validate
regdata ebnl-reporting-profiles
regdata ebnl-source-page 346
regdata ebnl-rag-search "fonds affectés"
```

Key source-first safeguards: no executable posting rule is inferred from narrative guidance; no perfect OCR is claimed for image-heavy pages; reporting models remain visually authoritative.

```json
{
  "conceptual": {
    "conventions": 5,
    "definitions": 47,
    "postulates": 5,
    "qualitative_characteristics": 6
  },
  "disclosures": {
    "profiles": 3
  },
  "full_source_router_rag": {
    "average_tokens": 22.48,
    "chunks": 439,
    "pages_with_chunks": 438,
    "terms": 558
  },
  "legal": {
    "articles": 28,
    "first_article": 1,
    "last_article": 28
  },
  "source_pages": {
    "pages": 438,
    "pages_sparse_or_header_only": 434,
    "pages_with_substantive_native_text": 4,
    "pages_with_title_bindings": 96
  },
  "specific_operations": {
    "chapters": 6
  },
  "syscohada_delta": {
    "ambiguous_ebnl_source_code": 1,
    "ebnl_only_code": 165,
    "same_code_label_variation": 338,
    "same_code_same_normalized_label": 545,
    "syscohada_only_code": 520
  },
  "v0": {
    "account_occurrences": 1050,
    "account_occurrences_by_class": {
      "1": 76,
      "2": 269,
      "3": 40,
      "4": 214,
      "5": 66,
      "6": 252,
      "7": 88,
      "8": 38,
      "9": 7
    },
    "class_scopes": 2,
    "classes": 9,
    "duplicate_source_codes": 1,
    "groups": 84,
    "unique_account_codes": 1049,
    "visual_line_corrections": 23
  },
  "v1": {
    "account_occurrence_nodes": 1050,
    "ambiguous_account_occurrence_nodes": 2,
    "class_nodes": 9,
    "class_scope_nodes": 2,
    "graph_nodes": 1145,
    "group_nodes": 84,
    "leaf_nodes": 880,
    "non_prefix_source_parent_nodes": 7,
    "unique_account_codes": 1049
  },
  "v2": {
    "extra_title_page_codes": [],
    "group_bindings": 84,
    "missing_group_title_pages": [],
    "visual_title_pages_bound": 84
  },
  "v3": {
    "profiles": 3,
    "sm_treasury_threshold_rules": 5,
    "statement_models": 13
  },
  "capability_status": {
    "normative_source_gap_closed": true,
    "full_verbatim_ocr_claimed": false,
    "executable_posting_rules_generated": false,
    "automatic_filing_generation": false
  }
}
```
