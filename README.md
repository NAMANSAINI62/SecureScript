---
title: Super Transcript AI
emoji: 💻
colorFrom: indigo
colorTo: indigo
sdk: docker
pinned: false
---

# Super AI Transcript 🎙️

A full-stack web application for audio transcription, AI-powered text cleaning, smart summarization, Q&A, and learning suggestions.

## Features

- 🎤 **Browser Recording** - Record audio directly in the browser using MediaRecorder API
- 📁 **File Upload** - Upload audio files (MP3, WAV, M4A, WebM, OGG)
- 📝 **Speech-to-Text** - Convert audio to text using OpenAI Whisper (local)
- ✨ **AI Cleaning** - Fix grammar and punctuation using Google Gemini (optional)
- 📊 **Smart Summary** - Extract title, key points, action items
- 💬 **Q&A on Transcript** - Ask questions about your recordings
- 📚 **Learning Suggestions** - Get better phrases, resources, and roadmaps
- 💾 **SQLite Storage** - Save recordings for future playback and analysis

## Tech Stack

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Python, Flask
- **Database**: SQLite
- **AI APIs**: Google Gemini (optional), OpenAI Whisper (local)
- **Audio decode**: FFmpeg

## Setup Instructions

### Prerequisites

1. **Python 3.8+** - [Download](https://www.python.org/downloads/)
2. **FFmpeg** (required for Whisper) - [Download](https://ffmpeg.org/download.html)

### Step 1: Install Python Dependencies

```bash
cd "d:\Super AI Transcript"
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Copy `.env.example` to `.env` and update:

```env
GEMINI_API_KEY=your-gemini-api-key
WHISPER_MODEL=tiny
```

### Step 3: Run the Application

```bash
cd "d:\Super AI Transcript"
python app.py
```

Open http://127.0.0.1:5000 in your browser.

## Project Structure

```
Super AI Transcript/
├── app.py                  # Flask backend (all routes)
├── database.py             # SQLite operations
├── templates/
│   └── index.html          # Main UI
├── static/
│   ├── script.js           # Frontend JavaScript
│   └── styles.css          # CSS styling
├── uploads/                # Temp audio files
├── requirements.txt        # Python dependencies
├── .env                    # API keys (secret!)
├── super_ai_transcript.db  # SQLite Database File
└── README.md               # This file
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main page |
| `/api/transcribe` | POST | Transcribe audio |
| `/api/clean` | POST | Clean transcript with AI |
| `/api/summary` | POST | Generate summary |
| `/api/ask` | POST | Q&A on transcript |
| `/api/learn` | POST | Learning suggestions |
| `/api/recordings` | GET | List all recordings |
| `/api/recordings/<id>/audio` | GET | Stream audio |
| `/api/recordings/<id>` | DELETE | Delete recording |

## License

MIT License - Free to use and modify.
