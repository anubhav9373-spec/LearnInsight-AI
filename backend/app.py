import logging
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os

from parsers import extract_text, ParsingError
from ai_service import generate_all_content, AIServiceError
from database import init_db, save_document, get_all_documents, get_document_by_id

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("learninsight")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

# --- Security hardening ---
# Reject oversized request bodies at the Flask level BEFORE they're fully 
# buffered into memory, not just after the fact in our own size check.
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB

# Restrict CORS to same-origin use only. Since the frontend is now served
# by this same Flask app, no external origin legitimately needs API access.
# This prevents other websites from calling our API and burning the
# free-tier daily Gemini quota.
CORS(app, resources={r"/api/*": {"origins": []}})

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB

init_db()

if not os.getenv("GEMINI_API_KEY"):
    logger.warning(
        "GEMINI_API_KEY is not set. AI generation will fail until this is configured "
        "in your .env file (local) or Render's Environment tab (production)."
    )


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[-1].lower() in ALLOWED_EXTENSIONS


def get_extension(filename):
    return filename.rsplit(".", 1)[-1].lower()


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    # Prevents noisy 404s in server logs for the browser's automatic favicon request.
    return "", 204


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
        # Log the real, detailed error server-side for debugging, but show
        # the user a clean, generic message — never leak raw library
        # exception internals to the client.
        logger.warning(f"Parsing failed for '{file.filename}': {e}")
        return jsonify({"error": "We couldn't read this file. Please check it isn't corrupted and try again."}), 422
    except Exception as e:
        logger.error(f"Unexpected parsing error for '{file.filename}': {e}")
        return jsonify({"error": "Something went wrong processing your document."}), 500

    try:
        ai_result = generate_all_content(extracted_text)
    except AIServiceError as e:
        message = str(e)
        logger.warning(f"AI generation failed: {message}")
        if "429" in message or "RESOURCE_EXHAUSTED" in message or "quota" in message.lower():
            return jsonify({"error": "Daily AI generation limit reached on the free tier. Please try again tomorrow."}), 429
        return jsonify({"error": "AI generation is temporarily unavailable. Please try again in a moment."}), 502

    try:
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
    except Exception as e:
        logger.error(f"Database save failed: {e}")
        return jsonify({"error": "Your content was generated but could not be saved. Please try again."}), 500

    saved_doc = get_document_by_id(doc_id)
    return jsonify(saved_doc)


@app.route("/api/history", methods=["GET"])
def history():
    try:
        documents = get_all_documents()
    except Exception as e:
        logger.error(f"History load failed: {e}")
        return jsonify({"error": "Could not load document history."}), 500

    return jsonify({"documents": documents})


@app.route("/api/document/<int:doc_id>", methods=["GET"])
def get_document(doc_id):
    try:
        document = get_document_by_id(doc_id)
    except Exception as e:
        logger.error(f"Document load failed for id={doc_id}: {e}")
        return jsonify({"error": "Could not load this document."}), 500

    if document is None:
        return jsonify({"error": "Document not found."}), 404

    return jsonify(document)


# --- Consistent JSON error responses for API routes ---
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "This endpoint does not exist."}), 404
    return render_template("index.html"), 404


@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File is too large. Maximum size is 10MB."}), 413


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Unhandled server error: {e}")
    return jsonify({"error": "An unexpected server error occurred. Please try again."}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
