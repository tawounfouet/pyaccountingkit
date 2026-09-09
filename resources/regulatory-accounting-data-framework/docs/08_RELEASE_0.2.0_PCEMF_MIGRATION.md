# Release 0.2.0 — Migration PCEMF / AMIFOND

## Objectif

Extraire du projet AMIFOND les contrats et composants génériques du pipeline PCEMF sans réécrire l'histoire des datasets.

La release introduit une migration **compatibilité-first** :

```text
ancien dépôt regulatory-data
        ↓
validation des invariants historiques
        ↓
copie byte-for-byte des artefacts canoniques
        ↓
nouvelle arborescence framework
        ↓
sidecar de migration + hashes
```

## Artefacts PCEMF supportés

```text
V0 RAW
V1 STRUCTURE
V2 ANNOTATED
V3 REPORTING
V4 PRUDENTIAL
V5 PCEMF ↔ SYSCOHADA
V6 AMIFOND BUSINESS
```

## Invariants repris de l'implémentation historique

### V0

```text
1 502 entrées source
50 entrées groupées
```

### V1

```text
1 552 nœuds comptes
9 nœuds classes
1 561 nœuds graphe
0 cycle
0 auto-référence
0 parent manquant
```

### V2

```text
86 fiches annotées
87 / 87 comptes top-level couverts
1 fiche groupée 30/31
3 blocs EST DEBITE ET CREDITE
40 observations source
```

### V3

```text
8 états
635 lignes
419 composants parsés
1 014 comptes feuilles reverse-indexés
20 observations
```

### V4

```text
13 règles prudentielles
114 composants
37 formules
19 seuils
23 observations
```

### V5

```text
756 chunks Guide
5 371 termes
4 656 candidats
0 mapping auto-approuvé
```

### V6

```text
17 tags
10 liens comptes
5 produits
5 frais/commissions/intérêts
13 événements
8 posting models
0 posting rule exécutable
15 contrôles
12 scénarios
```

## Sécurité de migration

La migration n'ajoute aucune sémantique au dataset legacy.

```text
source hash == target hash
```

Le timestamp de migration est écrit uniquement dans :

```text
validation/review/pcemf_legacy_migration_report.json
```

et jamais dans les datasets canoniques.

## Limite du ZIP

Les JSON V0→V6 historiques n'ont pas été fournis avec cette demande. Le livrable contient donc :

- le migrateur ;
- les contrats historiques ;
- les validateurs ;
- les tests ;
- le runbook.

L'import réel devient exécutable dès que le répertoire du dépôt AMIFOND est fourni.
