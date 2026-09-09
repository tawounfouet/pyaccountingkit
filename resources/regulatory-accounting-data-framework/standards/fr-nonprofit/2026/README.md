# FR Non-Profit 2026

Extension sectorielle du `fr-pcg:2026`.

## Priorité des sources

1. **ANC Recueil secteur non lucratif 2026** : source réglementaire primaire.
2. **ORCOM Plan de comptes Associations 2025** : référence praticien secondaire de comparaison uniquement.

ORCOM ne peut jamais modifier automatiquement un dataset canonique.

## Héritage réglementaire

L'article 320-1 du règlement ANC n° 2018-06 impose le plan de comptes du PCG sous réserve des comptes spécifiques énumérés à l'article 320-2.

Le modèle du framework est donc :

```text
fr-pcg:2026
   +
Art. 320-2 additions / overrides
   =
fr-nonprofit:2026 effective plan
```
