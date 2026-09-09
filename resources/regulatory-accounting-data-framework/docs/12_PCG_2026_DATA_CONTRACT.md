# Contrat de données PCG 2026

## V0

`datasets/raw/pcg_2026_v0_raw.json`

Types :

```text
class
group
account
account_range
```

Pour un compte :

```json
{
  "code_source": "1011",
  "optional": true,
  "parent_code": "101",
  "source_line_md": 20
}
```

Pour la plage :

```json
{
  "record_type": "account_range",
  "code_source": "471 à 473",
  "label_source": "Comptes d'attente"
}
```

Elle n'est jamais transformée silencieusement en trois comptes artificiels.

## V1

`datasets/structured/pcg_2026_v1_structure.json`

Identité :

```text
account:fr-pcg:2026:10131
```

Le code source reste :

```text
10131
```

## V2

`datasets/annotated/pcg_2026_v2_account_functioning.json`

Un article conserve :

```text
article_ref
scope
account_mentions
posting_guidance_evidence
text_source
page_start/end
provenance
```

`executable_rules_generated=false`.

## Doctrine

`datasets/annotated/pcg_2026_doctrine_ir.json`

Les IR sont typés :

```text
IR1 contexte
IR2 champ d'application
IR3 modalités de mise en œuvre
IR4 exemples
IR5 schémas d'écriture
```

## Reporting

`datasets/reporting/pcg_2026_v3_reporting.json`

```text
Statement
 └── StatementLine
      └── MappingComponent
           └── selectors
```

Les expressions source sont toujours conservées avant parsing.
