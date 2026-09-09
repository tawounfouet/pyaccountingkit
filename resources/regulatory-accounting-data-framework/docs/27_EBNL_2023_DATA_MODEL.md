# Modèle de données EBNL 2023

```text
PDF Scan
   |
   +--> OCR Markdown (inchangé)
   |
   +--> Visual Review Ledger
           |
           v
      V0 Reviewed Structure
           |
           v
      V1 Account Graph
```

## Identité

Un numéro de compte n'est pas toujours une identité unique.

```text
ref_code = 4555
```

possède deux occurrences imprimées.

Les identités sont donc :

```text
account:ohada-ebnl:2023:4555:occ01
account:ohada-ebnl:2023:4555:occ02
```

Le `ref_code` source reste `4555`.

## Extension 0.7.1 — corpus complet

La V0/V1 ci-dessus reste inchangée. La source complète ajoute désormais :

```text
Full Official Act — 438 pages
   |
   +--> Legal Registry (Articles 1–28)
   +--> Conceptual Framework
   +--> V2 Account Functioning Source Registry
   +--> Specific Operations Registry
   +--> V3 Reporting Profiles
   +--> Disclosures Registry
   +--> 438-page Source Router
```

Le modèle distingue la **complétude normative** de la **complétude OCR**. Les pages image sont liées aux objets structurés sans prétendre disposer d'une transcription textuelle parfaite.
