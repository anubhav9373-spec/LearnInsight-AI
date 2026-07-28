const BACKEND_URL = "";

let currentQuiz = [];
let userAnswers = [];
let currentFlashcards = [];
let currentCardIndex = 0;

document.getElementById("checkBtn").addEventListener("click", async () => {
  const resultEl = document.getElementById("result");
  resultEl.className = "";
  resultEl.textContent = "Checking...";
  try {
    const response = await fetch(`${BACKEND_URL}/api/health`);
    const data = await response.json();
    resultEl.textContent = `Backend says: ${data.status}`;
    resultEl.className = "status-ok";
  } catch (error) {
    resultEl.textContent = "Could not reach the backend. Is it running?";
    resultEl.className = "status-error";
  }
});

document.getElementById("fileInput").addEventListener("change", (e) => {
  const nameEl = document.getElementById("fileChosenName");
  if (e.target.files && e.target.files.length > 0) {
    nameEl.textContent = e.target.files[0].name;
  } else {
    nameEl.textContent = "No file chosen";
  }
});

// --- Tab switching (with accessibility: aria-selected updated) ---
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => {
      b.classList.remove("active");
      b.setAttribute("aria-selected", "false");
    });
    document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));

    btn.classList.add("active");
    btn.setAttribute("aria-selected", "true");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
  });
});

const uploadBtn = document.getElementById("uploadBtn");

uploadBtn.addEventListener("click", async () => {
  const fileInput = document.getElementById("fileInput");
  const statusEl = document.getElementById("uploadStatus");

  statusEl.className = "";

  if (!fileInput.files || fileInput.files.length === 0) {
    statusEl.textContent = "Please select a file first.";
    statusEl.className = "status-error";
    return;
  }

  const file = fileInput.files[0];
  const formData = new FormData();
  formData.append("file", file);

  uploadBtn.disabled = true;
  uploadBtn.textContent = "Processing...";
  statusEl.className = "status-loading";
  statusEl.innerHTML = '<span class="spinner"></span>Uploading and generating AI content (this may take 10-20 seconds)...';

  try {
    const response = await fetch(`${BACKEND_URL}/api/process`, {
      method: "POST",
      body: formData
    });
    const data = await response.json();

    if (!response.ok) {
      statusEl.className = "status-error";
      statusEl.textContent = data.error;
      return;
    }

    statusEl.className = "status-done";
    statusEl.textContent = "Done! Your study materials are ready below.";
    displayDocument(data);
    loadHistory();

  } catch (error) {
    statusEl.className = "status-error";
    statusEl.textContent = "Could not reach the backend. Is it running?";
  } finally {
    uploadBtn.disabled = false;
    uploadBtn.textContent = "Upload & Process";
  }
});

function displayDocument(doc) {
  const resultsSection = document.getElementById("resultsSection");
  const resultsHeading = document.getElementById("resultsHeading");

  resultsHeading.textContent = `${doc.filename} — processed ${new Date(doc.upload_date).toLocaleString()}`;
  document.getElementById("summaryText").textContent = doc.summary;
  document.getElementById("explanationText").textContent = doc.explanation;
  document.getElementById("notesText").textContent = doc.notes;

  renderQuiz(doc.quiz);
  renderFlashcards(doc.flashcards);

  resultsSection.style.display = "block";

  document.querySelectorAll(".tab-btn").forEach((b) => {
    b.classList.remove("active");
    b.setAttribute("aria-selected", "false");
  });
  document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));

  const summaryTabBtn = document.querySelector('.tab-btn[data-tab="summary"]');
  summaryTabBtn.classList.add("active");
  summaryTabBtn.setAttribute("aria-selected", "true");
  document.getElementById("tab-summary").classList.add("active");

  resultsSection.scrollIntoView({ behavior: "smooth" });
}

async function loadHistory() {
  const historyList = document.getElementById("historyList");
  historyList.innerHTML = '<p style="text-align:center; color:#6B7085; font-size:14px;"><span class="spinner"></span>Loading...</p>';

  try {
    const response = await fetch(`${BACKEND_URL}/api/history`);
    const data = await response.json();

    if (!response.ok || !data.documents || data.documents.length === 0) {
      historyList.innerHTML = '<p id="historyEmptyMessage">No documents yet. Upload your first file above to get started.</p>';
      return;
    }

    historyList.innerHTML = "";
    data.documents.forEach((doc) => {
      const item = document.createElement("div");
      item.className = "history-item";

      const name = document.createElement("span");
      name.className = "history-filename";
      name.textContent = doc.filename;

      const date = document.createElement("span");
      date.className = "history-date";
      date.textContent = new Date(doc.upload_date).toLocaleDateString();

      item.appendChild(name);
      item.appendChild(date);
      item.addEventListener("click", () => openHistoryDocument(doc.id));
      historyList.appendChild(item);
    });

  } catch (error) {
    historyList.innerHTML = '<p style="color:#B3261E; text-align:center; font-size:14px;">Could not load document history. Is the backend running?</p>';
  }
}

async function openHistoryDocument(id) {
  try {
    const response = await fetch(`${BACKEND_URL}/api/document/${id}`);
    const data = await response.json();

    if (!response.ok) {
      alert(`Could not load this document: ${data.error}`);
      return;
    }

    displayDocument(data);

  } catch (error) {
    alert("Could not reach the backend.");
  }
}

loadHistory();

function renderQuiz(quiz) {
  currentQuiz = quiz;
  userAnswers = new Array(quiz.length).fill(null);

  const container = document.getElementById("quizContainer");
  container.innerHTML = "";

  quiz.forEach((q, qIndex) => {
    const questionDiv = document.createElement("div");
    questionDiv.className = "quiz-question";

    const questionTitle = document.createElement("p");
    questionTitle.className = "quiz-question-title";
    questionTitle.textContent = `${qIndex + 1}. ${q.question}`;
    questionDiv.appendChild(questionTitle);

    q.options.forEach((option) => {
      const label = document.createElement("label");
      label.className = "quiz-option";

      const radio = document.createElement("input");
      radio.type = "radio";
      radio.name = `question-${qIndex}`;
      radio.value = option;
      radio.addEventListener("change", () => {
        userAnswers[qIndex] = option;
      });

      label.appendChild(radio);
      label.appendChild(document.createTextNode(" " + option));
      questionDiv.appendChild(label);
    });

    container.appendChild(questionDiv);
  });

  const submitBtn = document.createElement("button");
  submitBtn.textContent = "Submit Quiz";
  submitBtn.id = "submitQuizBtn";
  submitBtn.className = "btn-primary";
  submitBtn.addEventListener("click", submitQuiz);
  container.appendChild(submitBtn);

  const scoreDiv = document.createElement("div");
  scoreDiv.id = "quizScoreResult";
  container.appendChild(scoreDiv);
}

function submitQuiz() {
  let correctCount = 0;
  const scoreDiv = document.getElementById("quizScoreResult");

  currentQuiz.forEach((q, qIndex) => {
    const isCorrect = userAnswers[qIndex] === q.correct_answer;
    if (isCorrect) correctCount++;

    const questionDivs = document.querySelectorAll(".quiz-question");
    const questionDiv = questionDivs[qIndex];
    questionDiv.querySelectorAll(".quiz-option").forEach((label) => {
      const radio = label.querySelector("input");
      radio.disabled = true;
      if (radio.value === q.correct_answer) {
        label.classList.add("correct-answer");
      } else if (radio.value === userAnswers[qIndex] && !isCorrect) {
        label.classList.add("wrong-answer");
      }
    });

    const feedback = document.createElement("p");
    feedback.className = "quiz-explanation";
    feedback.textContent = isCorrect
      ? `Correct! ${q.explanation}`
      : `Incorrect. Correct answer: "${q.correct_answer}". ${q.explanation}`;
    questionDiv.appendChild(feedback);
  });

  scoreDiv.innerHTML = `<h3>Your Score: ${correctCount} / ${currentQuiz.length}</h3>`;
  document.getElementById("submitQuizBtn").disabled = true;
}

function renderFlashcards(flashcards) {
  currentFlashcards = flashcards;
  currentCardIndex = 0;
  drawCurrentCard();
}

function drawCurrentCard() {
  const container = document.getElementById("flashcardContainer");
  container.innerHTML = "";

  if (currentFlashcards.length === 0) return;

  const card = currentFlashcards[currentCardIndex];

  const cardOuter = document.createElement("div");
  cardOuter.className = "flashcard";

  const cardInner = document.createElement("div");
  cardInner.className = "flashcard-inner";

  const front = document.createElement("div");
  front.className = "flashcard-front";
  front.textContent = card.front;

  const back = document.createElement("div");
  back.className = "flashcard-back";
  back.textContent = card.back;

  cardInner.appendChild(front);
  cardInner.appendChild(back);
  cardOuter.appendChild(cardInner);

  cardOuter.addEventListener("click", () => {
    cardOuter.classList.toggle("flipped");
  });

  container.appendChild(cardOuter);

  const nav = document.createElement("div");
  nav.className = "flashcard-nav";

  const prevBtn = document.createElement("button");
  prevBtn.textContent = "< Prev";
  prevBtn.className = "btn-secondary";
  prevBtn.disabled = currentCardIndex === 0;
  prevBtn.addEventListener("click", () => {
    currentCardIndex--;
    drawCurrentCard();
  });

  const counter = document.createElement("span");
  counter.className = "flashcard-counter";
  counter.textContent = `Card ${currentCardIndex + 1} of ${currentFlashcards.length}`;

  const nextBtn = document.createElement("button");
  nextBtn.textContent = "Next >";
  nextBtn.className = "btn-secondary";
  nextBtn.disabled = currentCardIndex === currentFlashcards.length - 1;
  nextBtn.addEventListener("click", () => {
    currentCardIndex++;
    drawCurrentCard();
  });

  nav.appendChild(prevBtn);
  nav.appendChild(counter);
  nav.appendChild(nextBtn);
  container.appendChild(nav);

  const hint = document.createElement("p");
  hint.className = "flashcard-hint";
  hint.textContent = "(Click the card to flip it)";
  container.appendChild(hint);
}