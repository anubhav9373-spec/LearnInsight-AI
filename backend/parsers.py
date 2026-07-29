"""
parsers.py
Handles text extraction from PDF, DOCX, and TXT files.
"""

from PyPDF2 import PdfReader
import docx


class ParsingError(Exception):
    pass


def _is_readable_text(text, min_printable_ratio=0.85):
    """
    Checks whether extracted text looks like genuine readable content rather
    than binary garbage (e.g., an image file renamed with a .txt extension).
    Binary data, when force-decoded as text, produces a high proportion of
    non-printable/control characters — real documents don't.
    """
    if not text:
        return False

    printable_count = sum(1 for ch in text if ch.isprintable() or ch.isspace())
    ratio = printable_count / len(text)
    return ratio >= min_printable_ratio


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

        # Binary files (images, etc.) commonly contain null bytes, which
        # genuine text files never do. This catches most disguised binary
        # files immediately, before even attempting to decode them.
        if b"\x00" in raw_bytes[:8192]:
            raise ParsingError(
                "This file does not appear to be a valid text document. "
                "It may be an image or another non-text file renamed to .txt."
            )

        text = raw_bytes.decode("utf-8", errors="ignore")

        # Catches binary content that decoded "successfully" but produced
        # mostly unreadable/garbage characters (e.g., a renamed image).
        if not _is_readable_text(text):
            raise ParsingError(
                "This file does not appear to be a valid text document. "
                "It may be an image or another non-text file renamed to .txt."
            )

        return text.strip()
    except ParsingError:
        raise
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
        raise ParsingError(
            "This file appears to be too short to generate meaningful study materials. "
            "Please upload a document with more content."
        )

    return text