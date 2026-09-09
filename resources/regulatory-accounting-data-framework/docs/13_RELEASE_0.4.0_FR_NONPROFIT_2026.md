# Release 0.4.0 — FR Non-Profit 2026

## Positionnement

`fr-nonprofit:2026` est la première **extension réglementaire** réellement construite au-dessus d'un standard parent :

```text
fr-pcg:2026
      +
ANC 2018-06 / Art. 320-2
      =
fr-nonprofit:2026
```

La release ne duplique donc pas le PCG.

## Sources

### Primaire

```text
ANC_Recueil-non-lucratif_ONG_Associations_2026.pdf
```

Rôle :

```text
official_regulatory_source
```

### Secondaire

```text
PCA_plan-comptable-associations_orcom_2025.pdf
```

Rôle :

```text
external_practitioner_reference
```

La référence ORCOM ne peut jamais modifier automatiquement le dataset canonique.

## Article registry

Tome I ANC 2018-06 :

```json
{
  "articles": 142,
  "unique_article_refs": 137
}
```

## Doctrine IR

```json
{
  "IR1": 16,
  "IR2": 13,
  "IR3": 78,
  "IR4": 4,
  "IR5": 1,
  "linked_to_article": 111,
  "total": 112
}
```

## Nomenclature spécifique — Art. 320-2

```json
{
  "entries": 116,
  "unique_codes": 116
}
```

Le framework compare chaque code à `fr-pcg:2026` et le classe :

```text
specific_addition
label_or_semantic_override
same_semantics_label
```

Résultat :

```json
{
  "label_or_semantic_override": 26,
  "same_semantics_label": 17,
  "specific_addition": 73
}
```

## Plan effectif

Le plan effectif résulte de l'héritage du PCG et de l'application de l'overlay :

```json
{
  "effective_accounts_or_groups": 901,
  "extension_additions": 73,
  "extension_overrides": 43,
  "inherited": 785
}
```

## Fonctionnement des comptes

Les articles 331-1 à 333-2 sont conservés comme preuves réglementaires :

```json
{
  "account_refs_covered": 7,
  "annotations": 7
}
```

Aucune posting rule exécutable n'est produite.

## Reporting

La release structure quatre modèles :

```text
Bilan
Compte de résultat
Compte de résultat par origine et destination (CROD)
Compte d'emploi annuel des ressources collectées auprès du public (CER)
```

```json
{
  "lines_with_account_hints": 33,
  "statement_lines": 160,
  "statement_templates": 4
}
```

Les account hints sont des candidats dérivés à valider humainement.

## Disclosures / annexe

Les articles 431-* et 432-* sont publiés comme exigences d'information :

```json
{
  "general_annex": 14,
  "public_generosity": 22,
  "requirements": 36
}
```

## RAG

```json
{
  "average_tokens": 111.07,
  "chunks": 559,
  "pages_with_chunks": 236,
  "terms": 4319
}
```

## Comparaison ORCOM

```json
{
  "occurrences": 855,
  "unique_codes": 853
}
```

Comparaison au plan effectif :

```json
{
  "duplicate_code_meaning_in_practitioner_reference": 2,
  "label_match": 683,
  "label_variation": 142,
  "missing_from_practitioner_reference": 74,
  "practitioner_extra_not_in_canonical_effective_plan": 26
}
```

Le fichier ORCOM est plus ancien (2025) que l'édition canonique 2026 et conserve uniquement un rôle de contrôle secondaire.
