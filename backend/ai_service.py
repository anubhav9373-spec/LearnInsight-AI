"""
ai_service.py
Handles all interactions with the Gemini API.
No other module should call the Gemini API directly.

Day 6 update: added AI Notes into the existing single consolidated call
(still 1 Gemini request per document — quota-efficient architecture preserved).
"""

import os
import re
import json
import time
from google import genai

MODEL_NAME = "gemini-3.5-flash"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2

_client = None


class AIServiceError(Exception):
    """Raised when an AI generation call fails after all retries."""
    pass


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise AIServiceError("GEMINI_API_KEY is not configured.")
        _client = genai.Client(api_key=api_key)
    return _client


def _clean_markdown(text):
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    return text.strip()


def _is_retryable(error):
    message = str(error)
    return "503" in message or "UNAVAILABLE" in message


def _generate_with_retry(prompt):
    client = _get_client()
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
            return response.text
        except Exception as e:
            last_error = e
            if _is_retryable(e) and attempt < MAX_RETRIES:
                wait_time = RETRY_DELAY_SECONDS * (2 ** (attempt - 1))
                time.sleep(wait_time)
                continue
            else:
                break

    raise AIServiceError(f"Gemini API call failed after {MAX_RETRIES} attempts: {last_error}")


def _extract_json(raw_text):
    text = raw_text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise AIServiceError(f"AI returned malformed JSON: {e}")


def _validate_quiz(quiz_data):
    if not isinstance(quiz_data, list) or len(quiz_data) == 0:
        raise AIServiceError("AI returned an unexpected quiz format.")

    valid_questions = []
    for q in quiz_data:
        if (
            isinstance(q, dict)
            and "question" in q
            and "options" in q
            and isinstance(q["options"], list)
            and len(q["options"]) == 4
            and "correct_answer" in q
            and q["correct_answer"] in q["options"]
        ):
            valid_questions.append({
                "question": q["question"],
                "options": q["options"],
                "correct_answer": q["correct_answer"],
                "explanation": q.get("explanation", "")
            })

    if len(valid_questions) == 0:
        raise AIServiceError("AI-generated quiz did not contain any valid questions.")

    return valid_questions


def _validate_flashcards(flashcard_data):
    if not isinstance(flashcard_data, list) or len(flashcard_data) == 0:
        raise AIServiceError("AI returned an unexpected flashcard format.")

    valid_cards = []
    for c in flashcard_data:
        if isinstance(c, dict) and "front" in c and "back" in c and c["front"].strip() and c["back"].strip():
            valid_cards.append({"front": c["front"], "back": c["back"]})

    if len(valid_cards) == 0:
        raise AIServiceError("AI-generated flashcards did not contain any valid cards.")

    return valid_cards


def generate_all_content(text):
    """
    Generates Summary, Simplified Explanation, Quiz, Flashcards, AND Notes
    in a SINGLE Gemini API call, to conserve free-tier daily quota.

    Returns a dict:
    {
        "summary": str,
        "explanation": str,
        "notes": str,
        "quiz": [ {question, options, correct_answer, explanation}, ... ],
        "flashcards": [ {front, back}, ... ]
    }
    """
    prompt = f"""You are an expert study assistant. Read the following document text and generate FIVE distinct learning materials from it. Return ONLY valid JSON, no markdown code fences, no commentary before or after.

Return the JSON in EXACTLY this shape:
{{
  "summary": "A concise, well-structured summary in plain prose, 150-250 words. Capture the 5-7 most important ideas. No markdown formatting (no **, no #).",
  "explanation": "A simplified, beginner-friendly explanation in plain prose, 150-250 words. Written as if teaching someone with no background knowledge, using at least one simple analogy. Avoid jargon. No markdown formatting. Must read distinctly differently from the summary — teaching tone, not a condensed repeat of it.",
  "notes": "Structured, scannable study notes organized by topic. Use short lines separated by newlines, each starting with a dash (-) for a bullet point. Group related points under a plain-text topic heading line (no # symbol, just the heading text followed by a colon). This must be distinct from the summary: notes are terse and scannable, not narrative prose.",
  "quiz": [
    {{
      "question": "string",
      "options": ["string", "string", "string", "string"],
      "correct_answer": "string (must exactly match one of the 4 options)",
      "explanation": "string, one sentence explaining why this answer is correct"
    }}
  ],
  "flashcards": [
    {{
      "front": "string (a term, question, or concept, concise)",
      "back": "string (its definition or answer, concise)"
    }}
  ]
}}

Rules:
- Create between 5 and 8 quiz questions.
- Create between 5 and 10 flashcards.
- Every quiz question must have exactly 4 options.
- Base everything only on the document text below — do not add outside information.
- Return ONLY the JSON object above. No extra text, no markdown fences.

Document text:
\"\"\"
{text[:12000]}
\"\"\"

JSON:"""

    raw_text = _generate_with_retry(prompt)
    data = _extract_json(raw_text)

    if not isinstance(data, dict):
        raise AIServiceError("AI returned an unexpected response format.")

    required_keys = ["summary", "explanation", "notes", "quiz", "flashcards"]
    missing = [k for k in required_keys if k not in data]
    if missing:
        raise AIServiceError(f"AI response is missing required fields: {', '.join(missing)}")

    return {
        "summary": _clean_markdown(data["summary"]),
        "explanation": _clean_markdown(data["explanation"]),
        "notes": data["notes"].strip(),
        "quiz": _validate_quiz(data["quiz"]),
        "flashcards": _validate_flashcards(data["flashcards"]),
    }