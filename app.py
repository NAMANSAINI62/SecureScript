"""
Super AI Transcript - A Simple Audio Transcription & AI Processing App
========================================================================
This is a beginner-friendly Flask app for recording/uploading audio, 
transcribing it, and processing with AI (Gemini).
"""

import os
import json
import io
import sys
import re
import shutil
import subprocess
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
from database import (
    init_db, save_recording, update_recording, 
    get_all_recordings, get_audio_data, delete_recording, save_qa
)

# Whisper model (lazy-loaded). Defaulting to 'tiny' keeps first-run downloads fast for beginners.
WHISPER_MODEL_NAME = os.environ.get('WHISPER_MODEL', 'tiny')
whisper_model = None

# Load environment variables from .env file
load_dotenv()

# Ensure UTF-8 console output on Windows to avoid UnicodeEncodeError
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin requests

# Simple configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
BACKUP_EXPORT_DIR = Path(os.path.dirname(__file__)) / 'backups' / 'mysql_recordings_export'
BACKUP_METADATA_FILE = BACKUP_EXPORT_DIR / 'recordings_metadata.json'

# Gemini AI (used for text cleaning/summary/Q&A/learning tips)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def call_ai(system_prompt: str, user_message: str) -> str:
    if not GEMINI_API_KEY:
        return "⚠️ GEMINI_API_KEY not configured. Add it to your .env file."
    try:
        model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash').strip() or 'gemini-2.5-flash'
        if model_name.startswith('models/'):
            model_name = model_name[len('models/'):]
        model = genai.GenerativeModel(model_name)
        resp = model.generate_content(f"{system_prompt}\n\n{user_message}")
        return (resp.text or '').strip()
    except Exception as e:
        return f"Error calling AI: {str(e)}"

def parse_json_block(text: str, default_value):
    try:
        if not text:
            return default_value
        if '{' in text:
            return json.loads(text[text.find('{'):text.rfind('}') + 1])
    except Exception:
        pass
    return default_value

def ensure_ffmpeg_available():
    """
    Whisper relies on the `ffmpeg` executable.

    Beginner-friendly behavior:
    - If `ffmpeg` is already on PATH, great.
    - If not, try the common WinGet install location and temporarily patch PATH for this process.
    """
    if shutil.which('ffmpeg') is not None:
        return

    # Common WinGet portable location (Gyan.FFmpeg)
    local_app_data = os.environ.get('LOCALAPPDATA') or ''
    candidate_dirs = []
    if local_app_data:
        candidate_dirs.append(os.path.join(
            local_app_data,
            'Microsoft', 'WinGet', 'Packages',
            'Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe',
            'ffmpeg-8.1.1-full_build', 'bin'
        ))

    for d in candidate_dirs:
        ff = os.path.join(d, 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')
        if os.path.exists(ff):
            os.environ['PATH'] = d + os.pathsep + os.environ.get('PATH', '')
            if shutil.which('ffmpeg') is not None:
                return

    raise RuntimeError(
        "FFmpeg not found on PATH. Install FFmpeg and restart the terminal, or add FFmpeg to PATH. "
        "Whisper uses FFmpeg to read audio formats like webm/mp3/m4a."
    )


def get_audio_duration_seconds(file_path: str):
    """
    Get media duration using ffprobe (part of FFmpeg).
    Returns float seconds or None if unknown.
    """
    try:
        ensure_ffmpeg_available()
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True).strip()
        if not out:
            return None
        return float(out)
    except Exception:
        return None


def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        import whisper
        whisper_model = whisper.load_model(WHISPER_MODEL_NAME)
    return whisper_model


def basic_clean_text(text: str) -> str:
    text = (text or '').strip()
    if not text:
        return ''
    # Keep a tiny local fallback: whitespace + punctuation normalization.
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)
    return text.strip()


def basic_summary(text: str):
    text = basic_clean_text(text)
    if not text:
        return {'title': 'Summary', 'summary': '', 'key_points': [], 'action_items': []}

    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    summary = ' '.join(sentences[:3])
    key_points = sentences[:5]
    title = (sentences[0][:60] + '...') if len(sentences[0]) > 60 else sentences[0]
    return {
        'title': title or 'Summary',
        'summary': summary,
        'key_points': key_points,
        'action_items': []
    }


def basic_answer(transcript: str, question: str) -> str:
    transcript = (transcript or '').strip()
    question = (question or '').strip()
    if not transcript or not question:
        return ''
    q_words = [w.lower() for w in re.findall(r"[a-zA-Z']+", question) if len(w) > 2]
    if not q_words:
        return transcript[:400] + ('...' if len(transcript) > 400 else '')
    # Return a small excerpt around the first matching word
    lower = transcript.lower()
    for w in q_words[:10]:
        idx = lower.find(w)
        if idx != -1:
            start = max(0, idx - 120)
            end = min(len(transcript), idx + 240)
            excerpt = transcript[start:end].strip()
            return excerpt + ('...' if end < len(transcript) else '')
    return transcript[:400] + ('...' if len(transcript) > 400 else '')


def basic_learning_tips(topic: str = ''):
    t = (topic or '').strip()
    focus = f" (focus: {t})" if t else ''
    return {
        'better_phrases': [
            f"Break your learning into small daily practice sessions{focus}.",
            "Build a tiny project for each concept you learn.",
            "Write notes in your own words after finishing a lesson."
        ],
        'missing_points': [
            "Make sure you can explain the concept without looking at notes.",
            "Practice debugging: read errors carefully and search the message.",
        ],
        'resources': [
            "Official docs (Flask / JavaScript / Python).",
            "freeCodeCamp + MDN for web fundamentals.",
            "A small GitHub repo to track your progress."
        ],
        'roadmap': [
            "Week 1: Basics + setup tools",
            "Week 2: Build a small project",
            "Week 3: Add storage (DB) and deploy",
        ]
    }


def load_backup_recordings(limit: int = 50):
    """
    Load read-only recordings exported from MySQL for environments
    where DB is temporarily unavailable (e.g. cloud demo deployments).
    """
    if not BACKUP_METADATA_FILE.exists():
        return []
    try:
        with open(BACKUP_METADATA_FILE, 'r', encoding='utf-8') as f:
            items = json.load(f) or []
        items = sorted(items, key=lambda x: x.get('id', 0), reverse=True)
        return items[:limit]
    except Exception:
        return []


def get_backup_audio(recording_id):
    """Return (audio_data, mime_type) from exported backup files."""
    recordings = load_backup_recordings(limit=100000)
    matched = None
    for item in recordings:
        if str(item.get('id')) == str(recording_id):
            matched = item
            break
    if not matched:
        return None, None

    filename = matched.get('exported_audio_file')
    if not filename:
        return None, None
    audio_path = BACKUP_EXPORT_DIR / filename
    if not audio_path.exists():
        return None, None

    try:
        with open(audio_path, 'rb') as f:
            data = f.read()
        mime_type = matched.get('audio_mime_type') or 'audio/webm'
        return data, mime_type
    except Exception:
        return None, None



# ======================== ROUTES (URLs) ========================

@app.route('/')
def home():
    """Render the main page"""
    return render_template('index.html')


@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    """
    Upload audio file and transcribe it using Whisper.
    
    Steps:
    1. Save audio file to uploads folder
    2. Save audio data to database
    3. Use Whisper to convert audio to text
    4. Update database with transcript
    """
    try:
        # Check if audio file was uploaded
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        filename = audio_file.filename or 'temp.webm'
        
        # Save audio file to uploads folder
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        audio_file.save(file_path)
        
        # Read audio data for database
        audio_file.seek(0)
        audio_data = audio_file.read()

        # Duration (seconds) for history UI
        duration_seconds = get_audio_duration_seconds(file_path)
        
        # Save to database first (so we don't lose the audio)
        recording_id = save_recording(
            filename=filename,
            audio_data=audio_data,
            audio_mime_type=audio_file.content_type,
            original_transcript="",
            duration_seconds=duration_seconds
        )
        print(f"✅ Recording saved to database with ID: {recording_id}")
        
        try:
            ensure_ffmpeg_available()
            model = get_whisper_model()
            print(f"🎙️ Transcribing with Whisper ({WHISPER_MODEL_NAME})...")
            result = model.transcribe(file_path)
            transcript = (result.get('text') or '').strip()
            update_recording(recording_id, original_transcript=transcript)
            return jsonify({'original_transcript': transcript, 'recording_id': recording_id})
        except Exception as transcribe_error:
            print(f"⚠️ Transcription error: {str(transcribe_error)}")
            return jsonify({
                'error': f'Transcription failed: {str(transcribe_error)}',
                'recording_id': recording_id
            }), 500
            
    except Exception as e:
        print(f"❌ Error in /api/transcribe: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/clean', methods=['POST'])
def clean_text():
    """
    Use AI to fix grammar, punctuation, and remove filler words.
    """
    try:
        data = request.get_json() or {}
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        # Use Gemini AI for real grammar/punctuation clean-up (user provided API key).
        cleaned = call_ai(
            "Fix grammar and punctuation, remove filler words, and make it easy to read. Return ONLY the cleaned text.",
            text
        )
        if cleaned.startswith("⚠️") or cleaned.startswith("Error calling AI:"):
            # If AI isn't configured or fails, fall back to basic formatting so the button still works.
            cleaned = basic_clean_text(text)
        
        # Update database if we have a recording ID
        if data.get('recording_id'):
            update_recording(data['recording_id'], cleaned_transcript=cleaned)
        
        return jsonify({'cleaned_transcript': cleaned})
        
    except Exception as e:
        print(f"❌ Error in /api/clean: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/summary', methods=['POST'])
def get_summary():
    """
    Use AI to create a summary with title, key points, and action items.
    """
    try:
        data = request.get_json() or {}
        transcript = data.get('transcript', '').strip()
        
        if not transcript:
            return jsonify({'error': 'No transcript provided'}), 400
        ai_response = call_ai(
            "Summarize this transcript as JSON with keys: title, summary, key_points (array), action_items (array). Return ONLY JSON.",
            transcript
        )
        summary_json = parse_json_block(
            ai_response,
            basic_summary(transcript)
        )
        
        # Update database if we have a recording ID
        if data.get('recording_id'):
            update_recording(
                data['recording_id'],
                summary=summary_json.get('summary', ''),
                key_points=json.dumps(summary_json.get('key_points', []))
            )
        
        return jsonify(summary_json)
        
    except Exception as e:
        print(f"❌ Error in /api/summary: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ask', methods=['POST'])
def ask_question():
    """
    Ask a question about the transcript and get an AI-powered answer.
    """
    try:
        data = request.get_json() or {}
        transcript = data.get('transcript', '').strip()
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'error': 'No question provided'}), 400
        
        if not transcript:
            return jsonify({'error': 'No transcript provided'}), 400
        
        answer = call_ai(
            f"Answer the question using ONLY the transcript context.\n\nTranscript:\n{transcript}",
            f"Question: {question}"
        )
        if answer.startswith("⚠️") or answer.startswith("Error calling AI:"):
            answer = basic_answer(transcript, question)
        
        # Save Q&A to database if we have a recording ID
        if data.get('recording_id'):
            save_qa(data['recording_id'], question, answer)
        
        return jsonify({'answer': answer})
        
    except Exception as e:
        print(f"❌ Error in /api/ask: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/learn', methods=['POST'])
def get_learning_tips():
    """
    Get learning tips and improvement suggestions from AI.
    """
    try:
        data = request.get_json() or {}
        transcript = data.get('transcript', '').strip()
        topic = (data.get('topic') or '').strip()
        
        if not transcript:
            return jsonify({'error': 'No transcript provided'}), 400
        
        prompt = (
            "Return ONLY valid JSON (no markdown). "
            "Schema: { better_phrases: string[], missing_points: string[], resources: string[], roadmap: string[] }. "
            "Keep items short and beginner-friendly."
        )
        user_msg = transcript if not topic else f"Topic focus: {topic}\n\nTranscript:\n{transcript}"
        tips_text = call_ai(prompt, user_msg)
        tips_json = parse_json_block(tips_text, basic_learning_tips(topic=topic))
        normalized = {
            'better_phrases': tips_json.get('better_phrases') or [],
            'missing_points': tips_json.get('missing_points') or [],
            'resources': tips_json.get('resources') or [],
            'roadmap': tips_json.get('roadmap') or []
        }
        return jsonify(normalized)
        
    except Exception as e:
        print(f"❌ Error in /api/learn: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/recordings', methods=['GET'])
def list_all_recordings():
    """Get list of all saved recordings."""
    try:
        recordings = get_all_recordings()
        if not recordings:
            # Non-destructive fallback when DB is not reachable in deployment.
            recordings = load_backup_recordings()
        return jsonify({'recordings': recordings})
    except Exception as e:
        fallback_recordings = load_backup_recordings()
        if fallback_recordings:
            return jsonify({'recordings': fallback_recordings, 'warning': str(e)})
        return jsonify({'error': str(e)}), 500


@app.route('/api/recordings/<recording_id>', methods=['DELETE'])
def delete_recording_endpoint(recording_id):
    """Delete a specific recording."""
    try:
        if delete_recording(recording_id):
            return jsonify({'success': True})
        return jsonify({'error': 'Recording not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/recordings/<recording_id>/audio')
def download_audio(recording_id):
    """Download/play the audio file for a recording."""
    try:
        audio_data, mime_type = get_audio_data(recording_id)
        if not audio_data:
            audio_data, mime_type = get_backup_audio(recording_id)
        
        if not audio_data:
            return jsonify({'error': 'Recording not found'}), 404
        
        return send_file(
            io.BytesIO(audio_data),
            mimetype=mime_type,
            as_attachment=False,
            download_name=f"recording_{recording_id}.webm"
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ======================== ERROR HANDLERS ========================

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return jsonify({'error': 'Page not found'}), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500


# ======================== MAIN ========================

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Starting Super AI Transcript Server (Whisper-only)...")
    print("=" * 60)

    # MySQL may be absent on Hugging Face Spaces; do not crash the whole app.
    try:
        init_db()
    except Exception as db_error:
        print(f"⚠️ Database init skipped: {db_error}")
        print("⚠️ Recording history uses MySQL when available, or backup export on Space.")

    # Start Flask app (Spaces set PORT, e.g. 7860; local default 5000)
    app.run(
        debug=True,
        host='0.0.0.0',  # Allow connections from any IP
        port=int(os.environ.get('PORT', 5000))
    )
