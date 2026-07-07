---
title: Super Transcript AI
emoji: 💻
colorFrom: indigo
colorTo: indigo
sdk: docker
pinned: false
---

# Super AI Transcript

Super AI Transcript is a modern AI-powered speech practice app that records audio, transcribes speech with Whisper, and turns the result into an English improvement report using a local Ollama model.

It is built for learners who want more than a transcript: corrected English, improved phrasing, speaking practice, vocabulary upgrades, assessment scores, and a simple daily improvement plan.

## Core Features

- **Browser audio recording** with a clean start and stop flow.
- **Live recording feedback** with timer and waveform-style visual display.
- **Speech-to-text transcription** powered by local OpenAI Whisper.
- **AI transcript cleaning** through a local Ollama model.
- **Corrected transcript** that preserves the original meaning.
- **Improved English version** rewritten in clearer, more natural language.
- **English assessment report** with grammar, vocabulary, fluency, pronunciation likelihood, overall score, and level.
- **Speaking practice version** for pronunciation and fluency training.
- **Corrections explained** in a learner-friendly format.
- **Vocabulary upgrades** and a personalized improvement plan.

## How It Works

1. Record audio directly in the browser.
2. Send the audio file to the Flask backend.
3. Transcribe the audio locally with Whisper.
4. Review the original transcript.
5. Clean and improve the transcript with Ollama.
6. Generate an English learning report with scores, corrections, and practice advice.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, Flask, Flask-CORS |
| Transcription | OpenAI Whisper |
| AI feedback | Ollama local model |
| Audio processing | FFmpeg |
| Deployment | Docker, Docker Compose, Hugging Face Spaces metadata |

## Requirements

- Python 3.8+
- FFmpeg installed and available on your system `PATH`
- Ollama installed and running locally
- An Ollama model such as `phi3` or `llama3`

## Quick Start

Install dependencies:

```bash
pip install -r requirements.txt
```

Create the environment file:

```bash
copy .env.example .env
```

Pull an Ollama model:

```bash
ollama pull phi3
```

Start Ollama:

```bash
ollama serve
```

Run the Flask app:

```bash
python app.py
```

Open the app:

```text
http://127.0.0.1:5000
```

## Docker

Build and run the app with Docker Compose:

```bash
docker compose up --build
```

Then open:

```text
http://127.0.0.1:5000
```

## Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `5000` | Flask server port |
| `OLLAMA_MODEL` | `phi3` | Local Ollama model used for transcript improvement |
| `PERSIST_DATA_DIR` | project folder | Optional persistent data directory |
| `WHISPER_MODEL` | `small` in `.env.example` | Intended Whisper model setting |
| `GEMINI_API_KEY` | empty | Present in the template, not required by the current app code |

> Current note: `app.py` loads Whisper with the `small` model constant.

## API Endpoints

| Endpoint | Method | Description |
| --- | --- | --- |
| `/` | `GET` | Serves the main app interface |
| `/api/preload` | `POST` | Warms up Whisper and Ollama in the background |
| `/api/transcribe` | `POST` | Uploads audio and returns the original transcript |
| `/api/clean` | `POST` | Cleans transcript text and returns the English improvement report |

### Transcribe Audio

```bash
curl -X POST http://127.0.0.1:5000/api/transcribe ^
  -F "audio=@sample.webm"
```

### Clean Transcript

```bash
curl -X POST http://127.0.0.1:5000/api/clean ^
  -H "Content-Type: application/json" ^
  -d "{\"text\":\"hello my name is naman and i want improve english\"}"
```

## Project Structure

```text
Super AI Transcript/
├── app.py
├── templates/
│   └── index.html
├── static/
│   ├── script.js
│   └── styles.css
├── docs/
│   └── screenshots/
├── uploads/
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Notes

- FFmpeg is required for Whisper audio processing.
- Ollama must be running for full AI feedback.
- If Ollama is offline, the app returns a basic fallback learning report.
- Uploaded audio files are removed after transcription.

## License

MIT License. Free to use, modify, and build on.
