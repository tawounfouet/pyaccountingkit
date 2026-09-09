from pathlib import Path
import json, typer
from .registry import StandardRegistry
from .config import load_manifest
from .io import sha256_file, dump_json
from .framework.extraction.markdown_account_list import MarkdownAccountListExtractor
from .framework.structure.prefix_graph import build_prefix_graph
from .framework.validation.graph import validate_graph
app=typer.Typer(help='Regulatory Accounting Data Framework')
def parse_ref(ref):
    if ':' not in ref: raise typer.BadParameter('Expected STANDARD_ID:EDITION')
    return ref.rsplit(':',1)
@app.command('standard-list')
def standard_list(standards_dir: str='standards'):
    for m in StandardRegistry(standards_dir).list():
        caps=[k for k,v in m.capabilities.model_dump().items() if v]
        typer.echo(f"{m.standard_id}:{m.edition} | {m.standard_name} | {', '.join(caps)}")
@app.command('manifest-validate')
def manifest_validate(manifest_path: str):
    m=load_manifest(manifest_path); typer.echo(f'OK {m.standard_id}:{m.edition}')
@app.command('source-verify')
def source_verify(ref: str, project_root: str='.'):
    sid,ed=parse_ref(ref); m=StandardRegistry(Path(project_root)/'standards').get(sid,ed); base=Path(project_root)/'standards'/sid/ed; failed=False
    for a in m.source_documents:
        p=base/a.relative_path
        if not p.exists(): typer.echo(f'MISSING {a.document_id}: {p}'); failed=True; continue
        digest=sha256_file(p); status='OK' if not a.sha256 or digest==a.sha256 else 'HASH_MISMATCH'; typer.echo(f'{status} {a.document_id} {digest}'); failed |= status!='OK'
    if failed: raise typer.Exit(code=2)
@app.command('build-raw-from-markdown')
def build_raw_from_markdown(ref: str, markdown: str, document_id: str, output: str):
    sid,ed=parse_ref(ref); rows=[r.model_dump(mode='json') for r in MarkdownAccountListExtractor().extract(Path(markdown),document_id)]; dump_json(output,{'standard_id':sid,'edition':ed,'records':rows}); typer.echo(f'Wrote {len(rows)} raw records -> {output}')
@app.command('build-structure')
def build_structure(ref: str, raw_json: str, output: str):
    from .models import RawAccountEntry
    sid,ed=parse_ref(ref); data=json.loads(Path(raw_json).read_text(encoding='utf-8')); raw=[RawAccountEntry.model_validate(x) for x in data['records']]; nodes=build_prefix_graph(raw,sid,ed); payload={'standard_id':sid,'edition':ed,'nodes':[n.model_dump(mode='json') for n in nodes]}; errors=validate_graph(payload['nodes'])
    if errors: typer.echo('\n'.join(errors)); raise typer.Exit(code=2)
    dump_json(output,payload); typer.echo(f'Wrote {len(nodes)} structured nodes -> {output}')
@app.command('graph-validate')
def graph_validate(structured_json: str):
    data=json.loads(Path(structured_json).read_text(encoding='utf-8')); errors=validate_graph(data['nodes'])
    if errors: typer.echo('\n'.join(errors)); raise typer.Exit(code=2)
    typer.echo('OK graph')

if __name__ == '__main__':
    app()


@app.command("pcemf-legacy-validate")
def pcemf_legacy_validate(
    legacy_root: str,
    strict: bool = False,
    output: str | None = None,
):
    """Validate an AMIFOND regulatory-data legacy repository against documented V0→V6 invariants."""
    from .standards.pcemf.validator import validate_legacy_root
    from .io import dump_json
    result = validate_legacy_root(legacy_root, strict=strict)
    if output:
        dump_json(output, result)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
    if strict and result["status"] != "ok":
        raise typer.Exit(code=2)


@app.command("pcemf-migrate")
def pcemf_migrate(
    legacy_root: str,
    target_root: str = ".",
    strict: bool = False,
):
    """Migrate PCEMF/AMIFOND canonical artifacts byte-for-byte into the generalized framework."""
    from .standards.pcemf.migration import migrate_legacy_repository
    result = migrate_legacy_repository(legacy_root, target_root, strict=strict)
    typer.echo(json.dumps({
        "status": result["status"],
        "artifacts_migrated": len(result["artifacts"]),
        "missing_required": result["missing_required"],
        "optional_missing": result["optional_missing"],
    }, ensure_ascii=False, indent=2))
    if result["missing_required"]:
        raise typer.Exit(code=2)


@app.command("pcg-build")
def pcg_build(project_root: str = "."):
    """Build the PCG 2026 V0/V1/V2/V3 + article/doctrine/RAG datasets from the bundled ANC corpus."""
    from .standards.pcg.build import build_all
    result = build_all(project_root)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("pcg-validate")
def pcg_validate(project_root: str = "."):
    """Validate PCG 2026 canonical datasets and source-first safety invariants."""
    from .io import load_json
    from .standards.pcg.validation import validate_v0, validate_v1, validate_v2, validate_reporting
    root = Path(project_root)
    checks = {
        "v0": validate_v0(load_json(root/"datasets/raw/pcg_2026_v0_raw.json")),
        "v1": validate_v1(load_json(root/"datasets/structured/pcg_2026_v1_structure.json")),
        "v2": validate_v2(load_json(root/"datasets/annotated/pcg_2026_v2_account_functioning.json")),
        "reporting": validate_reporting(load_json(root/"datasets/reporting/pcg_2026_v3_reporting.json")),
    }
    typer.echo(json.dumps(checks, ensure_ascii=False, indent=2))
    if any(checks.values()):
        raise typer.Exit(code=2)


@app.command("pcg-rag-search")
def pcg_rag_search(query: str, project_root: str = ".", top_k: int = 5):
    """Search the deterministic lexical RAG index of the 2026 ANC PCG Recueil."""
    from .io import load_json
    from .framework.rag.bm25 import search
    index = load_json(Path(project_root)/"rag/indexes/pcg-recueil-2026-v1.json")
    typer.echo(json.dumps(search(index, query, top_k=top_k), ensure_ascii=False, indent=2))


@app.command("nonprofit-build")
def nonprofit_build(project_root: str = "."):
    """Build FR Non-Profit 2026 as a regulatory overlay of FR-PCG 2026."""
    from .standards.nonprofit.build import build_all
    result = build_all(project_root)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("nonprofit-validate")
def nonprofit_validate(project_root: str = "."):
    """Validate source priority, overlay inheritance and practitioner separation."""
    from .config import load_manifest
    from .io import load_json
    from .standards.nonprofit.validation import (
        validate_source_roles, validate_overlay, validate_functioning,
        validate_practitioner_comparison, validate_reporting,
    )
    root = Path(project_root)
    manifest = load_manifest(root / "standards/fr-nonprofit/2026/manifest.yaml")
    overlay = load_json(root / "datasets/structured/nonprofit_2026_v1_account_overlay.json")
    effective = load_json(root / "datasets/structured/nonprofit_2026_v1_effective_plan.json")
    v2 = load_json(root / "datasets/annotated/nonprofit_2026_v2_account_functioning.json")
    comparison = load_json(root / "validation/review/nonprofit_2026_orcom_comparison.json")
    reporting = load_json(root / "datasets/reporting/nonprofit_2026_v3_reporting.json")
    checks = {
        "source_roles": validate_source_roles(manifest),
        "overlay": validate_overlay(overlay, effective),
        "functioning": validate_functioning(v2),
        "practitioner_comparison": validate_practitioner_comparison(comparison),
        "reporting": validate_reporting(reporting),
    }
    typer.echo(json.dumps(checks, ensure_ascii=False, indent=2))
    if any(checks.values()):
        raise typer.Exit(code=2)


@app.command("nonprofit-rag-search")
def nonprofit_rag_search(query: str, project_root: str = ".", top_k: int = 5):
    """Search the deterministic lexical index of the 2026 ANC Non-Profit Recueil."""
    from .io import load_json
    from .framework.rag.bm25 import search
    index = load_json(Path(project_root) / "rag/indexes/nonprofit-recueil-2026-v1.json")
    typer.echo(json.dumps(search(index, query, top_k=top_k), ensure_ascii=False, indent=2))


@app.command("family-list")
def family_list(families_dir: str="families"):
    from .families.registry import FamilyRegistry
    for f in FamilyRegistry(families_dir).list():
        typer.echo(f"{f.family_id} | {f.family_name} | {len(f.member_standard_refs)} members")

@app.command("family-show")
def family_show(family_id: str, families_dir: str="families"):
    from .families.registry import FamilyRegistry
    f=FamilyRegistry(families_dir).get(family_id)
    typer.echo(json.dumps(f.model_dump(mode="json"),ensure_ascii=False,indent=2))

@app.command("ohada-foundation-build")
def ohada_foundation_build(project_root: str="."):
    from .standards.ohada.foundation import build_foundation
    r=build_foundation(project_root); typer.echo(json.dumps(r,ensure_ascii=False,indent=2))
    if r["status"]!="ok": raise typer.Exit(code=2)

@app.command("ohada-foundation-validate")
def ohada_foundation_validate(project_root: str="."):
    from .standards.ohada.foundation import build_foundation
    r=build_foundation(project_root); typer.echo(json.dumps(r["validation"],ensure_ascii=False,indent=2))
    if r["status"]!="ok": raise typer.Exit(code=2)

@app.command("relation-list")
def relation_list(project_root: str="."):
    data=json.loads((Path(project_root)/"datasets/relations/ohada_accounting_standard_relations.json").read_text(encoding="utf-8"))
    for r in data["relations"]:
        typer.echo(f"{r['relation_type']} | {r['subject_ref']} -> {r['target_ref']} | review={r['human_review_required']}")

@app.command("concept-list")
def concept_list(project_root: str="."):
    data=json.loads((Path(project_root)/"datasets/concepts/accounting_core_concepts_v0.json").read_text(encoding="utf-8"))
    for c in data["concepts"]:
        typer.echo(f"{c['concept_id']} | {c['label']} | {c['concept_type']}")

@app.command("syscohada-build")
def syscohada_build(project_root: str="."):
    from .standards.syscohada.build import build_all
    typer.echo(json.dumps(build_all(project_root),ensure_ascii=False,indent=2))

@app.command("syscohada-validate")
def syscohada_validate(project_root: str="."):
    from .io import load_json
    from .standards.syscohada.validation import validate_v0,validate_v1,validate_guide,validate_v2,validate_v3
    r=Path(project_root)
    v0=load_json(r/"datasets/raw/syscohada_2017_v0_raw.json");v1=load_json(r/"datasets/structured/syscohada_2017_v1_structure.json")
    toc=load_json(r/"datasets/annotated/syscohada_2017_guide_registry.json");apps=load_json(r/"datasets/annotated/syscohada_2017_applications.json")
    v2=load_json(r/"datasets/annotated/syscohada_2017_v2_accounting_knowledge.json");v3=load_json(r/"datasets/reporting/syscohada_2017_v3_reporting.json")
    checks={"v0":validate_v0(v0),"v1":validate_v1(v1),"guide":validate_guide(toc,apps),"v2":validate_v2(v2),"v3":validate_v3(v3)}
    typer.echo(json.dumps(checks,ensure_ascii=False,indent=2))
    if any(checks.values()):raise typer.Exit(code=2)

@app.command("syscohada-rag-search")
def syscohada_rag_search(query: str, project_root: str=".", top_k: int=5):
    from .io import load_json
    from .framework.rag.bm25 import search
    typer.echo(json.dumps(search(load_json(Path(project_root)/"rag/indexes/syscohada-guide-2017-v2.json"),query,top_k),ensure_ascii=False,indent=2))

@app.command("syscohada-application-show")
def syscohada_application_show(number: int, project_root: str="."):
    from .io import load_json
    d=load_json(Path(project_root)/"datasets/annotated/syscohada_2017_applications.json")
    a=next((x for x in d["applications"] if x["application_number"]==number),None)
    if a is None:raise typer.BadParameter("Unknown application")
    typer.echo(json.dumps(a,ensure_ascii=False,indent=2))


@app.command("ebnl-build")
def ebnl_build(project_root: str="."):
    """Build OHADA EBNL 2023 Complete: V0/V1 + legal/conceptual + V2 + specific ops + V3/disclosures + source router."""
    from .standards.ebnl.build import build_all
    typer.echo(json.dumps(build_all(project_root),ensure_ascii=False,indent=2))

@app.command("ebnl-validate")
def ebnl_validate(project_root: str="."):
    """Validate the complete EBNL 2023 source-first release and its non-invention safeguards."""
    from .io import load_json
    from .standards.ebnl.validation import (
        validate_v0,validate_v1,validate_duplicate_4555,validate_comparison,
        validate_complete_source,validate_legal_registry,validate_conceptual_framework,
        validate_v2_complete,validate_specific_operations,validate_reporting_complete,
        validate_disclosures_complete,validate_capability_status,
    )
    r=Path(project_root)
    v0=load_json(r/"datasets/raw/ebnl_2023_v0_reviewed_structure.json")
    v1=load_json(r/"datasets/structured/ebnl_2023_v1_structure.json")
    cmp=load_json(r/"datasets/crosswalk/ebnl_2023_vs_syscohada_2017_structural_delta.json")
    checks={
        "v0":validate_v0(v0),"v1":validate_v1(v1),"duplicate_4555":validate_duplicate_4555(v1),"comparison":validate_comparison(cmp),
        "source":validate_complete_source(load_json(r/"datasets/annotated/ebnl_2023_source_page_registry.json")),
        "legal":validate_legal_registry(load_json(r/"datasets/annotated/ebnl_2023_legal_act_registry.json")),
        "conceptual":validate_conceptual_framework(load_json(r/"datasets/annotated/ebnl_2023_conceptual_framework.json")),
        "v2":validate_v2_complete(load_json(r/"datasets/annotated/ebnl_2023_v2_account_functioning.json")),
        "specific_operations":validate_specific_operations(load_json(r/"datasets/annotated/ebnl_2023_specific_operations.json")),
        "v3":validate_reporting_complete(load_json(r/"datasets/reporting/ebnl_2023_v3_reporting.json")),
        "disclosures":validate_disclosures_complete(load_json(r/"datasets/annotated/ebnl_2023_disclosures_registry.json")),
        "capabilities":validate_capability_status(load_json(r/"validation/review/ebnl_2023_capability_status.json")),
    }
    typer.echo(json.dumps(checks,ensure_ascii=False,indent=2))
    if any(checks.values()):raise typer.Exit(code=2)

@app.command("ebnl-account-show")
def ebnl_account_show(code: str, project_root: str="."):
    """Show all EBNL source occurrences for one code; duplicate source codes are preserved."""
    from .io import load_json
    d=load_json(Path(project_root)/"datasets/structured/ebnl_2023_v1_structure.json")
    rows=[n for n in d["nodes"] if n["node_type"]=="account" and n["ref_code"]==code]
    typer.echo(json.dumps(rows,ensure_ascii=False,indent=2))

@app.command("ebnl-rag-search")
def ebnl_rag_search(query: str, project_root: str=".", top_k: int=5):
    """Search the complete 438-page EBNL source router. Returned pages must be checked in the official visual PDF for authoritative wording."""
    from .io import load_json
    from .framework.rag.bm25 import search
    idx=load_json(Path(project_root)/"rag/indexes/ebnl-sycebnl-2023-source-router-v2.json")
    typer.echo(json.dumps(search(idx,query,top_k),ensure_ascii=False,indent=2))

@app.command("ebnl-reporting-profiles")
def ebnl_reporting_profiles(project_root: str="."):
    """List the three EBNL reporting profiles and their official model pages."""
    from .io import load_json
    d=load_json(Path(project_root)/"datasets/reporting/ebnl_2023_v3_reporting.json")
    typer.echo(json.dumps(d["profiles"],ensure_ascii=False,indent=2))

@app.command("ebnl-source-page")
def ebnl_source_page(page: int, project_root: str="."):
    """Show routing metadata for one official SYCEBNL PDF page."""
    if page < 1 or page > 438:
        raise typer.BadParameter("page must be between 1 and 438")
    from .io import load_json
    d=load_json(Path(project_root)/"datasets/annotated/ebnl_2023_source_page_registry.json")
    typer.echo(json.dumps(d["pages"][page-1],ensure_ascii=False,indent=2))
