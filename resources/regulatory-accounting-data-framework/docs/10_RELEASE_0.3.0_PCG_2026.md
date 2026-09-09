# Release 0.3.0 — PCG 2026

## Objectif

Cette release démontre que le framework peut traiter un second référentiel complet avec la même architecture que PCEMF, sans recopier son pipeline.

Corpus embarqué :

```text
Plan de comptes PCG 2026
+
Règlement ANC n° 2014-03 consolidé au 1er janvier 2026
+
Recueil ANC des normes comptables françaises 2026
```

## Sources

Le standard `fr-pcg:2026` contient six artefacts :

- 3 PDF sources ;
- 3 transcriptions Markdown dérivées ;
- SHA-256 fixé dans `manifest.yaml`.

## V0 — plan de comptes

Le parser PCG conserve :

- classes ;
- groupes à deux chiffres ;
- comptes ;
- compte/plage `471 à 473` ;
- caractère facultatif déduit **uniquement de l'italique Markdown issu de la source** ;
- ordre source ;
- ligne Markdown ;
- texte source.

Invariants générés :

```text
classes                    : 7
groupes                    : 61
comptes                    : 768
plages                     : 1
comptes facultatifs        : 403
records total              : 837
```

## V1 — structure

La V1 reconstruit le graphe sans padding.

```text
class nodes                : 7
group nodes                : 61
account nodes              : 768
range nodes                : 1
graph nodes                : 837
```

Les collisions historiques `11/110`, `12/120`, `28/280`, `29/290`, `59/590` sont impossibles car l'identifiant technique n'est pas produit par padding.

## Registre réglementaire

Le règlement consolidé est transformé en registre d'articles :

```text
articles                   : 572
article refs uniques       : 531
```

Chaque article conserve :

```text
article_ref
page_start_pdf
page_end_pdf
heading_path
text_source
source_line_md
```

## V2 — fonctionnement des comptes

Le Titre XII est extrait comme **evidence documentaire**, jamais comme posting rules exécutables.

```text
annotations Titre XII       : 58
fragments débit/crédit      : 188
```

Les articles `1211-10`, `1211-12`, etc. restent rattachés à leur texte source. Les règles particulières de `109` ou `1209` ne sont donc plus remplacées par une règle générique héritée.

## Doctrine ANC

Le Recueil est analysé en blocs IR1→IR5 :

```text
{
  "IR1": 41,
  "IR2": 35,
  "IR3": 199,
  "IR4": 40,
  "IR5": 3,
  "linked_to_article": 318,
  "total": 318
}
```

Ces éléments sont **infra-réglementaires**, distincts des articles obligatoires.

## RAG déterministe

Le Recueil complet est indexé lexicalement par page et heading :

```text
chunks                     : 1797
termes                     : 9273
pages avec chunks          : 665
tokens moyens / chunk      : 110.62
```

Aucune génération LLM n'écrit dans le dataset canonique.

## V3 — reporting

Quatre modèles sont construits :

```text
balance - système de base
compte de résultat - système de base
balance - système abrégé
compte de résultat - système abrégé
```

Les mappings proviennent des tableaux IR4 de passage entre plan de comptes et documents de synthèse.

```text
statement templates        : 4
statement lines            : 158
mapping components         : 190
accounts reverse-indexed   : 763
observations               : 4
```

La donnée conserve explicitement que ces tableaux sont des **exemples IR4 à titre indicatif**, et non un remplacement des articles réglementaires.

## Frontière de la 0.3

La 0.3 ne crée pas encore :

- de sens naturel global heuristique compte par compte ;
- de posting rules exécutables ;
- de crosswalk PCG ↔ IFRS/SYSCOHADA/PCEMF ;
- de moteur complet des informations d'annexe ;
- de classification métier propre à une entreprise.

Ces couches viendront au-dessus des preuves réglementaires déjà structurées.
