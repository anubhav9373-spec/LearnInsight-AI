from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import os

from parsers import extract_text, ParsingError
from ai_service import generate_all_content, AIServiceError
from database import init_db, save_document, get_all_documents, get_document_by_id

load_dotenv()

app = Flask(__name__)
CORS(app)

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB

init_db()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[-1].lower() in ALLOWED_EXTENSIONS


def get_extension(filename):
    return filename.rsplit(".", 1)[-1].lower()


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})


@app.route("/api/process", methods=["POST"])
def process_document():
    if "file" not in request.files:
        return jsonify({"error": "No file was provided."}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file was selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type. Please upload a PDF, DOCX, or TXT file."}), 400

    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE_BYTES:
        return jsonify({"error": "File is too large. Maximum size is 10MB."}), 413

    if file_size == 0:
        return jsonify({"error": "This file appears to be empty or unreadable."}), 422

    try:
        extracted_text = extract_text(file.filename, file)
    except ParsingError as e:
        return jsonify({"error": str(e)}), 422
    except Exception:
        return jsonify({"error": "Something went wrong processing your document."}), 500

    try:
        ai_result = generate_all_content(extracted_text)
    except AIServiceError as e:
        message = str(e)
        if "429" in message or "RESOURCE_EXHAUSTED" in message or "quota" in message.lower():
            return jsonify({"error": "Daily AI generation limit reached on the free tier. Please try again tomorrow."}), 429
        return jsonify({"error": "AI generation is temporarily unavailable. Please try again in a moment."}), 502

    doc_id = save_document(
        filename=file.filename,
        file_type=get_extension(file.filename),
        extracted_text=extracted_text,
        summary=ai_result["summary"],
        explanation=ai_result["explanation"],
        quiz=ai_result["quiz"],
        flashcards=ai_result["flashcards"],
        notes=ai_result["notes"]
    )

    saved_doc = get_document_by_id(doc_id)
    return jsonify(saved_doc)


@app.route("/api/history", methods=["GET"])
def history():
    try:
        documents = get_all_documents()
    except Exception:
        return jsonify({"error": "Could not load document history."}), 500

    return jsonify({"documents": documents})


@app.route("/api/document/<int:doc_id>", methods=["GET"])
def get_document(doc_id):
    try:
        document = get_document_by_id(doc_id)
    except Exception:
        return jsonify({"error": "Could not load this document."}), 500

    if document is None:
        return jsonify({"error": "Document not found."}), 404

    return jsonify(document)


if __name__ == "__main__":
    app.run(debug=True, port=5000)