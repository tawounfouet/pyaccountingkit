from pathlib import Path
import re
from collections import Counter

PAGE_RE=re.compile(r"<!--\s*Page PDF\s+(\d+)\s*-->")
CLASS_RE=re.compile(r"^##\s+Classe\s+(\d+)\s*-\s*(.+?)\s*$",re.I)
GROUP_RE=re.compile(r"^-\s+\*\*(\d{2})\*\*\s*-\s*(.+?)\s*$")
MAIN_RE=re.compile(r"^•\s+(\d{3})\s+(.+?)\s*$")
SUB_RE=re.compile(r"^-\s+(\d{4,6})\s+(.+?)\s*$")

def parse_plan_markdown(path):
    lines=Path(path).read_text(encoding="utf-8").splitlines()
    page=None; current_class=None; current_class_record=None; source_order=0
    classes=[]; records=[]
    for lineno,line in enumerate(lines,1):
        if m:=PAGE_RE.match(line):
            page=int(m.group(1)); continue
        if m:=CLASS_RE.match(line):
            current_class=m.group(1); source_order+=1
            current_class_record={
                "record_id":f"syscohada2017:class:l{lineno:04d}",
                "source_order":source_order,"record_type":"class","code_source":current_class,
                "label_source":m.group(2).strip(),
                "source":{"document_id":"syscohada-plan-2017-md","page_pdf":page,"section":f"Classe {current_class}","source_line_md":lineno,"snippet":line},
                "source_rows":[line],
            }
            classes.append(current_class_record); continue
        if current_class=="9" and current_class_record and current_class_record["label_source"].endswith("de la"):
            if line.strip().lower().startswith("comptabilité analytique"):
                current_class_record["label_source"]+=" "+line.strip()
                current_class_record["source_rows"].append(line); continue
        if m:=GROUP_RE.match(line):
            source_order+=1
            records.append({
                "record_id":f"syscohada2017:p{page or 0:03d}:l{lineno:04d}",
                "source_order":source_order,"record_type":"group","code_source":m.group(1),"label_source":m.group(2).strip(),
                "class_number_source":int(current_class),"source_marker":"bold_group",
                "source":{"document_id":"syscohada-plan-2017-md","page_pdf":page,"section":f"Classe {current_class}","source_line_md":lineno,"snippet":line},
                "source_rows":[line],
            }); continue
        if m:=MAIN_RE.match(line):
            source_order+=1
            records.append({
                "record_id":f"syscohada2017:p{page or 0:03d}:l{lineno:04d}",
                "source_order":source_order,"record_type":"account","source_level":"main_account",
                "code_source":m.group(1),"label_source":m.group(2).strip(),"class_number_source":int(current_class),
                "source_marker":"bullet_main",
                "source":{"document_id":"syscohada-plan-2017-md","page_pdf":page,"section":f"Classe {current_class}","source_line_md":lineno,"snippet":line},
                "source_rows":[line],
            }); continue
        if m:=SUB_RE.match(line):
            source_order+=1
            records.append({
                "record_id":f"syscohada2017:p{page or 0:03d}:l{lineno:04d}",
                "source_order":source_order,"record_type":"account","source_level":"sub_account",
                "code_source":m.group(1),"label_source":m.group(2).strip(),"class_number_source":int(current_class),
                "source_marker":"dash_subaccount",
                "source":{"document_id":"syscohada-plan-2017-md","page_pdf":page,"section":f"Classe {current_class}","source_line_md":lineno,"snippet":line},
                "source_rows":[line],
            })
    return {
        "standard_id":"ohada-syscohada","edition":"2017","dataset_layer":"v0_raw",
        "source_policy":"printed_source_only","classes":classes,"records":records,
        "statistics":{
            "classes":len(classes),"source_entries":len(records),
            "groups":sum(x["record_type"]=="group" for x in records),
            "main_accounts":sum(x.get("source_level")=="main_account" for x in records),
            "sub_accounts":sum(x.get("source_level")=="sub_account" for x in records),
            "unique_codes":len({x["code_source"] for x in records}),
        }
    }

def build_structure(v0):
    classes=v0["classes"]; records=v0["records"]; nodes=[]; by_id={}; code_to_id={}
    for c in classes: code_to_id[("class",c["code_source"])]=f"class:ohada-syscohada:2017:{c['code_source']}"
    for r in records:
        code=r["code_source"]
        if code in code_to_id: raise ValueError(f"duplicate code {code}")
        code_to_id[code]=f"account:ohada-syscohada:2017:{code}"
    for c in classes:
        nid=code_to_id[("class",c["code_source"])]
        n={"node_id":nid,"node_type":"class","standard_id":"ohada-syscohada","edition":"2017",
           "source_record_id":c["record_id"],"ref_code":c["code_source"],"label_source":c["label_source"],
           "account_class":int(c["code_source"]),"parent_node_id":None,"children_node_ids":[],
           "depth":0,"path_node_ids":[nid],"path_codes":[c["code_source"]],"is_leaf":False,
           "attributes":{"source_rows":c["source_rows"]},
           "provenance":{"type":"source","method":"syscohada_class_heading","source_refs":[c["source"]],"confidence":1.0,"review_status":"official_source"}}
        nodes.append(n);by_id[nid]=n
    seen=[]
    for r in records:
        code=r["code_source"]; cls=str(r["class_number_source"])
        if r["record_type"]=="group":
            parent=code_to_id[("class",cls)]
        else:
            candidates=[c for c in seen if code.startswith(c) and c!=code and c[0]==cls]
            parent_code=max(candidates,key=len) if candidates else code[:2]
            parent=code_to_id[parent_code]
        nid=code_to_id[code]
        n={"node_id":nid,"node_type":r["record_type"],"standard_id":"ohada-syscohada","edition":"2017",
           "source_record_id":r["record_id"],"ref_code":code,"label_source":r["label_source"],
           "account_class":r["class_number_source"],"parent_node_id":parent,"children_node_ids":[],
           "depth":0,"path_node_ids":[],"path_codes":[],"is_leaf":True,
           "attributes":{"source_level":r.get("source_level"),"source_marker":r["source_marker"]},
           "provenance":{"type":"derived","method":"source_group_plus_longest_strict_prefix_v1","source_refs":[r["source"]],"confidence":1.0,"review_status":"auto_verified"}}
        nodes.append(n);by_id[nid]=n;seen.append(code)
    for n in nodes:
        if n["parent_node_id"]:by_id[n["parent_node_id"]]["children_node_ids"].append(n["node_id"])
    def path(n):
        ids=[n["node_id"]];codes=[n["ref_code"]];cur=n;guard={n["node_id"]}
        while cur["parent_node_id"]:
            p=by_id[cur["parent_node_id"]]
            if p["node_id"] in guard:raise ValueError("cycle")
            guard.add(p["node_id"]);ids.append(p["node_id"]);codes.append(p["ref_code"]);cur=p
        return list(reversed(ids)),list(reversed(codes))
    for n in nodes:
        ids,codes=path(n);n["path_node_ids"]=ids;n["path_codes"]=codes;n["depth"]=len(ids)-1;n["is_leaf"]=not n["children_node_ids"]
    depths=Counter(n["depth"] for n in nodes if n["node_type"]!="class")
    return {"standard_id":"ohada-syscohada","edition":"2017","dataset_layer":"v1_structure","nodes":nodes,
            "statistics":{"class_nodes":9,"account_nodes":1403,"group_nodes":85,
                          "leaf_nodes":sum(n["node_type"]!="class" and n["is_leaf"] for n in nodes),
                          "graph_nodes":len(nodes),"unique_atomic_codes":1403,
                          "depth_distribution":{str(k):v for k,v in sorted(depths.items()) }}}
