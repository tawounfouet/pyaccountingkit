# Release 0.6.0 — SYSCOHADA 2017 Complete

## V0 / V1

```json
{
  "classes": 9,
  "groups": 85,
  "main_accounts": 432,
  "source_entries": 1403,
  "sub_accounts": 886,
  "unique_codes": 1403
}
```

```json
{
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
}
```

Le plan contient exactement 1 403 entrées de comptes/groupes et 9 classes. Aucun padding n'est appliqué.

## Guide

```json
{
  "applications": 142,
  "chapters": 56,
  "parts": 4,
  "sections": 33
}
```

Le sommaire est utilisé comme registre structurel pour les 4 parties, 56 chapitres, 33 sections et 142 applications.

## Applications

```json
{
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
}
```

Les anomalies de titres/numérotation du corps sont conservées puis résolues contre le sommaire :
- `APPLICATION 535` → Application 53, *Stocks de marchandises* ;
- `APPLICATION 616` → Application 61 ;
- `APPLICATIONü 113` est conservé comme marqueur source ;
- la seconde rubrique Application 142 est une continuation.

Les subdivisions locales d'exemples comme `101300` ne deviennent pas des comptes du plan : elles sont résolues vers le plus long préfixe canonique (`1013`) avec provenance.

## V2 Accounting Knowledge

```json
{
  "accounts_reverse_indexed": 553,
  "applications": 142,
  "chapters": 56,
  "consolidation_applications": 15,
  "current_operation_applications": 24,
  "financial_statement_applications": 1,
  "sections": 33,
  "specific_operation_applications": 102,
  "topics": 89
}
```

Les applications restent des preuves d'application et ne génèrent aucune posting rule exécutable.

## Consolidation

```json
{
  "applications": 15,
  "first_application": 128,
  "last_application": 142
}
```

La quatrième partie couvre les applications 128 à 142.

## V3 Reporting

```json
{
  "balance_model_lines": 48,
  "cashflow_model_lines": 23,
  "income_model_lines": 34,
  "narrative_rules": 10,
  "notes": 46,
  "source_observations": 2,
  "statement_types": 4
}
```

La release structure :
- Bilan ;
- Compte de résultat ;
- Tableau des flux de trésorerie ;
- 46 références de Notes de l'Application 127.

Le Guide renvoie toutefois aux tables officielles Postes/Comptes du Titre IX chapitre 7, absentes du corpus fourni. Aucune table exhaustive n'est inventée.

## RAG

```json
{
  "average_tokens": 107.41,
  "chunks": 621,
  "pages_with_chunks": 437,
  "terms": 5686
}
```

Index lexical déterministe sur les 437 pages.
