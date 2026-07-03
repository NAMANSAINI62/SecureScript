import os
import json
import sys
import re
import shutil
import subprocess
import requests
import threading
from pathlib import Path
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

WHISPER_MODEL_NAME = 'small'
whisper_model = None

load_dotenv()

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

app = Flask(__name__)
CORS(app)

def get_data_dir() -> str:
    env_dir = os.getenv("PERSIST_DATA_DIR")
    if env_dir and os.path.isdir(env_dir):
        return env_dir
    if os.path.isdir("/data"):
        return "/data"
    return os.path.dirname(__file__)

DATA_DIR = get_data_dir()
UPLOAD_FOLDER = os.path.join(DATA_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def call_ollama(prompt: str, model_name: str = "llama3") -> str:
    try:
        response = requests.post(
            'http://127.0.0.1:11434/api/generate',
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "1h",
                "options": {
                    "temperature": 0.1,
                    "num_ctx": 512,
                    "top_k": 20,
                    "top_p": 0.9
                }
            },
            timeout=180
        )
        if response.status_code == 200:
            return response.json().get("response", "").strip()
    except Exception as e:
        print(f"Ollama error: {str(e)}")
    return None

def call_ai(system_prompt: str, user_message: str) -> str:
    full_prompt = f"INSTRUCTIONS: {system_prompt}\n\nUSER INPUT: {user_message}"
    local_model = os.getenv("OLLAMA_MODEL", "phi3")
    print(f"Calling Ollama model: {local_model}")
    local_response = call_ollama(full_prompt, local_model)
    if local_response:
        return local_response
    print("Ollama failed. Make sure Ollama is running.")
    return "Error: Ollama not running or model not found."

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
    if shutil.which('ffmpeg') is not None:
        return
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
    raise RuntimeError("FFmpeg not found. Install FFmpeg and add it to PATH.")

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
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)
    return text.strip()

@app.route('/')
def home():
    return render_template('index.html')

def preload_models_async():
    try:
        get_whisper_model()
        print("Whisper model preloaded successfully.")
    except Exception as e:
        print(f"Whisper preload error: {e}")
        
    try:
        local_model = os.getenv("OLLAMA_MODEL", "phi3")
        requests.post(
            'http://127.0.0.1:11434/api/generate',
            json={
                "model": local_model,
                "prompt": "warmup",
                "stream": False,
            },
            timeout=15
        )
        print(f"Ollama {local_model} preloaded successfully.")
    except Exception as e:
        print(f"Ollama preload error: {e}")

@app.route('/api/preload', methods=['POST'])
def preload_models():
    threading.Thread(target=preload_models_async, daemon=True).start()
    return jsonify({'status': 'preloading started'})

@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    file_path = None
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        audio_file = request.files['audio']
        filename = audio_file.filename or 'temp.webm'
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        audio_file.save(file_path)
        try:
            ensure_ffmpeg_available()
            model = get_whisper_model()
            print(f"Transcribing with Whisper ({WHISPER_MODEL_NAME})...")
            result = model.transcribe(file_path, language='en', fp16=False)
            transcript = (result.get('text') or '').strip()
            return jsonify({'original_transcript': transcript})
        except Exception as transcribe_error:
            print(f"Transcription error: {str(transcribe_error)}")
            return jsonify({'error': f'Transcription failed: {str(transcribe_error)}'}), 500
        finally:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as cleanup_error:
                    print(f"Cleanup failed: {cleanup_error}")
    except Exception as e:
        print(f"Error in /api/transcribe: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/clean', methods=['POST'])
def clean_text():
    try:
        data = request.get_json() or {}
        text = data.get('text', '').strip()
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        cleaned = call_ai(
            "You are an expert English teacher and language coach. Analyze the user's transcript and generate an English improvement report using these exact steps:\n"
            "STEP 1: Correct the Transcript: Fix speech-to-text errors, spelling, grammar, punctuation, and remove fillers. Preserve original meaning. Do not add new information.\n"
            "STEP 2: Improve the English: Rewrite in natural, fluent, professional, native-like English.\n"
            "STEP 3: Explain Improvements: For each important correction, explain what was wrong, why it was changed, simply for learners.\n"
            "STEP 4: Vocabulary Enhancement: Provide a list of stronger alternatives in the format: Original → Better Alternative.\n"
            "STEP 5: Speaking Practice Version: Create one fluent, easy-to-pronounce practice sentence.\n"
            "STEP 6: English Assessment: Rate Grammar, Vocabulary, Fluency, and Pronunciation Likelihood out of 100. Provide Overall Score and Level (Beginner: 0-20, Elementary: 21-40, Intermediate: 41-60, Upper Intermediate: 61-80, Advanced: 81-100).\n"
            "STEP 7: Personalized Improvement Advice: Top 3 grammar improvements, top 3 vocabulary improvements, top 3 speaking improvements, and one daily exercise.\n\n"
            "You MUST format your output exactly as follows with no introductory or concluding chat text:\n"
            "CORRECTED TRANSCRIPT\n[Corrected version]\n\n"
            "IMPROVED ENGLISH\n[Fluent native-level version]\n\n"
            "CORRECTIONS EXPLAINED\n[Correction 1]\n[Correction 2]\n[Correction 3]\n\n"
            "VOCABULARY UPGRADES\n[Original] → [Improved]\n[Original] → [Improved]\n\n"
            "SPEAKING PRACTICE VERSION\n[Practice sentence]\n\n"
            "ENGLISH ASSESSMENT\n"
            "Grammar: [Score]/100\n"
            "Vocabulary: [Score]/100\n"
            "Fluency: [Score]/100\n"
            "Pronunciation Likelihood: [Score]/100\n"
            "Overall Score: [Score]/100\n"
            "Level: [Level]\n\n"
            "PERSONALIZED IMPROVEMENT PLAN\n"
            "Grammar:\n- [Item 1]\n- [Item 2]\n- [Item 3]\n"
            "Vocabulary:\n- [Item 1]\n- [Item 2]\n- [Item 3]\n"
            "Speaking:\n- [Item 1]\n- [Item 2]\n- [Item 3]\n"
            "Daily Exercise:\n- [Exercise description]",
            text
        )
        if cleaned.startswith("Error"):
            cleaned = (
                f"CORRECTED TRANSCRIPT\n{basic_clean_text(text)}\n\n"
                f"IMPROVED ENGLISH\n{basic_clean_text(text)}\n\n"
                f"CORRECTIONS EXPLAINED\nNo corrections could be processed because Ollama is offline.\n\n"
                f"VOCABULARY UPGRADES\nNone\n\n"
                f"SPEAKING PRACTICE VERSION\n{basic_clean_text(text)}\n\n"
                f"ENGLISH ASSESSMENT\nGrammar: 50/100\nVocabulary: 50/100\nFluency: 50/100\nPronunciation Likelihood: 50/100\nOverall Score: 50/100\nLevel: Intermediate\n\n"
                f"PERSONALIZED IMPROVEMENT PLAN\nGrammar:\n- Practice basic grammar rules.\nVocabulary:\n- Learn new words daily.\nSpeaking:\n- Practice speaking aloud.\nDaily Exercise:\n- Read sentences aloud for 5 minutes."
            )
        return jsonify({'cleaned_transcript': cleaned})
    except Exception as e:
        print(f"Error in /api/clean: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def page_not_found(e):
    return jsonify({'error': 'Page not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("Starting Super AI Transcript Server...")
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
