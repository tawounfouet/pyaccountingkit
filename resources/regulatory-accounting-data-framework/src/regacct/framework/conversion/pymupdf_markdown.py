from pathlib import Path
from .base import DocumentConverter
class PyMuPDFTextToMarkdown(DocumentConverter):
    def convert(self, source: Path, target: Path) -> Path:
        try:
            import fitz
        except ImportError as exc:
            raise RuntimeError("Install PyMuPDF to use this converter") from exc
        doc = fitz.open(source)
        parts = []
        for i, page in enumerate(doc, start=1):
            parts.append(f"<!-- Page PDF {i} -->\n{page.get_text('text').rstrip()}\n")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(parts), encoding="utf-8")
        return target
