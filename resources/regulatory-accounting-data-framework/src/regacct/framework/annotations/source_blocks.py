from ...models import AnnotationField, SourceReference
def make_source_field(text_source, *, document_id, page_pdf, heading, present_in_source=True, mode="normal"):
    refs=[]
    if present_in_source:
        refs=[SourceReference(document_id=document_id,page_pdf=page_pdf,section=heading,snippet=text_source[:400] if text_source else None)]
    return AnnotationField(present_in_source=present_in_source,mode=mode,text_source=text_source,fragments=refs)
