# LearnInsight AI

Turn any document into a complete AI-powered learning experience.

**Live Demo:** https://learninsight-ai.onrender.com

Built as part of the AB Talks 60-Day Claude AI Challenge.

---

## What It Does

Upload a PDF, DOCX, or TXT document and LearnInsight AI generates five distinct learning materials from it in a single AI call:

- **Summary** — a concise overview of the core content
- **Simplified Explanation** — the same content explained in plain, beginner-friendly language
- **Quiz** — an interactive multiple-choice quiz with instant scoring
- **Flashcards** — flip-through cards for quick revision
- **AI Notes** — structured, topic-organized study notes

All processed documents are saved to a history list so you can revisit their generated materials without reprocessing.

## Tech Stack

- **Frontend:** HTML, CSS, Vanilla JavaScript (served directly by Flask)
- **Backend:** Python, Flask
- **Database:** SQLite
- **AI:** Google Gemini API (`gemini-3.5-flash`)
- **Hosting:** Render (free tier)

## Live Application

https://learninsight-ai.onrender.com

> **Note:** This app runs on Render's free tier, which has two known limitations:
> 1. The server "sleeps" after periods of inactivity — the first request after sleeping may take up to a minute to respond while it wakes up.
> 2. The free tier's filesystem is ephemeral, meaning the document history (SQLite database) resets whenever the service restarts or redeploys. This is a hosting-tier limitation, not an application bug.

## Running Locally

### Prerequisites
- Python 3.10+
- A free Google Gemini API key ([get one here](https://aistudio.google.com/apikey))

### Setup

```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\Activate.ps1
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file inside `backend/`:
