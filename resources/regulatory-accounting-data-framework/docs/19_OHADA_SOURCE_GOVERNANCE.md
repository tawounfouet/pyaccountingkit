# Gouvernance des sources OHADA/CEMAC

## EBNL

Le PDF est image-only et reste l'autorité visuelle. Le Markdown OCR est `canonical_eligibility=false` tant que les artefacts OCR ne sont pas corrigés par revue contre le scan.

## PCEMF — liste autonome

Le PDF autonome est visuel. Son Markdown est reconstruit page par page depuis la section identique du PCEMF complet : il sert à la comparaison, pas comme source textuelle canonique indépendante.

## SHA-256

Les 12 artefacts du corpus sont hashés dans les manifests.

## Mise à jour 0.7.1 — SYCEBNL complet

La source primaire EBNL est désormais `SYSCEBNL_Acte_Uniforme_2023.pdf` (438 pages), avec `authority_level=official_primary_normative_source`.

L'ancien PDF de 29 pages devient une source secondaire de validation du plan et son Markdown OCR reste non canonique.

Le corpus de la famille OHADA/CEMAC référencé dans les manifests compte désormais **13 artefacts**, tous vérifiés par SHA-256 ; 11 sont éligibles comme sources canoniques et 2 sont bloqués comme dérivés OCR non autoritaires.
