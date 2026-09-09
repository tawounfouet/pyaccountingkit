from pathlib import Path
import json, re, unicodedata
from collections import Counter, defaultdict

PAGE_RE = re.compile(r"<!--\s*Page PDF\s+(\d+)\s*-->")
CLASS_RE = re.compile(r"^##\s+CLASSE\s+(\d+)\s*[-—–]+\s*(.+?)\s*$", re.I)
GROUP_RE = re.compile(r"^###\s+(\d{2})\s*-\s*(.+?)\s*$")
GOOD_RE = re.compile(r"^-\s+\*\*(\d{2,6})\*\*\s*-\s*(.+?)\s*$")
ITALIC_RE = re.compile(r"^\*\s+(\d{2,6})\s+(.+?)\s+\*$")
BARE_DOT_RE = re.compile(r"^(\d{2,6})\.\s+(.+?)\s*$")
DOLLAR_RE = re.compile(r"^\$(\d{2,6})\s+(.+?)\s*$")
PAREN_RE = re.compile(r"^(\d{2,6})\)\s+(.+?)\s*$")

CLASS_LABELS = {
    "1":"COMPTES DE RESSOURCES DURABLES",
    "2":"COMPTES D’ACTIF IMMOBILISE",
    "3":"COMPTES DES STOCKS",
    "4":"COMPTES DE TIERS",
    "5":"COMPTES DE TRESORERIE",
    "6":"COMPTES DE CHARGES DES ACTIVITES ORDINAIRES",
    "7":"COMPTES DE PRODUITS DES ACTIVITES ORDINAIRES",
    "8":"COMPTES DES AUTRES CHARGES ET DES AUTRES PRODUITS",
    "9":"COMPTES DE CLASSE 9",
}

CLASS_PAGES = {
    "1":1,"2":3,"3":9,"4":11,"5":16,"6":18,"7":24,"8":27,"9":29
}

CLASS9_SCOPES = [
    {"scope_id":"voluntary_contributions","label_source":"COMPTE DES CONTRIBUTIONS VOLONTAIRES EN NATURE","group_codes":["90","91"],"page_pdf":29},
    {"scope_id":"management_accounting","label_source":"COMPTE DE LA COMPTABILITE ANALYTIQUE DE GESTION","group_codes":["92","93","94","95","96","97","98","99"],"page_pdf":29},
]


def normalize_search(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = value.lower().replace("’","'").replace("–","-").replace("—","-")
    value = re.sub(r"[^a-z0-9]+"," ",value)
    return re.sub(r"\s+"," ",value).strip()


def load_review_ledger(path):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    by_line={x["source_line_md"]:x for x in data["line_corrections"]}
    return data, by_line


def _page_class(page):
    if page <= 2: return "1"
    if page <= 8: return "2"
    if page <= 10: return "3"
    if page <= 15: return "4"
    if page <= 17: return "5"
    if page <= 23: return "6"
    if page <= 26: return "7"
    if page <= 28: return "8"
    return "9"


def parse_plan_markdown(path, review_ledger_path):
    lines=Path(path).read_text(encoding="utf-8").splitlines()
    review, corrections=load_review_ledger(review_ledger_path)
    page=None
    current_group=None
    source_order=0
    last_account_by_length={}
    records=[]
    group_occurrences=[]
    skipped_heading_lines={1330}  # OCR made group 79 look like an account.
    malformed_account_injected={1377}

    # Static class records from visually checked page headings.
    classes=[]
    for code,label in CLASS_LABELS.items():
        classes.append({
            "record_id":f"ebnl2023:class:{code}",
            "record_type":"class",
            "code_source":code,
            "label_source":label,
            "page_pdf":CLASS_PAGES[code],
            "review_status":"visual_heading_verified",
        })

    for lineno,line in enumerate(lines,1):
        if m:=PAGE_RE.match(line):
            page=int(m.group(1))
            current_group=None
            last_account_by_length.clear()
            continue

        # Explicit visual correction takes precedence.
        correction=corrections.get(lineno)
        if correction and correction["kind"]=="group_heading":
            current_group=correction["reviewed_code"]
            last_account_by_length.clear()
            source_order+=1
            group_occurrences.append({
                "record_id":f"ebnl2023:group:p{page:02d}:l{lineno:04d}",
                "source_order":source_order,
                "record_type":"group",
                "code_source":current_group,
                "label_source":correction["reviewed_label"],
                "label_ocr":line,
                "class_number_source":int(current_group[0]),
                "page_pdf":page,
                "source_line_md":lineno,
                "review_status":"visual_correction",
                "source_rows":[line],
            })
            continue

        def source_parent_and_register(code):
            shorter=[k for k in last_account_by_length if k < len(code)]
            source_parent=last_account_by_length[max(shorter)] if shorter else current_group
            for k in list(last_account_by_length):
                if k >= len(code):
                    del last_account_by_length[k]
            last_account_by_length[len(code)] = code
            return source_parent

        # Any account-code visual correction is injected directly, including OCR rows
        # that no regex can parse (e.g. "* $025 = Autres actions *").
        if correction and correction["kind"]=="account_code":
            code=correction["reviewed_code"]
            source_parent=source_parent_and_register(code)
            source_order+=1
            records.append({
                "record_id":f"ebnl2023:account:p{page:02d}:l{lineno:04d}",
                "source_order":source_order,
                "record_type":"account",
                "code_source":code,
                "label_source":correction["reviewed_label"],
                "label_ocr":line,
                "class_number_source":int(code[0]),
                "source_group_context":current_group,
                "source_parent_context":source_parent,
                "page_pdf":page,
                "source_line_md":lineno,
                "extraction_method":"visual_correction",
                "review_status":"visual_code_and_label_verified",
                "label_search":normalize_search(correction["reviewed_label"]),
                "source_rows":[line],
            })
            continue

        if m:=GROUP_RE.match(line):
            # Corrected line 893 reads 37 in OCR but is 57 in PDF.
            if lineno==893:
                continue
            current_group=m.group(1)
            last_account_by_length.clear()
            source_order+=1
            group_occurrences.append({
                "record_id":f"ebnl2023:group:p{page:02d}:l{lineno:04d}",
                "source_order":source_order,
                "record_type":"group",
                "code_source":current_group,
                "label_source":m.group(2).strip(),
                "label_ocr":m.group(2).strip(),
                "class_number_source":int(current_group[0]),
                "page_pdf":page,
                "source_line_md":lineno,
                "review_status":"ocr_structurally_valid",
                "source_rows":[line],
            })
            continue

        # Skip class headings and obvious non-account content.
        if CLASS_RE.match(line) or lineno in skipped_heading_lines:
            continue

        parsed=None
        method=None
        for name,pat in [
            ("ocr_bold",GOOD_RE),
            ("ocr_italic",ITALIC_RE),
            ("ocr_bare_dot",BARE_DOT_RE),
            ("ocr_dollar",DOLLAR_RE),
            ("ocr_paren",PAREN_RE),
        ]:
            m=pat.match(line)
            if m:
                parsed=(m.group(1),m.group(2).strip())
                method=name
                break
        if not parsed:
            continue

        code,label=parsed

        # "13. RESULTAT..." is a group heading, not account 13.
        if lineno==52:
            continue
        # OCR account-like heading 719 -> group 79.
        if lineno==1330:
            continue

        correction=corrections.get(lineno)
        if correction and correction["kind"]=="account_code":
            code=correction["reviewed_code"]
            label=correction["reviewed_label"]
            method="visual_correction"
            review_status="visual_code_and_label_verified"
        else:
            review_status="ocr_structurally_valid_label_unproofread"

        # 5022 / 2014 / 2443 / 6243 are valid bare-dot account rows.
        # Any remaining dollar-form row without a visual correction is rejected.
        if method=="ocr_dollar":
            continue

        source_parent=source_parent_and_register(code)
        source_order+=1
        records.append({
            "record_id":f"ebnl2023:account:p{page:02d}:l{lineno:04d}",
            "source_order":source_order,
            "record_type":"account",
            "code_source":code,
            "label_source":label,
            "label_ocr":parsed[1],
            "class_number_source":int(code[0]),
            "source_group_context":current_group,
            "source_parent_context":source_parent,
            "page_pdf":page,
            "source_line_md":lineno,
            "extraction_method":method,
            "review_status":review_status,
            "label_search":normalize_search(label),
            "source_rows":[line],
        })

    # Deduplicate group headings: summary + detailed headings are both printed.
    by_group=defaultdict(list)
    for g in group_occurrences:
        by_group[g["code_source"]].append(g)

    groups=[]
    for code, occs in sorted(by_group.items(), key=lambda kv:int(kv[0])):
        # Prefer visual corrections; otherwise last occurrence is the detailed heading.
        visual=[x for x in occs if x["review_status"]=="visual_correction"]
        chosen=visual[-1] if visual else occs[-1]
        chosen={**chosen}
        chosen["record_id"]=f"ebnl2023:group:{code}"
        chosen["source_occurrences"]=[
            {
                "page_pdf":x["page_pdf"],
                "source_line_md":x["source_line_md"],
                "label_source":x["label_source"],
                "review_status":x["review_status"],
            } for x in occs
        ]
        groups.append(chosen)

    # Source occurrence ambiguity.
    by_code=defaultdict(list)
    for r in records:
        by_code[r["code_source"]].append(r)
    duplicate_codes={code:rows for code,rows in by_code.items() if len(rows)>1}
    for code, rows in duplicate_codes.items():
        for idx,row in enumerate(rows,1):
            row["source_code_occurrence_index"]=idx
            row["source_code_ambiguous"]=True

    # Class 9 scopes.
    scopes=[
        {
            "record_id":f"ebnl2023:class9-scope:{x['scope_id']}",
            "record_type":"class_scope",
            "code_source":"9",
            "scope_id":x["scope_id"],
            "label_source":x["label_source"],
            "group_codes":x["group_codes"],
            "page_pdf":x["page_pdf"],
            "review_status":"visual_heading_verified",
        }
        for x in CLASS9_SCOPES
    ]

    return {
        "standard_id":"ohada-ebnl",
        "edition":"2023",
        "dataset_layer":"v0_reviewed_structure",
        "source_policy":{
            "pdf_is_visual_authority":True,
            "ocr_markdown_is_canonical_text_source":False,
            "visual_corrections_applied":len(review["line_corrections"]),
            "all_labels_fully_proofread":False,
        },
        "classes":classes,
        "class_scopes":scopes,
        "groups":groups,
        "records":records,
        "duplicate_source_codes":{
            code:[
                {
                    "record_id":r["record_id"],
                    "label_source":r["label_source"],
                    "source_group_context":r["source_group_context"],
                    "source_parent_context":r.get("source_parent_context"),
                    "page_pdf":r["page_pdf"],
                    "source_line_md":r["source_line_md"],
                } for r in rows
            ] for code,rows in sorted(duplicate_codes.items())
        },
        "statistics":{
            "classes":len(classes),
            "class_scopes":len(scopes),
            "groups":len(groups),
            "account_occurrences":len(records),
            "unique_account_codes":len(by_code),
            "duplicate_source_codes":len(duplicate_codes),
            "visual_line_corrections":len(review["line_corrections"]),
            "account_occurrences_by_class":dict(sorted(Counter(str(r["class_number_source"]) for r in records).items())),
        },
    }


def build_structure(v0):
    nodes=[]
    by_id={}
    class_ids={c["code_source"]:f"class:ohada-ebnl:2023:{c['code_source']}" for c in v0["classes"]}
    scope_ids={s["scope_id"]:f"class-scope:ohada-ebnl:2023:9:{s['scope_id']}" for s in v0["class_scopes"]}
    group_ids={g["code_source"]:f"group:ohada-ebnl:2023:{g['code_source']}" for g in v0["groups"]}

    # Classes.
    for c in v0["classes"]:
        nid=class_ids[c["code_source"]]
        n={
            "node_id":nid,"node_type":"class","standard_id":"ohada-ebnl","edition":"2023",
            "ref_code":c["code_source"],"label_source":c["label_source"],"account_class":int(c["code_source"]),
            "parent_node_id":None,"children_node_ids":[],"depth":0,"path_node_ids":[nid],"path_codes":[c["code_source"]],
            "is_leaf":False,"attributes":{"review_status":c["review_status"]},
            "provenance":{"type":"source","method":"visual_heading_review","source_refs":[{"document_id":"ohada-ebnl-plan-2023","page_pdf":c["page_pdf"]}],"confidence":1.0,"review_status":"visual_verified"},
        }
        nodes.append(n);by_id[nid]=n

    # Class 9 scopes.
    for s in v0["class_scopes"]:
        nid=scope_ids[s["scope_id"]]
        parent=class_ids["9"]
        n={
            "node_id":nid,"node_type":"class_scope","standard_id":"ohada-ebnl","edition":"2023",
            "ref_code":"9","label_source":s["label_source"],"account_class":9,
            "parent_node_id":parent,"children_node_ids":[],"depth":1,"path_node_ids":[parent,nid],"path_codes":["9",s["scope_id"]],
            "is_leaf":False,"attributes":{"scope_id":s["scope_id"],"group_codes":s["group_codes"]},
            "provenance":{"type":"source","method":"visual_heading_review","source_refs":[{"document_id":"ohada-ebnl-plan-2023","page_pdf":29}],"confidence":1.0,"review_status":"visual_verified"},
        }
        nodes.append(n);by_id[nid]=n
        by_id[parent]["children_node_ids"].append(nid)

    # Groups.
    group_scope={}
    for s in v0["class_scopes"]:
        for code in s["group_codes"]:
            group_scope[code]=s["scope_id"]

    for g in v0["groups"]:
        code=g["code_source"]
        if code[0]=="9":
            parent=scope_ids[group_scope[code]]
        else:
            parent=class_ids[code[0]]
        nid=group_ids[code]
        n={
            "node_id":nid,"node_type":"group","standard_id":"ohada-ebnl","edition":"2023",
            "ref_code":code,"label_source":g["label_source"],"account_class":int(code[0]),
            "parent_node_id":parent,"children_node_ids":[],"depth":0,"path_node_ids":[],"path_codes":[],"is_leaf":False,
            "attributes":{"source_occurrences":g["source_occurrences"],"review_status":g["review_status"]},
            "provenance":{"type":"derived","method":"reviewed_group_heading_deduplication","source_refs":[{"document_id":"ohada-ebnl-plan-2023","page_pdf":g["page_pdf"],"source_line_md":g["source_line_md"]}],"confidence":1.0,"review_status":"structurally_reviewed"},
        }
        nodes.append(n);by_id[nid]=n;by_id[parent]["children_node_ids"].append(nid)

    # Accounts; preserve duplicate source codes as occurrence nodes.
    code_seen=defaultdict(int)
    code_nodes=defaultdict(list)
    previous_by_class=defaultdict(list)
    for r in v0["records"]:
        code=r["code_source"]
        code_seen[code]+=1
        suffix=f":occ{code_seen[code]:02d}" if r.get("source_code_ambiguous") else ""
        nid=f"account:ohada-ebnl:2023:{code}{suffix}"

        # Parent policy:
        # 1) longest prior strict code prefix within class;
        # 2) source group context;
        # For a source group mismatch (e.g. printed duplicate 4555 under group 452),
        # source layout wins and the anomaly is recorded.
        prefix_candidates=[
            c for c in previous_by_class[str(r["class_number_source"])]
            if code.startswith(c) and c!=code
        ]
        longest=max(prefix_candidates,key=len) if prefix_candidates else None
        source_group=r.get("source_group_context")
        source_parent=r.get("source_parent_context")
        non_prefix_source_parent=False

        if source_parent and source_parent in code_nodes:
            parent=code_nodes[source_parent][-1]
            non_prefix_source_parent=not code.startswith(source_parent)
        elif source_parent and source_parent in group_ids:
            parent=group_ids[source_parent]
            non_prefix_source_parent=not code.startswith(source_parent)
        elif longest:
            parent=code_nodes[longest][-1]
        elif source_group and source_group in group_ids:
            parent=group_ids[source_group]
            non_prefix_source_parent=not code.startswith(source_group)
        else:
            parent=group_ids[code[:2]]

        n={
            "node_id":nid,"node_type":"account","standard_id":"ohada-ebnl","edition":"2023",
            "source_record_id":r["record_id"],"ref_code":code,"label_source":r["label_source"],
            "account_class":r["class_number_source"],"parent_node_id":parent,"children_node_ids":[],
            "depth":0,"path_node_ids":[],"path_codes":[],"is_leaf":True,
            "attributes":{
                "label_ocr":r["label_ocr"],"label_search":r["label_search"],
                "source_group_context":source_group,"source_parent_context":source_parent,
                "source_code_ambiguous":r.get("source_code_ambiguous",False),
                "source_code_occurrence_index":r.get("source_code_occurrence_index"),
                "non_prefix_source_parent":non_prefix_source_parent,
                "review_status":r["review_status"],"extraction_method":r["extraction_method"],
            },
            "provenance":{
                "type":"derived","method":"ebnl_visual_review_plus_ocr_structure_v1",
                "source_refs":[{"document_id":"ohada-ebnl-plan-2023","page_pdf":r["page_pdf"]},{"document_id":"ohada-ebnl-plan-2023-md","page_pdf":r["page_pdf"],"source_line_md":r["source_line_md"]}],
                "confidence":1.0 if r["review_status"].startswith("visual") else 0.85,
                "review_status":r["review_status"],
            },
        }
        nodes.append(n);by_id[nid]=n
        by_id[parent]["children_node_ids"].append(nid)
        code_nodes[code].append(nid)
        previous_by_class[str(r["class_number_source"])].append(code)

    def path_for(n):
        ids=[n["node_id"]];codes=[n["ref_code"]];cur=n;guard={n["node_id"]}
        while cur["parent_node_id"]:
            p=by_id[cur["parent_node_id"]]
            if p["node_id"] in guard: raise ValueError(f"cycle:{p['node_id']}")
            guard.add(p["node_id"]);ids.append(p["node_id"]);codes.append(p["ref_code"]);cur=p
        return list(reversed(ids)),list(reversed(codes))

    for n in nodes:
        ids,codes=path_for(n)
        n["path_node_ids"]=ids;n["path_codes"]=codes;n["depth"]=len(ids)-1
        n["is_leaf"]=len(n["children_node_ids"])==0

    return {
        "standard_id":"ohada-ebnl","edition":"2023","dataset_layer":"v1_structure",
        "nodes":nodes,
        "statistics":{
            "class_nodes":sum(n["node_type"]=="class" for n in nodes),
            "class_scope_nodes":sum(n["node_type"]=="class_scope" for n in nodes),
            "group_nodes":sum(n["node_type"]=="group" for n in nodes),
            "account_occurrence_nodes":sum(n["node_type"]=="account" for n in nodes),
            "unique_account_codes":len({n["ref_code"] for n in nodes if n["node_type"]=="account"}),
            "ambiguous_account_occurrence_nodes":sum(n["node_type"]=="account" and n["attributes"]["source_code_ambiguous"] for n in nodes),
            "non_prefix_source_parent_nodes":sum(n["node_type"]=="account" and n["attributes"]["non_prefix_source_parent"] for n in nodes),
            "graph_nodes":len(nodes),
            "leaf_nodes":sum(n["is_leaf"] for n in nodes),
        },
    }
