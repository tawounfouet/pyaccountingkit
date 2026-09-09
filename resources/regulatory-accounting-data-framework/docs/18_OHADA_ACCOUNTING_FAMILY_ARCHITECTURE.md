# Architecture de la famille OHADA/CEMAC

## Objets

```text
AccountingFamily
StandardEdition
StandardRelation
SourceArtifact
AccountingConcept
ConceptBinding
```

## Relations v0.5

```text
SYSCOHADA 2017 -> member_of_family -> ohada-accounting
EBNL 2023 -> specialized_standard_within_family -> ohada-accounting
PCEMF 2010 -> sector_specialization_within_family -> ohada-accounting
PCEMF 2010 -> crosswalk -> SYSCOHADA 2017
```

Le crosswalk exige une revue humaine et ne constitue pas un héritage.
