"""
parsers.py
Handles text extraction from PDF, DOCX, and TXT files.
"""

from PyPDF2 import PdfReader
import docx


class ParsingError(Exception):
    pass


def extract_text_from_pdf(file_stream):
    try:
        reader = PdfReader(file_stream)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts).strip()
    except Exception as e:
        raise ParsingError(f"Could not read this PDF file: {e}")


def extract_text_from_docx(file_stream):
    try:
        document = docx.Document(file_stream)
        text_parts = [para.text for para in document.paragraphs if para.text.strip()]
        return "\n".join(text_parts).strip()
    except Exception as e:
        raise ParsingError(f"Could not read this DOCX file: {e}")


def extract_text_from_txt(file_stream):
    try:
        raw_bytes = file_stream.read()
        text = raw_bytes.decode("utf-8", errors="ignore")
        return text.strip()
    except Exception as e:
        raise ParsingError(f"Could not read this TXT file: {e}")


def extract_text(filename, file_stream):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension == "pdf":
        text = extract_text_from_pdf(file_stream)
    elif extension == "docx":
        text = extract_text_from_docx(file_stream)
    elif extension == "txt":
        text = extract_text_from_txt(file_stream)
    else:
        raise ParsingError(f"Unsupported file type: .{extension}")

    if not text or len(text.strip()) < 10:
        raise ParsingError("This file appears to be empty or unreadable.")

    return text