"""Extract text from uploaded resume/JD files (PDF, DOCX, or plain text)."""
import io
import re
from typing import Optional

import PyPDF2
from fastapi import HTTPException, UploadFile

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}


def _normalize_extracted_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r", "\n")
    text = re.sub(r"\u00a0", " ", text)
    text = re.sub(r"[\t\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    return text.strip()


def _get_extension(filename: str) -> str:
    if "." in filename:
        return "." + filename.rsplit(".", 1)[1].lower()
    return ""


def _extract_docx_text(content: bytes) -> str:
    """Extract text from DOCX file using python-docx."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(content))
        parts = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
        return _normalize_extracted_text("\n".join(parts) if parts else "")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read DOCX: {str(e)}")


def _extract_pdf_text(content: bytes) -> str:
    """Extract text from PDF file using PyPDF2."""
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        parts = [page.extract_text() for page in reader.pages if page.extract_text()]
        return _normalize_extracted_text("\n".join(parts) if parts else "")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read PDF: {str(e)}")


def extract_text_from_file(file: UploadFile) -> str:
    """
    Extract plaintext from various file formats.
    Supports: PDF, DOCX, TXT
    """
    ext = _get_extension(file.filename or "")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    content = file.file.read()
    file.file.seek(0)

    if ext == ".pdf":
        return _extract_pdf_text(content)
    elif ext == ".docx":
        return _extract_docx_text(content)
    else:  # .txt
        return _normalize_extracted_text(content.decode("utf-8", errors="replace"))
