"""
PDF parser for digital bills, statements, and policy documents using pypdf.
Adheres to strict ₹0 baseline: gracefully detects scanned/image PDFs without paid OCR.
"""
import io
from typing import Dict, Any
from pypdf import PdfReader
from app.parsers.text_parser import hash_content


class ScannedPdfError(Exception):
    """Raised when PDF lacks an extractable digital text layer."""
    pass


def parse_pdf_input(pdf_bytes: bytes, default_title: str = "Uploaded Document") -> Dict[str, Any]:
    """
    Extract text content from digital PDF bytes.
    Detects scanned PDFs with insufficient text layer.
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception as e:
        raise ValueError(f"Failed to read PDF file format: {str(e)}")

    if len(reader.pages) == 0:
        raise ValueError("PDF file contains no pages.")

    extracted_pages = []
    for idx, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        extracted_pages.append(page_text.strip())

    full_text = "\n\n".join(extracted_pages).strip()

    # Integrity Check: Check if PDF is a scanned image with no readable text layer
    if len(full_text) < 25:
        raise ScannedPdfError(
            "No readable text layer; please paste text or provide a digital PDF"
        )

    # Infer title from PDF metadata or first prominent line
    title = default_title
    if reader.metadata and reader.metadata.title:
        title = str(reader.metadata.title).strip()
    else:
        first_lines = [l.strip() for l in full_text.splitlines() if l.strip()]
        if first_lines and len(first_lines[0]) < 80:
            title = first_lines[0]

    return {
        "title": title,
        "clean_text": full_text,
        "raw_text": full_text,
        "page_count": len(reader.pages),
        "file_hash": hash_content(full_text),
        "source_type": "pdf"
    }
