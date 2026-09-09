# Release 0.7.0 — OHADA EBNL

## Périmètre documentaire réel

La source fournie est un extrait de 29 pages du Journal officiel OHADA 2023 :

```text
PARTIE 2 : STRUCTURE, CONTENU ET FONCTIONNEMENT DES COMPTES
Plan des comptes détaillé
```

Elle permet de construire le plan et sa structure, mais pas de reconstruire sans invention
le fonctionnement détaillé des comptes, les états financiers ou l'annexe.

## Revue OCR / scan

Le PDF image-only reste l'autorité visuelle. Le Markdown OCR original est conservé.
Le ledger `validation/review/ebnl_2023_visual_review_ledger.json` contient 23 corrections
de codes ou entêtes directement vérifiées contre le scan.

Aucune correction globale de libellé OCR n'est appliquée silencieusement.

## V0

```json
{
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
}
```

Le V0 contient 1 050 occurrences pour 1 049 codes distincts.

La différence vient du code `4555`, réellement imprimé deux fois avec deux significations.

## V1

```json
{
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
```

L'identité n'est donc pas réduite au numéro de compte :
`4555:occ01` et `4555:occ02` restent deux occurrences distinctes et chacune conserve
son parent de mise en page source.

La classe 9 est modélisée avec deux scopes :
- contributions volontaires en nature (90–91) ;
- comptabilité analytique de gestion (92–99).

## Delta SYSCOHADA

```json
{
  "ambiguous_ebnl_source_code": 1,
  "ebnl_only_code": 165,
  "same_code_label_variation": 338,
  "same_code_same_normalized_label": 545,
  "syscohada_only_code": 520
}
```

Ce delta est structurel :
`code égal != équivalence sémantique`, et aucun héritage EBNL → SYSCOHADA n'est déclaré.

## RAG OCR

```json
{
  "average_tokens": 100.1,
  "chunks": 63,
  "pages_with_chunks": 29,
  "terms": 1802
}
```

Le RAG couvre les 29 pages mais tout libellé faisant autorité doit être vérifié contre le scan.

## Capacités bloquées

```text
V2 account functioning  -> blocked_missing_normative_corpus
V3 reporting            -> blocked_missing_normative_corpus
Disclosures             -> blocked_missing_normative_corpus
```
