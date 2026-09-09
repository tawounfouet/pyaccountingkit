from pathlib import Path
import re, unicodedata
from collections import Counter, defaultdict

PAGE_RE=re.compile(r"<!--\s*Page PDF\s+(\d+)\s*-->")
PART_RE=re.compile(r"^#\s+(PREMIERE|DEUXIEME|TROISIEME|QUATRIEME)\s+PARTIE\s*:\s*(.*)",re.I)
CH_RE=re.compile(r"^###\s+CHAPITRE\s+(\d+)\s*:\s*(.*)",re.I)
SEC_RE=re.compile(r"^####\s+Section\s+(\d+)\s*:\s*(.*)",re.I)
APP_TOC_RE=re.compile(r"^#####\s+Application\s+(\d+)\s*:\s*(.*)",re.I)
# Body has mostly "##### APPLICATION", plus source anomaly "APPLICATIONü 113".
APP_BODY_RE=re.compile(r"^(?:#####\s+)?APPLICATION\S*\s+(\d+)\s+(.+?)\s*$")

PART_NAMES={"PREMIERE":"OPERATIONS COURANTES","DEUXIEME":"OPERATIONS ET PROBLEMES SPECIFIQUES",
            "TROISIEME":"PRESENTATION DES ETATS FINANCIERS","QUATRIEME":"COMPTES CONSOLIDES ET COMBINES"}

def _title_page(s):
    if m:=re.search(r"\.{2,}\s*(\d+)\s*$",s):return s[:m.start()].strip(),int(m.group(1))
    if m:=re.search(r"\s+(\d{1,3})\s*$",s):
        if int(m.group(1))<=437:return s[:m.start()].strip(),int(m.group(1))
    return s.strip(),None

def _norm(s):
    s=unicodedata.normalize("NFKD",s or "")
    s="".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s)).strip()

def parse_toc(path):
    lines=Path(path).read_text(encoding="utf-8").splitlines()
    body_start=next(i for i,l in enumerate(lines) if i>500 and l.startswith("# PREMIERE PARTIE"))
    toc=lines[:body_start];parts=[];chapters=[];sections=[];apps=[];part=chap=sec=None
    for i,line in enumerate(toc):
        if m:=PART_RE.match(line):
            part=m.group(1).upper();chap=sec=None
            parts.append({"part_id":f"syscohada-guide:part:{part.lower()}","part_key":part,"title":PART_NAMES[part]});continue
        m=CH_RE.match(line) or SEC_RE.match(line) or APP_TOC_RE.match(line)
        if not m:continue
        kind="chapter" if CH_RE.match(line) else "section" if SEC_RE.match(line) else "application"
        num=int(m.group(1));title,page=_title_page(m.group(2).strip());j=i+1
        while page is None and j<len(toc):
            nxt=toc[j].strip()
            if not nxt:j+=1;continue
            if nxt.startswith("#") or nxt.startswith("<!--") or re.fullmatch(r"\d+",nxt):break
            t2,p2=_title_page(nxt);title=(title+" "+t2).strip();page=p2;j+=1
        if kind=="chapter":
            chap=num;sec=None;chapters.append({"chapter_id":f"syscohada-guide:{part.lower()}:chapter:{num}","part_key":part,"chapter_number":num,"title":title,"page_start_printed":page})
        elif kind=="section":
            sec=num;sections.append({"section_id":f"syscohada-guide:{part.lower()}:chapter:{chap}:section:{num}","part_key":part,"chapter_number":chap,"section_number":num,"title":title,"page_start_printed":page})
        else:
            apps.append({"application_id":f"syscohada2017:application:{num:03d}","application_number":num,"part_key":part,"chapter_number":chap,"section_number":sec,"title_toc":title,"page_start_printed_toc":page})
    return {"parts":parts,"chapters":chapters,"sections":sections,"applications":apps,
            "statistics":{"parts":len(parts),"chapters":len(chapters),"sections":len(sections),"applications":len(apps)}}

def _resolve(code,known):
    if code in known:return {"source_code":code,"resolved_code":code,"match_type":"exact"}
    p=[x for x in known if code.startswith(x)]
    if p:return {"source_code":code,"resolved_code":max(p,key=len),"match_type":"local_subdivision_prefix"}
    return None

def _mentions(body,known):
    out=[];seen=set()
    for line_idx,raw in enumerate(body):
        line=raw.strip();cands=[]
        for m in re.finditer(r"\bcompte(?:s)?\s+([0-9]{2,6})\b",line,re.I):cands.append((m.group(1),"explicit_compte_reference"))
        if m:=re.match(r"^([0-9]{2,6})\s+([A-Za-zÀ-ÖØ-öø-ÿ].+)$",line):cands.append((m.group(1),"line_start_account_code"))
        for m in re.finditer(r"\b(?:débit|credit|crédit|débité|crédité)\s+(?:du\s+|de\s+)?(?:compte\s+)?([0-9]{2,6})\b",line,re.I):
            cands.append((m.group(1),"debit_credit_reference"))
        for code,method in cands:
            r=_resolve(code,known)
            if not r:continue
            key=(line_idx,code,r["resolved_code"],method)
            if key in seen:continue
            seen.add(key);out.append({**r,"mention_method":method,"evidence_line":line})
    return out

def parse_applications(path,toc_registry,known_codes):
    all_lines=Path(path).read_text(encoding="utf-8").splitlines()
    body_start=next(i for i,l in enumerate(all_lines) if i>500 and l.startswith("# PREMIERE PARTIE"))
    lines=all_lines[body_start:];offset=body_start
    by_num={x["application_number"]:x for x in toc_registry["applications"]}
    by_title={_norm(x["title_toc"]):x for x in toc_registry["applications"]}
    page=None;current=None;apps=[];seen=set();heading_obs=[]

    def resolve_heading(source_num,title):
        clean_title=title.replace(": Suite des données","")
        n=_norm(clean_title)
        if current and source_num==current["application_number"] and "suite" in title.lower():return source_num,"continuation"
        if source_num in by_num and source_num not in seen:return source_num,"source_number"
        if n in by_title:return by_title[n]["application_number"],"toc_title_match"
        matches=[x for k,x in by_title.items() if n and (n in k or k in n)]
        if len(matches)==1:return matches[0]["application_number"],"toc_title_containment"
        return source_num,"unresolved_source_number"

    def close():
        nonlocal current
        if not current:return
        body=current.pop("_body");current["text_source"]="\n".join(body).strip();current["page_end_pdf"]=current.pop("_last_page")
        current["account_mentions"]=_mentions(body,known_codes);apps.append(current);seen.add(current["application_number"]);current=None

    for lineno,line in enumerate(lines,1):
        if m:=PAGE_RE.match(line):
            page=int(m.group(1))
            if current:current["_last_page"]=page
            continue
        if m:=APP_BODY_RE.match(line):
            sn=int(m.group(1));title=m.group(2).strip();cn,res=resolve_heading(sn,title)
            if res=="continuation" and current:
                current["_body"].append(line)
                current.setdefault("continuation_headings",[]).append({"source_number":sn,"source_title":title,"page_pdf":page,"source_line_md":lineno+offset})
                heading_obs.append({"type":"application_continuation_heading","source_number":sn,"canonical_number":cn,"source_title":title,"resolution":res,"page_pdf":page})
                continue
            close();toc=by_num.get(cn,{})
            if res!="source_number":
                heading_obs.append({"type":"application_heading_number_resolution","source_number":sn,"canonical_number":cn,"source_title":title,"resolution":res,"page_pdf":page})
            current={"application_id":f"syscohada2017:application:{cn:03d}","application_number":cn,"application_number_source":sn,"number_resolution":res,
                     "title_source":title,"title_toc":toc.get("title_toc"),"part_key":toc.get("part_key"),"chapter_number":toc.get("chapter_number"),
                     "section_number":toc.get("section_number"),"page_start_pdf":page,"page_start_printed_toc":toc.get("page_start_printed_toc"),
                     "_last_page":page,"source_line_md":lineno+offset,"_body":[]}
            continue
        if current:current["_body"].append(line)
    close();apps.sort(key=lambda x:x["application_number"])
    reverse=defaultdict(set);mention_count=local=0
    for a in apps:
        for m in a["account_mentions"]:
            mention_count+=1;local+=m["match_type"]=="local_subdivision_prefix";reverse[m["resolved_code"]].add(a["application_id"])
    return {"standard_id":"ohada-syscohada","edition":"2017","dataset_layer":"v2_applications","applications":apps,
            "account_to_applications":{k:sorted(v) for k,v in sorted(reverse.items())},
            "observations":{"heading_resolutions":heading_obs,
                            "printed_toc_page_vs_pdf_page":[{"application_id":a["application_id"],"printed_page_toc":a["page_start_printed_toc"],"pdf_page":a["page_start_pdf"]} for a in apps if a["page_start_printed_toc"]!=a["page_start_pdf"]]},
            "statistics":{"applications":len(apps),"account_mentions":mention_count,"resolved_accounts_reverse_indexed":len(reverse),
                          "local_subdivision_mentions":local,"heading_observations":len(heading_obs),
                          "part_distribution":dict(sorted(Counter(a["part_key"] for a in apps).items()))}}
