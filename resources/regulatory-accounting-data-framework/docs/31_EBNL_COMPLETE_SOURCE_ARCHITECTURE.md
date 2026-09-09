# OHADA EBNL 2023 — Complete Source Architecture

## Hiérarchie des sources

```text
Tier 1 — source normative primaire
└── SYSCEBNL_Acte_Uniforme_2023.pdf (438 pages)

Tier 2 — extrait officiel de contrôle
└── PC-EBNL_Liste des comptes.pdf (29 pages)

Tier 3 — source dérivée non normative
└── PC-EBNL_Liste des comptes.md (OCR)
```

La source Tier 1 arbitre toute divergence de contenu. Le Markdown OCR Tier 3 n'est jamais une autorité de libellé.

## Architecture des couches

```text
Official PDF
   │
   ├── page registry ───────────────► provenance / navigation
   ├── legal registry ──────────────► Articles 1–28
   ├── conceptual registry ─────────► définitions / principes
   ├── V0 / V1 ─────────────────────► plan et graphe
   ├── V2 source registry ──────────► fonctionnement des comptes
   ├── specific operations ─────────► Partie 3
   ├── V3 reporting ────────────────► profils / modèles
   ├── disclosure registry ─────────► Notes annexes
   └── source-router RAG ───────────► recherche de pages
```

## Granularité V2

Le V2 est volontairement construit au niveau du **groupe de compte à deux chiffres** : c'est le niveau auquel le SYCEBNL présente le contenu et le fonctionnement dans la Partie 2.

Chaque binding contient :

- le code du groupe ;
- le node V1 correspondant ;
- le libellé source ;
- la page de titre visuellement vérifiée ;
- la plage de classe ;
- le schéma de sections attendu ;
- l'indication explicite que le texte n'a pas été transformé en règle exécutable.

## PDF image-based

Sur 438 pages, la couche texte PDF native est majoritairement constituée d'en-têtes et pieds de page. Le framework distingue donc :

```text
source completeness    ≠ OCR completeness
source page binding    ≠ semantic extraction
accounting guidance    ≠ executable posting rule
```

Cette séparation évite qu'un artefact OCR devienne une règle comptable.

## Provenance

Le minimum de provenance pour tout objet EBNL complet est :

```json
{
  "document_id": "ohada-sycebnl-2023-full-act",
  "page_pdf": 120,
  "section": "Compte 16"
}
```

Les couches futures de transcription fine devront conserver cette provenance et ajouter leur statut de revue.
