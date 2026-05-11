# Super AI Transcript (Whisper-only)

A beginner-friendly Flask web app for audio transcription using **local Whisper** (no Google keys required).
It also includes simple local text tools (cleaning, summary, Q&A, learning tips) that work offline.

## Features

- 🎤 **Browser Recording** - Record audio directly in the browser using MediaRecorder API
- 📁 **File Upload** - Upload audio files (MP3, WAV, M4A, WebM, OGG)
- 📝 **Speech-to-Text** - Convert audio to text using **local Whisper**
- ✨ **Text Cleaning (Local)** - Basic cleanup (spacing/punctuation)
- 📊 **Summary (Local)** - Basic structured summary
- 💬 **Q&A (Local)** - Simple excerpt-based answers
- 📚 **Learning Tips (Local)** - Starter-friendly suggestions
- 🗄️ **MySQL Storage** - Robust database for storing recordings and analysis

## Tech Stack

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Python, Flask
- **Database**: MySQL
- **Speech-to-Text**: OpenAI Whisper (local)
- **Audio decode**: FFmpeg

## Setup Instructions

### Prerequisites

1. **Python 3.10+** (3.12 works) - [Download](https://www.python.org/downloads/)
2. **MySQL Server** - [Download](https://dev.mysql.com/downloads/mysql/)
3. **FFmpeg** (required for Whisper) - [Download](https://ffmpeg.org/download.html)
4. **Docker** - optional

### Step 1: Install Python Dependencies

```bash
cd "c:\Super AI Transcript"
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Copy `.env.example` to `.env` and update:

```env
WHISPER_MODEL=tiny
```

### Step 3: Run the Application

```bash
cd "c:\Super AI Transcript"
python app.py
```

Open http://127.0.0.1:5000 in your browser (change `PORT` in `.env` if you use another port).

### Hugging Face Spaces (Docker)

This repo is meant to deploy as a **Docker Space**. The platform sets `PORT` (often `7860`); the app reads it automatically.

1. Create a Space with SDK **Docker** and connect this GitHub repo (or push with the included GitHub Action).
2. In the Space **Settings → Variables and secrets**, add at least `GEMINI_API_KEY` if you want AI cleaning/summary/Q&A. Optional: `DB_*` if you attach an external MySQL reachable from the Space.
3. Without MySQL, the UI still loads; **recording history** can fall back to the shipped export under `backups/mysql_recordings_export/` when the database is unavailable.

Space URL pattern: `https://huggingface.co/spaces/<your-username>/<space-name>`

### Optional: Run with Docker (local)

```bash
docker build -t super-ai-transcript .
docker run -p 5000:5000 --rm -v %cd%:/app -v %cd%/uploads:/app/uploads super-ai-transcript
```

With Whisper inside the container (larger image):

```bash
docker run -p 5000:5000 -e WHISPER_LOCAL=1 -e WHISPER_MODEL=small --rm -v %cd%:/app -v %cd%/uploads:/app/uploads super-ai-transcript
```

## Project Structure

```
Super AI Transcript/
├── app.py            # Main Flask backend
├── database.py       # MySQL operations
├── requirements.txt  # Python dependencies
├── README.md         # Project overview
├── templates/
│   └── index.html   # Main UI
├── static/
│   ├── script.js    # Frontend JavaScript
│   └── styles.css   # CSS styling
├── backups/         # Optional: exported history for Space fallback
└── uploads/         # Temporary audio files
```

## API Endpoints (Local)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main page |
| `/api/transcribe` | POST | Transcribe audio |
| `/api/clean` | POST | Clean transcript |
| `/api/summary` | POST | Generate summary |
| `/api/ask` | POST | Q&A on transcript |
| `/api/learn` | POST | Learning suggestions |
| `/api/recordings` | GET | List all recordings |
| `/api/recordings/<id>` | DELETE | Delete recording |

## License

MIT License - Free to use and modify.
