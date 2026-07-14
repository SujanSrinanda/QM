# QuizMania 🎯

**QuizMania** is a Django-based AI-powered quiz platform that allows users to generate quizzes, host quiz sessions, join using unique quiz codes, track participants, and view scores.

The platform can generate multiple-choice questions from:

- A topic or text prompt
- PDF documents
- Images using OCR

AI-powered quiz generation is handled locally using **Ollama**.

---

## ✨ Features

### AI Quiz Generation

- Generate MCQs from a topic or prompt
- Generate questions from PDF files
- Extract text from images using OCR
- Generate explanations for answers
- Review generated questions before saving
- Local AI processing using Ollama

### Quiz Management

- Create and save quizzes
- Automatically generate unique quiz codes
- Store questions, choices, marks, and duration
- Delete quizzes
- View previous quiz history

### Live Quiz Sessions

- Start a quiz session
- Join using a unique quiz code
- Join with a participant alias
- View live participants
- Track participant count
- Display a live scoreboard
- End quiz sessions and view final results

### User Management

- User registration
- Login and logout
- Protected quiz-master features using Django authentication

---

## 🛠️ Technology Stack

| Category | Technology |
| --- | --- |
| Backend | Python, Django |
| Frontend | HTML, CSS, Django Templates |
| Database | SQLite |
| AI | Ollama |
| AI Model | `qwen2.5:3b` |
| PDF Processing | pypdf |
| OCR | Tesseract OCR, pytesseract |
| Image Processing | Pillow |
| Production Server | Gunicorn |
| Static Files | WhiteNoise |

---

## 📁 Project Structure

```text
QM-main/
├── manage.py
├── requirements.txt
├── Procfile
├── README.md
│
├── QM/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── QuizMania/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── ai_utils.py
│   ├── migrations/
│   ├── static/
│   └── templates/
│
└── scripts/
```

### Important Files

- `models.py` — Defines quizzes, questions, choices, participants, history, and responses.
- `views.py` — Contains authentication, quiz generation, sessions, scoring, and result logic.
- `ai_utils.py` — Handles Ollama, PDF extraction, image OCR, and AI response processing.
- `urls.py` — Defines application routes.
- `templates/` — Contains the HTML pages.
- `static/` — Contains CSS and other static files.

---

## ⚙️ Installation

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd QM-main
```

### 2. Create a Virtual Environment

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

#### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Apply Database Migrations

```bash
python manage.py migrate
```

### 5. Run the Development Server

```bash
python manage.py runserver
```

Open the application at:

```text
http://127.0.0.1:8000/
```

---

## 🤖 Ollama Setup

QuizMania uses Ollama for local AI-powered quiz generation.

### Install the Required Model

```bash
ollama pull qwen2.5:3b
```

### Verify the Model

```bash
ollama list
```

Make sure Ollama is running before using AI quiz generation.

The application connects to the local Ollama API at:

```text
http://localhost:11434/api/generate
```

---

## 🖼️ Image OCR Setup

Tesseract OCR is required only when generating quizzes from images.

After installing Tesseract, verify it with:

```bash
tesseract --version
```

If Tesseract is not available in the system `PATH`, configure its location in `QuizMania/ai_utils.py`.

Example for Windows:

```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

---

## 🔄 How It Works

### Quiz Creation

1. Register or log in.
2. Enter a topic or upload a PDF/image.
3. AI generates multiple-choice questions.
4. Review the generated questions.
5. Save the quiz.
6. A unique quiz code is created.

### Quiz Session

1. The quiz master starts a session.
2. Participants enter the quiz code.
3. Participants join using an alias.
4. Participants answer the questions.
5. Scores are calculated and stored.
6. The quiz master can view participants and the live scoreboard.
7. Final results are available after the quiz.

---

## 🗃️ Main Database Models

- **Quiz** — Stores quiz information and the unique join code.
- **Question** — Stores quiz questions, marks, duration, and explanations.
- **Choice** — Stores answer options and the correct answer.
- **QuizTaker** — Stores participant information and scores.
- **QuizHistory** — Stores completed quiz results.
- **UserResponse** — Stores the answers selected by participants.

---

## 🚀 Deployment

The project includes a `Procfile`:

```text
release: python manage.py migrate
web: gunicorn QM.wsgi
```

Before deploying:

- Set a strong `SECRET_KEY`
- Set `DEBUG = False`
- Configure `ALLOWED_HOSTS`
- Use environment variables for sensitive values
- Run `python manage.py collectstatic`
- Ensure the AI service is accessible from the deployed application

> **Note:** The project currently connects to Ollama on `localhost:11434`. For cloud deployment, Ollama must run on the same server or the AI configuration must be changed.

---

## 🔒 Security Notes

- Never commit `.env` files or secret keys.
- Disable Django debug mode in production.
- Configure trusted production hosts.
- Use HTTPS for production deployments.
- Consider PostgreSQL for larger production applications.

---

## 🔮 Future Improvements

- Real-time updates using Django Channels and WebSockets
- PostgreSQL support
- More question types
- Quiz categories and difficulty levels
- Randomized questions and answers
- Detailed analytics
- QR-code based quiz joining
- Export results to CSV or PDF
- Docker support
- Automated testing and CI/CD

---

## 🤝 Contributing

Contributions are welcome.

1. Fork the repository.
2. Create a new branch.
3. Make your changes.
4. Test the application.
5. Commit and push your changes.
6. Open a Pull Request.

---

## 📄 License

No license is currently included.

Add a license such as the **MIT License** if you want others to freely use, modify, and distribute the project.
