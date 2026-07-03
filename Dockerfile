# Beginner-friendly Dockerfile for Super AI Transcript
# Uses Python slim base, installs ffmpeg and Python deps

FROM python:3.11.13-slim-bullseye

# Install system dependencies (ffmpeg for audio processing)
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
     && apt-get install -y --no-install-recommends \
         ffmpeg \
         build-essential \
         libsndfile1 \
     && apt-get clean \
     && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy requirements and install
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r /app/requirements.txt

# Copy application
COPY . /app

# Create uploads dir
RUN mkdir -p /app/uploads

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Default: do NOT enable Whisper local mode to keep image smaller.
# To enable local Whisper transcription set environment variable WHISPER_LOCAL=1
# and optionally WHISPER_MODEL (tiny, base, small, medium, large).

# Local Docker default is PORT=5000; Hugging Face Spaces sets PORT (often 7860).
EXPOSE 7860
CMD ["python", "app.py"]
