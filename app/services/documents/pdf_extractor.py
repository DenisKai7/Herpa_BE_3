import fitz

from app.core.config import Settings


def extract_pdf(data: bytes, settings: Settings) -> dict:
    document = fitz.open(stream=data, filetype="pdf")
    pages: list[dict] = []
    for index, page in enumerate(document):
        if index >= settings.max_pdf_pages:
            break
        text = page.get_text("text").strip()
        pages.append({"page": index + 1, "text": text})
    full = "\n\n".join(f"[Halaman {page['page']}]\n{page['text']}" for page in pages if page["text"])
    return {
        "text": full[: settings.max_document_characters],
        "pages": pages,
        "truncated": len(document) > settings.max_pdf_pages,
        "needs_vision": not bool(full.strip()),
    }
