# Release 0.5.0 — OHADA Family Foundation

## But

Introduire `AccountingFamily`, `StandardRelation`, la gouvernance de sources et un pivot sémantique neutre avant les implémentations complètes SYSCOHADA / EBNL / PCEMF.

```text
                  ohada-accounting
                         |
        +----------------+----------------+
        |                |                |
SYSCOHADA 2017       EBNL 2023        PCEMF 2010
OHADA général        OHADA EBNL       COBAC/CEMAC
```

`MEMBER_OF_FAMILY` n'est jamais synonyme de `INHERITS`.

## Garde temporelle

`cemac-pcemf:2010 INHERITS ohada-syscohada:2017` est explicitement interdit.

La source PCEMF rattache la normalisation COBAC au cadre OHADA commun et décrit les dispositifs concernés comme plans comptables sectoriels : cela justifie la famille et la spécialisation sectorielle, pas une filiation vers l'édition 2017.

## Sources

- SYSCOHADA : plan + guide.
- EBNL : scan officiel + OCR bloqué avant revue.
- PCEMF : document complet + liste autonome + annexes reporting/prudentiel.

## Concept pivot

12 concepts neutres sont créés, avec 0 binding compte-concept. Les bindings viendront après validation des structures.
