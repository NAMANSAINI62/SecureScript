# Google Cloud Speech-to-Text Setup Guide

This project uses **Google Cloud Speech-to-Text API** for audio transcription (instead of Whisper). This works seamlessly on Hugging Face Spaces without Docker.

---

## 🔧 Setup Steps (5 minutes)

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click **"Select a Project"** → **"NEW PROJECT"**
3. Name it: `super-ai-transcript`
4. Click **"Create"**

---

### Step 2: Enable Speech-to-Text API

1. In the console, go to **"APIs & Services"** → **"Library"**
2. Search for **"Cloud Speech-to-Text API"**
3. Click on it and then click **"ENABLE"**

---

### Step 3: Create a Service Account

1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"+ CREATE CREDENTIALS"** → **"Service Account"**
3. Fill in:
   - **Service account name**: `speech-to-text`
   - **Description**: Audio transcription service
4. Click **"CREATE AND CONTINUE"**

---

### Step 4: Grant Permissions

1. Click **"Continue"** (or select the service account and edit it)
2. Click **"GRANT ROLES"**
3. Search for and select: **"Editor"**
4. Click **"Continue"**
5. Click **"DONE"**

---

### Step 5: Create and Download Key

1. Go to **"APIs & Services"** → **"Credentials"**
2. Find your service account and click on it
3. Go to **"KEYS"** tab
4. Click **"ADD KEY"** → **"Create new key"**
5. Select **"JSON"** and click **"CREATE"**
6. A JSON file will download automatically

---

### Step 6: Add to Your Project

#### Local Development:

1. Rename the downloaded file to `google-cloud-key.json`
2. Place it in your project root folder (same level as `app.py`)
3. Add to `.env` file:
   ```
   GOOGLE_APPLICATION_CREDENTIALS=./google-cloud-key.json
   ```

#### Hugging Face Spaces:

1. Go to your Space settings
2. Click **"Variables and secrets"**
3. Add a **secret** named `GOOGLE_APPLICATION_CREDENTIALS`
4. Copy the entire JSON file content and paste it as the value

---

## 💾 Install Package

```bash
pip install google-cloud-speech==2.23.0
```

Or if installing from scratch:

```bash
pip install -r requirements.txt
```

---

## 🚀 Test It

1. Update `.env` with your credentials
2. Run the app:
   ```bash
   python app.py
   ```
3. Upload an audio file and test the transcription

---

## ⚙️ How It Works

1. **Audio Upload** → Saved to disk and database
2. **Google Cloud API Call** → Converts audio to text
3. **Transcript Stored** → In database and returned to frontend
4. **AI Processing** → Gemini AI cleans, summarizes, etc.

---

## 🔐 Security Notes

- **Keep your key secret!** Never commit to Git
- `.env` is in `.gitignore` - it won't be pushed
- For Spaces, use **Secrets** (not Environment Variables)
- Rotate keys periodically for security

---

## 💰 Cost

- **First 60 minutes/month**: Free
- **After that**: ~$0.04 per 15 seconds of audio
- Check pricing at: https://cloud.google.com/speech-to-text/pricing

---

## 🆘 Troubleshooting

### Error: "GOOGLE_APPLICATION_CREDENTIALS not set"

→ Make sure `.env` file exists and has the correct path

### Error: "Service account key not found"

→ Check that the JSON file path is correct

### Error: "API not enabled"

→ Go to Cloud Console and enable "Speech-to-Text API"

### Error: "Quota exceeded"

→ Your free tier limit is used up. Check quotas in Cloud Console

---

## 📚 Resources

- [Google Cloud Speech-to-Text Docs](https://cloud.google.com/speech-to-text/docs)
- [Authentication Guide](https://cloud.google.com/docs/authentication/getting-started)
- [API Reference](https://cloud.google.com/speech-to-text/docs/reference/rest)

---

**Done! Your transcription is now powered by Google Cloud.** ☁️
