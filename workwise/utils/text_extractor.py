

import pdfplumber
import docx2txt

def extract_text_from_file(path: str) -> str:
    """
    Given a filesystem path to a PDF or DOCX or image,
    return the full extracted text.
    """
    lower = path.lower()
    if lower.endswith('.pdf'):
        # Extract page-by-page text from PDF
        text_pages = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_pages.append(page_text)
        return "\n".join(text_pages)

    # DOCX (and DOC) → plain text
    if lower.endswith('.docx') or lower.endswith('.doc'):
        return docx2txt.process(path)

    # (Optional) you could add OCR for JPG/PNG here, but for now:
    raise ValueError("Unsupported file type for text extraction")
