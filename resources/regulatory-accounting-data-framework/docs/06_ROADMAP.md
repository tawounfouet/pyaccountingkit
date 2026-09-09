# Roadmap

## 0.1 — Socle (ce livrable)
- [x] modèles communs ; manifests ; registry ; provenance ; V0 ; V1 ; validation graphe ; parser reporting minimal ; évaluateur prudentiel ; ranking crosswalk ; workflow revue ; CLI ; profils initiaux.

## 0.2 — Migration PCEMF
- [ ] migrer les datasets V0→V6, les parseurs complets, le RAG SYSCOHADA et les tests historiques.

## 0.3 — PCG 2026
- [ ] V0 plan de comptes ; V1 structure + facultatif/italique ; V2 fonctionnement des comptes + articles ; reporting ; doctrine IR ; tests.

## 0.4 — Extensions ANC
- [ ] banque ; assurance ; non-lucratif ; logement social ; gestion d'actifs ; comptes consolidés.

## 0.5 — Crosswalks
- [ ] PCG 2024↔2026 ; PCG↔SYSCOHADA ; PCG↔PCEMF ; PCG↔IFRS avec corpus adapté et revue humaine.

## 0.6 — Publication
- [ ] JSONL ; Parquet ; PostgreSQL ; API ; dbt ; knowledge graph.


## 0.4 — FR Non-Profit 2026

- [x] source ANC 2026 primaire ;
- [x] ORCOM 2025 comme référence praticien secondaire ;
- [x] modèle générique `StandardOverlay` ;
- [x] Art. 320-1 héritage PCG ;
- [x] Art. 320-2 additions / overrides ;
- [x] plan effectif `fr-pcg + nonprofit overlay` ;
- [x] registre d'articles du Tome I ANC 2018-06 ;
- [x] IR1→IR5 ;
- [x] V2 fonctionnement des comptes ;
- [x] disclosures 431-* / 432-* ;
- [x] Bilan + compte de résultat ;
- [x] CROD + CER générosité du public ;
- [x] RAG lexical ;
- [x] comparaison ORCOM avec blocage de promotion canonique ;
- [x] tests de provenance et d'héritage.

## 0.5 — OHADA Family Foundation

- [x] AccountingFamily
- [x] StandardRelation
- [x] source roles / quality / canonical eligibility
- [x] `ohada-accounting`
- [x] SYSCOHADA 2017 member
- [x] EBNL 2023 specialized member
- [x] PCEMF 2010 sectoral member
- [x] no false inheritance
- [x] temporal guard PCEMF 2010 vs SYSCOHADA 2017
- [x] 12 source files with SHA-256
- [x] EBNL OCR blocked before canonical ingestion
- [x] neutral AccountingConcept registry
- [x] 0 automatic ConceptBinding

## 0.6 — SYSCOHADA 2017 Complete

- [ ] V0
- [ ] V1
- [ ] V2 accounting knowledge
- [ ] V3 reporting
- [ ] applications
- [ ] Guide RAG

## 0.7 — OHADA EBNL

- [ ] OCR review
- [ ] V0/V1
- [ ] complete normative corpus before V2/V3

## 0.8 — PCEMF 2010 Complete

- [ ] consolidate full plan + list + annexes
- [ ] migrate historical V0→V6
- [ ] reporting/prudential complete

## 0.9 — OHADA Cross-Standard

- [ ] PCEMF ↔ SYSCOHADA
- [ ] EBNL ↔ SYSCOHADA
- [ ] ConceptBinding candidates
- [ ] evidence + human review

## 0.6 — SYSCOHADA 2017 Complete
- [x] V0 1 403 entrées source
- [x] V1 graphe + 9 classes
- [x] 4 parties / 56 chapitres / 33 sections / 142 applications
- [x] anomalies de numérotation préservées
- [x] subdivisions locales résolues sans modifier le plan
- [x] V2 accounting knowledge
- [x] consolidation 128→142
- [x] V3 reporting + Application 127
- [x] limites Titre IX explicites
- [x] RAG 437 pages

## 0.7 — OHADA EBNL
- [x] scan PDF conservé comme autorité visuelle
- [x] OCR Markdown conservé comme source dérivée
- [x] ledger de revue visuelle
- [x] corrections structurelles vérifiées
- [x] V0 : 84 groupes / 1 049 occurrences / 1 048 codes
- [x] anomalie source 4555 préservée
- [x] V1 avec identités par occurrence
- [x] double scope de classe 9
- [x] delta structurel EBNL ↔ SYSCOHADA
- [x] RAG OCR avec avertissement qualité
- [x] V2/V3 bloqués tant que le corpus normatif complet n'est pas fourni


## 0.7.1 — OHADA EBNL Complete — DONE

- complete 438-page official normative source bundled;
- legal + conceptual registries;
- V2 source bindings for all 84 groups;
- six specific-operation chapters;
- three reporting profiles / 13 official templates;
- disclosure source registry;
- 438-page source router;
- future optional work: fine visual transcription of V2/V3 cells and paragraphs.
