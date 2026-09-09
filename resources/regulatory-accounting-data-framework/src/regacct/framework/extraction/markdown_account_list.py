from pathlib import Path
import re
from .base import AccountExtractor
from ...models import RawAccountEntry, SourceReference
PAGE_RE = re.compile(r"<!--\s*Page PDF\s+(\d+)\s*-->")
ACCOUNT_RE = re.compile(r"^\s*([0-9]{1,6}(?:\s*(?:/|à|-)\s*[0-9]{1,6})*)\s+(.+?)\s*$")
class MarkdownAccountListExtractor(AccountExtractor):
    def __init__(self, section: str = "PLAN DE COMPTES"):
        self.section = section
    def extract(self, source: Path, document_id: str):
        page = None; order = 0
        for line in source.read_text(encoding="utf-8").splitlines():
            mp = PAGE_RE.search(line)
            if mp:
                page = int(mp.group(1)); continue
            m = ACCOUNT_RE.match(line)
            if not m: continue
            code, label = m.groups(); order += 1
            yield RawAccountEntry(
                record_id=f"{document_id}:p{page or 0:03d}:e{order:05d}", source_order=order,
                code_source=code, code_normalized=re.sub(r"\s+", "", code), label_source=label.strip(),
                class_number_source=int(re.sub(r"\D", "", code)[0]) if re.sub(r"\D", "", code) else None,
                source=SourceReference(document_id=document_id, page_pdf=page, section=self.section),
                source_rows=[line]
            )
