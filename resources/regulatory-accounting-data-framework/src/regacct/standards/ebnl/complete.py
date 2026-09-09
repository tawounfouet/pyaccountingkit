from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from regacct.io import dump_json, load_json
from regacct.framework.rag.bm25 import build_markdown_page_index

DOC_ID = "ohada-sycebnl-2023-full-act"
DOC_REL = "standards/ohada-ebnl/2023/sources/SYSCEBNL_Acte_Uniforme_2023.pdf"
PAGE_COUNT = 438

# Title pages verified against the official visual source. Some groups share one source page.
GROUP_TITLE_PAGES: dict[str, int] = {
    # Class 1
    "10":107,"11":110,"12":112,"13":114,"14":116,"15":118,"16":120,"17":124,"18":127,"19":130,
    # Class 2
    "20":136,"21":138,"22":141,"23":144,"24":148,"25":151,"26":153,"27":155,"28":158,"29":161,
    # Class 3
    "31":168,"32":170,"33":173,"34":175,"35":177,"36":178,"37":181,"38":184,"39":186,
    # Class 4
    "40":189,"41":193,"42":199,"43":201,"44":203,"45":205,"46":207,"47":210,"48":212,"49":216,
    # Class 5
    "50":218,"51":220,"52":222,"53":224,"55":226,"56":228,"57":230,"58":232,"59":235,
    # Class 6 (62 and 63 are presented together)
    "60":238,"61":241,"62":243,"63":243,"64":247,"65":250,"66":254,"67":258,"68":261,"69":263,
    # Class 7
    "70":266,"71":268,"72":270,"73":272,"75":275,"77":279,"78":281,"79":283,
    # Class 8
    "81":288,"82":290,"83":292,"84":295,"85":297,"86":299,"87":301,"88":303,
    # Class 9
    "90":306,"91":306,"92":308,"93":308,"94":308,"95":308,"96":308,"97":308,"98":308,"99":308,
}

CLASS_PAGE_RANGES = {
    "1": [106,132], "2": [133,164], "3": [165,187], "4": [188,217],
    "5": [218,237], "6": [238,264], "7": [265,286], "8": [287,304], "9": [305,308],
}

SPECIFIC_OPERATIONS = [
    (1, "Fonds propres des associations et ordres professionnels", 311, 318, ["fonds_propres","associations","ordres_professionnels"]),
    (2, "Fonds affectés et reportés des associations et ordres professionnels", 319, 324, ["fonds_affectes","fonds_reportes"]),
    (3, "Fonds propres des projets de développement et assimilés", 325, 328, ["projets_de_developpement","fonds_propres"]),
    (4, "Dons", 329, 332, ["dons","legs","liberalites"]),
    (5, "Cotisations des membres et versements des fondateurs", 333, 334, ["cotisations","fondateurs"]),
    (6, "Autres opérations spécifiques", 335, 338, ["operations_specifiques"]),
]

ARTICLE_PAGES = {
    1:15,2:15,3:16,4:16,5:16,6:17,7:17,8:18,9:18,
    10:19,11:19,12:19,13:19,14:19,15:19,16:20,17:21,
    18:22,19:22,20:23,21:23,22:23,23:24,24:24,25:24,26:24,27:24,28:25,
}

DEFINITIONS_BY_PAGE = {
    34:["Adhérents","Association","Bailleur de fonds","Bénévole","Commodat","Consomptible"],
    35:["Contributions","Contribution volontaire en nature","Cotisations","Déficit","Denier du culte","Dîme","Donation","Donation temporaire d'usufruit"],
    36:["Don manuel","Dotation consomptible","Dotation non consomptible","Droit d'entrée","EBNL","Excédent","Exercice","Fondateurs"],
    37:["Fondation","Fonds affectés","Fonds d'administration","Fonds de dotation","Fonds dédiés","Fonds propres provenant de legs et dons d'immobilisations","Fonds reportés"],
    38:["Générosité","Legs","Mécénat","Mutuelle"],
    39:["Ordre professionnel","Parrainage","Potentiel de service","Projet de développement","Projet de développement durable"],
    40:["Subvention d'équilibre","Subvention d'exploitation","Subventions d'investissement","Subventions versées","Tiers financeurs","Testateur","Usager","Waqf"],
    41:["Zakat"],
}

POSTULATES = [
    ("entity", "Postulat de l'entité", 46),
    ("accrual", "Postulat de la comptabilité d'engagement ou d'exercice", 46),
    ("period_specialization", "Postulat de la spécialisation des exercices", 46),
    ("method_consistency", "Postulat de la permanence des méthodes", 46),
    ("substance_over_form", "Postulat de la prééminence de la réalité économique sur l'apparence juridique", 46),
]
CONVENTIONS = [
    ("historical_cost", "Convention du coût historique", 52),
    ("prudence", "Convention de prudence", 52),
    ("regularity_sincerity", "Convention de régularité et sincérité", 52),
    ("opening_balance_correspondence", "Convention de la correspondance bilan de clôture - bilan d'ouverture", 52),
    ("materiality", "Convention de l'importance significative", 52),
]
QUALITATIVE = [
    ("relevance", "Pertinence", 56),
    ("faithful_representation", "Représentation fidèle", 57),
    ("comparability", "Comparabilité", 58),
    ("verifiability", "Vérifiabilité", 58),
    ("timeliness", "Rapidité", 59),
    ("understandability", "Compréhensibilité", 59),
]


def _source_ref(page: int, section: str | None = None) -> dict[str, Any]:
    out = {"document_id": DOC_ID, "page_pdf": page}
    if section:
        out["section"] = section
    return out


def build_legal_registry() -> dict:
    articles = []
    for n in range(1,29):
        if n <= 3:
            chapter = "Dispositions générales"
        elif n <= 16:
            chapter = "Etats financiers annuels"
        elif n <= 23:
            chapter = "Moyens de contrôle"
        elif n <= 27:
            chapter = "Dispositions pénales"
        else:
            chapter = "Dispositions finales"
        record = {
            "article_number": n,
            "chapter": chapter,
            "page_pdf": ARTICLE_PAGES[n],
            "source": _source_ref(ARTICLE_PAGES[n], chapter),
            "text_transcription_status": "visual_source_not_retranscribed_in_dataset",
        }
        if n == 4:
            record["structured_facts"] = {
                "association_order_complete_set": ["Bilan","Compte de résultat","Tableau des flux de trésorerie","Notes annexes"],
                "development_project_complete_set": ["Tableau emplois-ressources","Tableau d'exécution budgétaire","Tableau de réconciliation de trésorerie","Bilan","Compte d'exploitation","Notes annexes"],
            }
        if n == 6:
            record["structured_facts"] = {
                "sm_treasury_threshold_value": 30000000,
                "currency": "XAF",
                "threshold_categories": [
                    "subventions reçues",
                    "cotisations et autres revenus",
                    "dons reçus",
                    "ressources des projets de développement",
                    "autres ressources annuelles",
                ],
                "rule_note": "The official article contains category-specific annual-resource thresholds; no additional eligibility inference is generated.",
            }
        if n == 28:
            record["structured_facts"] = {"effective_from": "2024-01-01"}
        articles.append(record)
    return {
        "standard_id":"ohada-ebnl","edition":"2023","document_id":DOC_ID,
        "registry_type":"legal_act_article_registry",
        "articles": articles,
        "statistics":{"articles":len(articles),"first_article":1,"last_article":28},
        "source_policy":{"official_pdf_is_authority":True,"invented_legal_rules_allowed":False},
    }


def build_conceptual_framework() -> dict:
    definitions = []
    for page, terms in DEFINITIONS_BY_PAGE.items():
        for term in terms:
            definitions.append({"term_source":term,"page_pdf":page,"source":_source_ref(page,"Définitions")})
    return {
        "standard_id":"ohada-ebnl","edition":"2023","document_id":DOC_ID,
        "part":"PARTIE 1 — DEFINITIONS ET CADRE CONCEPTUEL",
        "source_range":[31,67],
        "definitions": definitions,
        "postulates":[{"concept_id":i,"label_source":l,"page_pdf":p,"source":_source_ref(p,"Postulats comptables")} for i,l,p in POSTULATES],
        "conventions":[{"concept_id":i,"label_source":l,"page_pdf":p,"source":_source_ref(p,"Conventions comptables")} for i,l,p in CONVENTIONS],
        "qualitative_characteristics":[{"concept_id":i,"label_source":l,"page_pdf":p,"source":_source_ref(p,"Caractéristiques qualitatives")} for i,l,p in QUALITATIVE],
        "financial_statement_elements": [
            {"element":"actif","source":_source_ref(59,"Composantes des grandes masses du bilan")},
            {"element":"passif","source":_source_ref(60,"Passif")},
            {"element":"fonds propres","source":_source_ref(61,"Fonds propres")},
            {"element":"charges","source":_source_ref(61,"Composantes des grandes masses du compte de résultat")},
            {"element":"produits","source":_source_ref(61,"Composantes des grandes masses du compte de résultat")},
        ],
        "statement_structure": {
            "associations_and_professional_orders": ["Bilan","Compte de résultat","Tableau de flux de trésorerie","Notes"],
            "development_projects": ["Tableau emplois-ressources","Tableau de suivi budgétaire","Tableau de réconciliations de trésorerie","Bilan","Compte d'exploitation","Notes"],
            "source":_source_ref(62,"Structure des états financiers"),
        },
        "measurement_sections": [
            {"topic":"formes de valeur","page_range":[62,64]},
            {"topic":"règles d'évaluation","page_range":[64,65]},
            {"topic":"règles de comptabilisation","page_range":[65,67]},
            {"topic":"règles de décomptabilisation","page_range":[67,67]},
        ],
        "statistics":{"definitions":len(definitions),"postulates":len(POSTULATES),"conventions":len(CONVENTIONS),"qualitative_characteristics":len(QUALITATIVE)},
        "source_policy":{"definitions_are_source_terms_not_model_redefinitions":True,"semantic_inference":False},
    }


def build_v2_account_functioning(v1: dict) -> dict:
    groups = [n for n in v1["nodes"] if n["node_type"] == "group"]
    by_code = {g["ref_code"]: g for g in groups}
    missing = sorted(set(by_code) - set(GROUP_TITLE_PAGES))
    extra = sorted(set(GROUP_TITLE_PAGES) - set(by_code))
    bindings=[]
    for code in sorted(by_code, key=lambda c:(int(c[0]), int(c))):
        node=by_code[code]
        page=GROUP_TITLE_PAGES.get(code)
        cls=code[0]
        bindings.append({
            "binding_id":f"ebnl2023:functioning:{code}",
            "group_code":code,
            "group_node_id":node["node_id"],
            "label_source":node["label_source"],
            "title_page_pdf":page,
            "class_source_range":CLASS_PAGE_RANGES[cls],
            "source":_source_ref(page or CLASS_PAGE_RANGES[cls][0],f"Compte {code}") if page else _source_ref(CLASS_PAGE_RANGES[cls][0],f"Classe {cls}"),
            "source_binding_status":"visual_title_page_verified" if page else "class_range_only",
            "structured_section_schema":["contenu","subdivisions","commentaires","fonctionnement_débit","fonctionnement_crédit","exclusions","éléments_de_contrôle"],
            "field_transcription_status":"visual_source_bound_not_fully_retranscribed",
        })
    return {
        "standard_id":"ohada-ebnl","edition":"2023","document_id":DOC_ID,
        "dataset_version":"v2_source_registry_0.7.1",
        "source_range":[106,308],
        "account_functioning_model":{
            "granularity":"two_digit_account_group_source_binding",
            "fields_supported":["content","subdivisions","comments","debit_usage","credit_usage","exclusions","control_elements"],
            "executable_posting_rules_generated":False,
            "semantic_rule_inference":False,
            "visual_source_is_authority":True,
        },
        "group_bindings":bindings,
        "class_ranges":[{"class_number":int(k),"page_range":v} for k,v in CLASS_PAGE_RANGES.items()],
        "statistics":{"group_bindings":len(bindings),"visual_title_pages_bound":sum(1 for x in bindings if x["title_page_pdf"]),"missing_group_title_pages":missing,"extra_title_page_codes":extra},
    }


def build_specific_operations() -> dict:
    rows=[]
    for n,title,start,end,tags in SPECIFIC_OPERATIONS:
        rows.append({
            "chapter_number":n,"title_source":title,"page_range":[start,end],"topic_tags":tags,
            "source":_source_ref(start,title),
            "treatment_extraction_status":"chapter_source_bound",
            "executable_rules_generated":False,
        })
    return {
        "standard_id":"ohada-ebnl","edition":"2023","document_id":DOC_ID,
        "part":"PARTIE 3 — OPERATIONS ET PROBLEMES SPECIFIQUES",
        "source_range":[309,338],"chapters":rows,
        "statistics":{"chapters":len(rows)},
        "source_policy":{"no_treatment_invented_beyond_source":True},
    }


def build_reporting() -> dict:
    profiles=[
        {
            "profile_id":"association_professional_order",
            "label_source":"Associations et ordres professionnels",
            "legal_basis":{"article":4,"page_pdf":16},
            "chapter_page":345,
            "statements":[
                {"statement_id":"balance_sheet","label_source":"Bilan","model_page_pdf":346},
                {"statement_id":"income_statement","label_source":"Compte de résultat","model_page_pdf":347},
                {"statement_id":"cash_flow_statement","label_source":"Tableau des flux de trésorerie","model_page_pdf":348},
                {"statement_id":"notes","label_source":"Notes annexes","model_page_pdf":349,"source_range":[349,396]},
            ],
        },
        {
            "profile_id":"development_project",
            "label_source":"Projets de développement et assimilés",
            "legal_basis":{"article":4,"page_pdf":16},
            "chapter_page":397,
            "statements":[
                {"statement_id":"uses_resources","label_source":"Tableau emplois-ressources","model_page_pdf":398},
                {"statement_id":"budget_execution","label_source":"Tableau d'exécution budgétaire","model_page_pdf":399},
                {"statement_id":"treasury_reconciliation","label_source":"Tableau de réconciliation de trésorerie","model_page_pdf":400},
                {"statement_id":"balance_sheet","label_source":"Bilan","model_page_pdf":401},
                {"statement_id":"operating_statement","label_source":"Compte d'exploitation","model_page_pdf":402},
                {"statement_id":"notes","label_source":"Notes annexes","model_page_pdf":403,"source_range":[403,432]},
            ],
        },
        {
            "profile_id":"minimal_cash_system",
            "label_source":"Système Minimal de Trésorerie",
            "legal_basis":{"article":6,"page_pdf":17},
            "chapter_page":433,
            "eligibility_thresholds":[
                {"category":"subventions reçues","comparator":"<","value":30000000,"currency":"XAF"},
                {"category":"cotisations et autres revenus","comparator":"<","value":30000000,"currency":"XAF"},
                {"category":"dons reçus","comparator":"<","value":30000000,"currency":"XAF"},
                {"category":"ressources des projets de développement","comparator":"<","value":30000000,"currency":"XAF"},
                {"category":"autres ressources annuelles","comparator":"<","value":30000000,"currency":"XAF"},
            ],
            "statements":[
                {"statement_id":"balance_sheet","label_source":"Bilan","model_page_pdf":434},
                {"statement_id":"income_statement","label_source":"Compte de résultat","model_page_pdf":435},
                {"statement_id":"notes","label_source":"Notes annexes","model_page_pdf":435,"source_range":[435,438]},
            ],
        },
    ]
    for p in profiles:
        p["source"]=_source_ref(p["chapter_page"],p["label_source"])
        for s in p["statements"]:
            s["source"]=_source_ref(s["model_page_pdf"],s["label_source"])
            s["line_level_extraction_status"]="visual_template_bound_not_exhaustively_transcribed"
    return {
        "standard_id":"ohada-ebnl","edition":"2023","document_id":DOC_ID,
        "dataset_version":"v3_reporting_profiles_0.7.1",
        "part":"PARTIE 4 — PRESENTATION DES ETATS FINANCIERS","source_range":[339,438],
        "general_principles_range":[341,344],"profiles":profiles,
        "statistics":{"profiles":3,"statement_models":sum(len(p["statements"]) for p in profiles),"sm_treasury_threshold_rules":5},
        "execution_policy":{"automatic_filing_generation":False,"template_visual_verification_required":True},
    }


def build_disclosures(reporting: dict) -> dict:
    rows=[]
    for p in reporting["profiles"]:
        notes=next(s for s in p["statements"] if s["statement_id"]=="notes")
        rows.append({
            "profile_id":p["profile_id"],"label_source":p["label_source"],
            "notes_model_page_pdf":notes["model_page_pdf"],"source_range":notes.get("source_range",[notes["model_page_pdf"],notes["model_page_pdf"]]),
            "source":_source_ref(notes["model_page_pdf"],"Notes annexes"),
            "requirement_registry_status":"source_range_and_template_registry_implemented",
            "field_level_requirements_exhaustively_transcribed":False,
        })
    return {
        "standard_id":"ohada-ebnl","edition":"2023","document_id":DOC_ID,
        "registry_type":"disclosure_source_registry","profiles":rows,
        "statistics":{"profiles":len(rows)},
        "source_policy":{"no_disclosure_requirement_invented":True,"visual_template_remains_authority":True},
    }


def page_section(page: int) -> tuple[str,str]:
    if page <= 14: return "front_matter","Journal officiel / sommaires"
    if page <= 26: return "acte_uniforme","Acte uniforme"
    if page <= 30: return "annex_front_matter","Annexe SYCEBNL"
    if page <= 42: return "part1_definitions","PARTIE 1 — Définitions"
    if page <= 68: return "part1_conceptual_framework","PARTIE 1 — Cadre conceptuel"
    if page <= 74: return "part2_accounting_framework","PARTIE 2 — Cadre comptable"
    if page <= 105: return "part2_chart","PARTIE 2 — Structure du plan de comptes"
    if page <= 308: return "part2_account_functioning","PARTIE 2 — Contenu et fonctionnement des comptes"
    if page <= 338: return "part3_specific_operations","PARTIE 3 — Opérations et problèmes spécifiques"
    if page <= 344: return "part4_reporting_principles","PARTIE 4 — Principes généraux"
    if page <= 396: return "part4_association_reporting","PARTIE 4 — Associations et ordres professionnels"
    if page <= 432: return "part4_project_reporting","PARTIE 4 — Projets de développement et assimilés"
    return "part4_smt_reporting","PARTIE 4 — Système Minimal de Trésorerie"


def _page_title_bindings(v2:dict, specific:dict, reporting:dict) -> dict[int,list[str]]:
    d:dict[int,list[str]]=defaultdict(list)
    for b in v2["group_bindings"]:
        if b["title_page_pdf"]:
            d[b["title_page_pdf"]].append(f"Compte {b['group_code']} — {b['label_source']}")
    for c in specific["chapters"]:
        d[c["page_range"][0]].append(f"Chapitre {c['chapter_number']} — {c['title_source']}")
    for p in reporting["profiles"]:
        d[p["chapter_page"]].append(p["label_source"])
        for s in p["statements"]:
            d[s["model_page_pdf"]].append(s["label_source"])
    return d


def build_source_page_registry(root: Path, v2:dict, specific:dict, reporting:dict) -> tuple[dict,Path]:
    pdf_path=root/DOC_REL
    try:
        import fitz  # PyMuPDF; optional project extra [pdf]
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is required to rebuild the EBNL complete source registry. Install the project with the 'pdf' extra.") from exc
    doc=fitz.open(pdf_path)
    if len(doc)!=PAGE_COUNT:
        raise ValueError(f"Unexpected SYCEBNL page count: {len(doc)}")
    titles=_page_title_bindings(v2,specific,reporting)
    pages=[]
    router_lines=["# SYCEBNL 2023 — Source Page Router", "", "This derived router contains page metadata, not a verbatim OCR transcription. The bundled official PDF remains the visual and normative authority.", ""]
    substantive=0
    for page_num in range(1,PAGE_COUNT+1):
        page=doc[page_num-1]
        native=page.get_text("text").strip()
        chars=len(native)
        is_substantive=chars>=300
        substantive += int(is_substantive)
        section_id,section_label=page_section(page_num)
        page_titles=titles.get(page_num,[])
        rec={
            "page_pdf":page_num,"section_id":section_id,"section_label":section_label,
            "title_bindings":page_titles,
            "native_text_chars":chars,
            "native_text_quality":"substantive" if is_substantive else "sparse_or_header_only",
            "image_objects":len(page.get_images(full=True)),
            "visual_source_authority":True,
        }
        pages.append(rec)
        router_lines += [f"<!-- Page PDF {page_num} -->", f"# {section_label}"]
        for t in page_titles:
            router_lines.append(f"## {t}")
        router_lines.append(f"Source page {page_num}. Visual authority: official SYCEBNL PDF. Native text layer: {rec['native_text_quality']} ({chars} chars).")
        if page_titles:
            router_lines.append("Indexed source bindings: " + " ; ".join(page_titles))
        router_lines.append("")
    router_path=root/"standards/ohada-ebnl/2023/sources/SYSCEBNL_2023_SOURCE_ROUTER.md"
    router_path.write_text("\n".join(router_lines),encoding="utf-8")
    registry={
        "standard_id":"ohada-ebnl","edition":"2023","document_id":DOC_ID,
        "page_count":PAGE_COUNT,"pages":pages,
        "statistics":{"pages":PAGE_COUNT,"pages_with_substantive_native_text":substantive,"pages_sparse_or_header_only":PAGE_COUNT-substantive,"pages_with_title_bindings":sum(1 for p in pages if p["title_bindings"])},
        "extraction_policy":{
            "pdf_visual_source_is_authority":True,
            "full_verbatim_ocr_claimed":False,
            "router_is_metadata_not_normative_text":True,
            "reason":"The official PDF is image-heavy; the release binds structured datasets to source pages rather than silently inventing or normalizing unread text.",
        },
    }
    return registry,router_path


def build_capability_status() -> dict:
    return {
        "standard_id":"ohada-ebnl","edition":"2023","source_bundle_scope":"complete_official_act_438_pages",
        "capabilities":{
            "v0_chart":{"status":"implemented","source":"official chart extract + reviewed structure"},
            "v1_structure":{"status":"implemented","source":"official chart extract + structural visual review ledger"},
            "legal_act_registry":{"status":"implemented","source":DOC_ID},
            "conceptual_framework":{"status":"implemented_source_registry","source":DOC_ID},
            "v2_account_functioning":{"status":"implemented_source_registry","source":DOC_ID,"executable_rules_generated":False,"invented_rules_allowed":False},
            "specific_operations":{"status":"implemented_source_registry","source":DOC_ID,"executable_rules_generated":False},
            "v3_reporting":{"status":"implemented_reporting_profiles_and_visual_template_registry","source":DOC_ID,"automatic_template_generation":False,"invented_templates_allowed":False},
            "disclosures":{"status":"implemented_source_registry","source":DOC_ID,"field_level_exhaustive_transcription":False},
            "full_verbatim_ocr":{"status":"not_claimed","reason":"image-heavy official source; page router + visual authority retained"},
        },
        "normative_source_gap_closed":True,
        "remaining_engineering_gap":"Line-level transcription of image-based detailed functioning/reporting templates remains a separate extraction layer; it is not required to establish normative source completeness.",
    }


def build_complete(root: Path) -> dict:
    v1=load_json(root/"datasets/structured/ebnl_2023_v1_structure.json")
    legal=build_legal_registry(); conceptual=build_conceptual_framework(); v2=build_v2_account_functioning(v1)
    specific=build_specific_operations(); reporting=build_reporting(); disclosures=build_disclosures(reporting)
    status=build_capability_status()
    page_registry,router_path=build_source_page_registry(root,v2,specific,reporting)

    dump_json(root/"datasets/annotated/ebnl_2023_legal_act_registry.json",legal)
    dump_json(root/"datasets/annotated/ebnl_2023_conceptual_framework.json",conceptual)
    dump_json(root/"datasets/annotated/ebnl_2023_v2_account_functioning.json",v2)
    dump_json(root/"datasets/annotated/ebnl_2023_specific_operations.json",specific)
    dump_json(root/"datasets/annotated/ebnl_2023_disclosures_registry.json",disclosures)
    dump_json(root/"datasets/annotated/ebnl_2023_source_page_registry.json",page_registry)
    dump_json(root/"datasets/reporting/ebnl_2023_v3_reporting.json",reporting)
    dump_json(root/"validation/review/ebnl_2023_capability_status.json",status)
    # Backward compatible path: its content now records the closed normative-source gap.
    dump_json(root/"validation/review/ebnl_2023_capability_gaps.json",status)

    rag=build_markdown_page_index(router_path,"ohada-sycebnl-2023-source-router-v2",max_chars=2400)
    rag["source_quality_notice"]={
        "official_pdf_is_visual_authority":True,
        "router_is_metadata_not_verbatim_ocr":True,
        "use_for_authoritative_quote_without_pdf_check":False,
        "complete_page_routing":True,
    }
    dump_json(root/"rag/indexes/ebnl-sycebnl-2023-source-router-v2.json",rag)
    return {
        "legal":legal,"conceptual":conceptual,"v2":v2,"specific":specific,"reporting":reporting,
        "disclosures":disclosures,"page_registry":page_registry,"rag":rag,"capability_status":status,
    }
