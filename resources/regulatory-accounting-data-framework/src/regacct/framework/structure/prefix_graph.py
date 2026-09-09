import re
from collections import defaultdict
from ...models import StructuredAccount, Provenance, ProvenanceType, ReviewStatus

def _atomic_codes(code_source: str):
    if "/" in code_source:
        return [re.sub(r"\D", "", p) for p in code_source.split("/") if re.sub(r"\D", "", p)]
    if "à" in code_source or "-" in code_source:
        return []
    code = re.sub(r"\D", "", code_source)
    return [code] if code else []

def build_prefix_graph(raw_entries, standard_id: str, edition: str):
    projections=[]
    for e in raw_entries:
        atoms=_atomic_codes(e.code_source)
        for i, code in enumerate(atoms):
            projections.append((e, code, len(atoms)>1, i))
    seen=defaultdict(list); temp=[]
    for e, code, grouped, i in projections:
        cls=e.class_number_source or int(code[0])
        candidates=[x for x in seen[cls] if code.startswith(x[0]) and code!=x[0]]
        parent_code,parent_id=max(candidates,key=lambda x:len(x[0])) if candidates else (None,None)
        node_id=f"account:{standard_id}:{edition}:{e.record_id}:{i}"
        temp.append(dict(entry=e,ref_code=code,grouped=grouped,node_id=node_id,account_class=cls,parent_node_id=parent_id,parent_code=parent_code))
        seen[cls].append((code,node_id))
    by_id={t['node_id']:t for t in temp}; children=defaultdict(list)
    for t in temp:
        if t['parent_node_id']: children[t['parent_node_id']].append(t['node_id'])
    def path_for(nid):
        chain=[nid]; cur=by_id[nid]
        while cur['parent_node_id']:
            chain.append(cur['parent_node_id']); cur=by_id[cur['parent_node_id']]
        return list(reversed(chain))
    out=[]
    for t in temp:
        pids=path_for(t['node_id']); pcodes=[by_id[x]['ref_code'] for x in pids]
        out.append(StructuredAccount(
            node_id=t['node_id'], standard_id=standard_id, edition=edition,
            source_record_id=t['entry'].record_id, ref_code=t['ref_code'], label_source=t['entry'].label_source,
            account_class=t['account_class'], parent_node_id=t['parent_node_id'], children_node_ids=children[t['node_id']],
            depth=len(pids)-1, path_node_ids=pids, path_codes=pcodes, is_leaf=not children[t['node_id']],
            is_grouped_source=t['grouped'], source_code=t['entry'].code_source,
            provenance=Provenance(type=ProvenanceType.DERIVED, method="longest_strict_prefix_preceding_source_v1",
                source_refs=[t['entry'].source], confidence=1.0, review_status=ReviewStatus.AUTO_VERIFIED)
        ))
    return out
