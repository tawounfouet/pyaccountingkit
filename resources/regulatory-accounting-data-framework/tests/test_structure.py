from pathlib import Path
from regacct.framework.extraction.markdown_account_list import MarkdownAccountListExtractor
from regacct.framework.structure.prefix_graph import build_prefix_graph
from regacct.framework.validation.graph import validate_graph

def nodes():
    raw=list(MarkdownAccountListExtractor().extract(Path('examples/sample_pcg_markdown.md'),'sample-pcg'))
    return build_prefix_graph(raw,'fr-pcg','2026')

def test_no_padding_collision():
    ns=nodes(); assert validate_graph([n.model_dump(mode='json') for n in ns])==[]
    ids={n.ref_code:n.node_id for n in ns}
    assert ids['11']!=ids['110']

def test_parent_longest_prefix():
    ns=nodes(); by={n.node_id:n for n in ns}; n=next(x for x in ns if x.ref_code=='10131')
    assert by[n.parent_node_id].ref_code=='1013'
