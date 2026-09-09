def validate_graph(nodes):
    errors=[]; ids=[n['node_id'] for n in nodes]
    if len(ids)!=len(set(ids)): errors.append('duplicate_node_id')
    by={n['node_id']:n for n in nodes}
    for n in nodes:
        p=n.get('parent_node_id')
        if p and p not in by: errors.append(f"missing_parent:{n['node_id']}:{p}")
        if p==n['node_id']: errors.append(f"self_reference:{n['node_id']}")
        for c in n.get('children_node_ids',[]):
            if c not in by: errors.append(f"missing_child:{n['node_id']}:{c}")
            elif by[c].get('parent_node_id')!=n['node_id']: errors.append(f"asymmetric_link:{n['node_id']}:{c}")
    state={}
    def visit(nid):
        if state.get(nid)==1: errors.append(f"cycle:{nid}"); return
        if state.get(nid)==2: return
        state[nid]=1
        for c in by[nid].get('children_node_ids',[]):
            if c in by: visit(c)
        state[nid]=2
    for nid in by: visit(nid)
    return sorted(set(errors))
