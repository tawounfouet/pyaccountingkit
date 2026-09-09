# Méthodologie

## Règles non négociables

1. **Source-first** : le PDF officiel reste la source primaire ; Markdown et JSON sont dérivés.
2. **Aucune inférence silencieuse** : `source`, `derived`, `official_external`, `human_verified`, `ai_inferred`.
3. **Aucune correction silencieuse** : toute divergence devient une `Observation`.
4. **Pas de padding comme identité** : le code réglementaire n'est pas une clé technique.
5. **Reproductibilité** : pas d'horodatage volatile dans le dataset canonique.
6. **Human-in-the-loop** : crosswalk, conflits réglementaires et posting rules sensibles restent soumis à revue.

## V0 universelle

La V0 représente ce qui est imprimé : code source, libellé source, ordre, page, classe, marqueur, lignes source, features d'extraction.

## V1 universelle

La V1 ne reconstruit que la structure : parent, enfants, profondeur, chemin, feuille, projections de codes groupés.

## Couches optionnelles

Annotations, reporting, prudentiel, consolidation, crosswalk et business enrichment sont indépendants et activés selon le manifest.
