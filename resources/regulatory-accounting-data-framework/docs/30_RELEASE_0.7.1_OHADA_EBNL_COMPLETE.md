# Release 0.7.1 — OHADA EBNL Complete

## Objectif

La release 0.7.1 remplace le statut documentaire incomplet de la 0.7.0 par une couverture normative complète du **Système comptable des entités à but non lucratif (SYCEBNL)**.

La nouvelle source primaire est le **Journal officiel OHADA — Acte uniforme relatif au système comptable des entités à but non lucratif**, 438 pages. L'extrait de 29 pages utilisé en 0.7.0 est conservé comme source secondaire de validation du plan de comptes.

## Source-first

```text
SYSCEBNL_Acte_Uniforme_2023.pdf
        │
        ├── Acte uniforme                    p. 15–25
        ├── Définitions / cadre conceptuel   p. 31–67
        ├── Plan de comptes                  p. 69–105
        ├── Fonctionnement des comptes       p. 106–308
        ├── Opérations spécifiques           p. 309–338
        └── Etats financiers                 p. 339–438
```

L'Article 28 fixe l'entrée en vigueur au **1er janvier 2024**.

## Datasets nouveaux

```text
datasets/annotated/
├── ebnl_2023_legal_act_registry.json
├── ebnl_2023_conceptual_framework.json
├── ebnl_2023_v2_account_functioning.json
├── ebnl_2023_specific_operations.json
├── ebnl_2023_disclosures_registry.json
└── ebnl_2023_source_page_registry.json

datasets/reporting/
└── ebnl_2023_v3_reporting.json

rag/indexes/
└── ebnl-sycebnl-2023-source-router-v2.json
```

## V0 / V1

Les invariants de 0.7.0 sont conservés :

- 9 classes ;
- 2 scopes de classe 9 ;
- 84 groupes ;
- 1 050 occurrences de comptes ;
- 1 049 codes distincts ;
- anomalie source `4555` préservée sous deux occurrences distinctes.

## Registre juridique

Les **28 articles** de l'Acte uniforme sont routés vers leur page source. Les faits structurés critiques de la release sont limités à ce que la source permet d'établir sans inférence, notamment :

- composition des jeux d'états financiers — Article 4 ;
- seuils du Système Minimal de Trésorerie — Article 6 ;
- date d'entrée en vigueur — Article 28.

## Cadre conceptuel

Le dataset structure :

- 47 termes du chapitre des définitions ;
- 5 postulats comptables ;
- 5 conventions comptables ;
- 6 caractéristiques qualitatives ;
- les composantes des états financiers ;
- les sections d'évaluation, comptabilisation et décomptabilisation.

## V2 — fonctionnement des comptes

Le V2 couvre les **84 groupes à deux chiffres** et les rattache aux pages du chapitre « Contenu et fonctionnement des comptes ».

Le modèle reconnaît le schéma documentaire :

```text
Contenu
Subdivisions
Commentaires
Fonctionnement au débit
Fonctionnement au crédit
Exclusions
Eléments de contrôle
```

Les pages image restent l'autorité. La release **ne transforme pas automatiquement** les phrases normatives en règles de posting exécutables.

## Opérations spécifiques

Les six chapitres officiels de la Partie 3 sont enregistrés :

1. Fonds propres des associations et ordres professionnels — p. 311–318
2. Fonds affectés et reportés — p. 319–324
3. Fonds propres des projets de développement — p. 325–328
4. Dons — p. 329–332
5. Cotisations / versements des fondateurs — p. 333–334
6. Autres opérations spécifiques — p. 335–338

## V3 — reporting

Trois profils réglementaires distincts sont modélisés :

```text
association_professional_order
├── Bilan                         p. 346
├── Compte de résultat            p. 347
├── Tableau des flux              p. 348
└── Notes annexes                 p. 349–396

development_project
├── Tableau emplois-ressources    p. 398
├── Exécution budgétaire          p. 399
├── Réconciliation de trésorerie  p. 400
├── Bilan                         p. 401
├── Compte d'exploitation         p. 402
└── Notes annexes                 p. 403–432

minimal_cash_system
├── Bilan                         p. 434
├── Compte de résultat            p. 435
└── Notes annexes                 p. 435–438
```

Soit **13 modèles d'états** routés vers leurs pages officielles.

## Système Minimal de Trésorerie

L'Article 6 est représenté avec cinq catégories de seuil à **30 000 000 XAF**. La release conserve les catégories de la source et n'invente pas de règle d'éligibilité supplémentaire.

## RAG / Source router

Le PDF est très majoritairement image-based. La couche texte native n'est substantielle que sur quelques pages.

La release ne prétend donc pas disposer d'un OCR parfait. Elle fournit plutôt un **source router de 438 pages** :

- une entrée pour chaque page ;
- la partie / le chapitre ;
- les comptes ou états liés lorsque vérifiés visuellement ;
- l'état de la couche texte native ;
- un index lexical de routage.

Toute citation faisant autorité doit être vérifiée dans le PDF officiel.

## CLI

```bash
regdata ebnl-build
regdata ebnl-validate
regdata ebnl-account-show 4555
regdata ebnl-reporting-profiles
regdata ebnl-source-page 346
regdata ebnl-rag-search "fonds affectés"
```

## Garde-fous

```text
complete normative source        = true
full verbatim OCR claimed        = false
executable posting rules         = false
automatic filing generation      = false
silent template reconstruction   = false
visual PDF authority             = true
```

La notion **Complete** de 0.7.1 signifie donc : *source normative officielle complète et modèles structurés couvrant l'ensemble des capacités documentaires*, pas *transcription OCR exhaustive de chaque cellule ou paragraphe*.
