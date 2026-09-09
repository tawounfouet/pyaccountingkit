# Migration AMIFOND / PCEMF

Le pipeline existant devient le premier cas d'usage complet du framework.

```text
pcemf_2010_v0_raw.json        -> datasets/raw/
pcemf_2010_v1_structure.json  -> datasets/structured/
pcemf_2010_v2_annotated.json  -> datasets/annotated/
pcemf_2010_v3_reporting.json  -> datasets/reporting/
pcemf_2010_v4_prudential.json -> datasets/prudential/
V5 crosswalk                  -> datasets/crosswalk/ + validation/review/
V6 AMIFOND                    -> business/amifond/
```

À conserver : pas de padding, pas de correction silencieuse, codes groupés projetés, annotations non exécutables, crosswalk sans auto-approval, posting rules non exécutables avant revue.
