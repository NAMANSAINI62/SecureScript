let mediaRecorder = null;
let audioChunks = [];
let recordingStartTime = null;
let timerInterval = null;
let audioContext = null;
let analyser = null;
let recordedFile = null;

const recordButton = document.getElementById('recordButton');
const recordPulse = document.getElementById('recordPulse');
const recordingTimer = document.getElementById('recordingTimer');
const timerDisplay = document.getElementById('timerDisplay');
const audioVisualizer = document.getElementById('audioVisualizer');
const visualizerWrap = document.getElementById('visualizerWrap');
const transcribeButton = document.getElementById('transcribeButton');
const originalTranscript = document.getElementById('originalTranscript');
const cleanedTranscript = document.getElementById('cleanedTranscript');
const originalWordCount = document.getElementById('originalWordCount');
const cleanedWordCount = document.getElementById('cleanedWordCount');
const copyCleanedBtn = document.getElementById('copyCleanedBtn');
const cleanButton = document.getElementById('cleanButton');

const loadingOverlay = document.getElementById('loadingOverlay');
const loadingText = document.getElementById('loadingText');
const toastContainer = document.getElementById('toastContainer');

document.addEventListener('DOMContentLoaded', function () {
    setupEventListeners();
    updateButtonStates();
});

async function parseApiResponse(response) {
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
        return await response.json();
    }
    const text = await response.text();
    return { error: `Server returned non-JSON response (${response.status}).`, raw: text };
}

function getApiErrorMessage(response, data, fallbackMessage) {
    if (data && typeof data.error === 'string' && data.error.trim()) {
        return data.error;
    }
    return `${fallbackMessage} (HTTP ${response.status})`;
}

function setupEventListeners() {
    recordButton.addEventListener('click', toggleRecording);
    transcribeButton.addEventListener('click', transcribeAudio);
    cleanButton.addEventListener('click', cleanTranscript);
    originalTranscript.addEventListener('input', () => {
        updateWordCount(originalTranscript, originalWordCount);
        updateButtonStates();
    });
    copyCleanedBtn.addEventListener('click', copyCleanedTranscript);

}

async function toggleRecording() {
    const isRecording = recordButton.dataset.recording === 'true';
    if (!isRecording) {
        await startRecording();
    } else {
        stopRecording();
    }
}

async function startRecording() {
    try {
        // Fire preload request asynchronously in the background so models warm up
        fetch('/api/preload', { method: 'POST' }).catch(err => console.log('Preload error:', err));

        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 44100
            }
        });

        mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = handleRecordingComplete;
        mediaRecorder.start(1000);

        recordButton.dataset.recording = 'true';
        recordButton.querySelector('.btn-text').textContent = 'Stop Recording';
        recordButton.querySelector('.btn-icon').textContent = '⏹';
        recordButton.classList.add('recording');
        recordPulse.classList.add('active');

        recordingStartTime = Date.now();
        recordingTimer.classList.remove('hidden');
        timerInterval = setInterval(updateRecordingTimer, 1000);

        setupAudioVisualization(stream);
        showToast('Recording started...', 'info');

    } catch (error) {
        if (error.name === 'NotAllowedError') {
            showToast('Microphone access denied. Please allow microphone access.', 'error');
        } else if (error.name === 'NotFoundError') {
            showToast('No microphone found. Please connect a microphone.', 'error');
        } else {
            showToast('Error starting recording: ' + error.message, 'error');
        }
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
    recordButton.dataset.recording = 'false';
    recordButton.querySelector('.btn-text').textContent = 'Start Recording';
    recordButton.querySelector('.btn-icon').textContent = '⏺';
    recordButton.classList.remove('recording');
    recordPulse.classList.remove('active');
    clearInterval(timerInterval);
    visualizerWrap.classList.add('hidden');
}

async function handleRecordingComplete() {
    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
    recordedFile = new File([audioBlob], `recording_${Date.now()}.webm`, { type: 'audio/webm' });
    recordingTimer.classList.add('hidden');
    showToast('Recording complete! Processing transcription...', 'success');
    await transcribeAudio();
}

function updateRecordingTimer() {
    const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
    const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
    const seconds = (elapsed % 60).toString().padStart(2, '0');
    timerDisplay.textContent = `${minutes}:${seconds}`;
}

function setupAudioVisualization(stream) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;
    const source = audioContext.createMediaStreamSource(stream);
    source.connect(analyser);
    visualizerWrap.classList.remove('hidden');
    drawVisualization();
}

function drawVisualization() {
    if (!analyser) return;
    const canvas = audioVisualizer;
    const ctx = canvas.getContext('2d');
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    function draw() {
        if (recordButton.dataset.recording !== 'true') return;
        requestAnimationFrame(draw);
        analyser.getByteFrequencyData(dataArray);

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const barWidth = Math.max(2, (canvas.width / bufferLength) * 2);
        const gap = 2;
        let x = 0;
        for (let i = 0; i < bufferLength; i++) {
            const ratio = dataArray[i] / 255;
            const barHeight = ratio * canvas.height;
            // Gradient color per bar from purple to pink based on amplitude
            const r = Math.round(102 + ratio * 143);
            const g = Math.round(126 - ratio * 89);
            const b = Math.round(234 - ratio * 120);
            ctx.fillStyle = `rgb(${r},${g},${b})`;
            // Draw bar from bottom center
            ctx.beginPath();
            ctx.roundRect(x, canvas.height - barHeight, barWidth, barHeight, 2);
            ctx.fill();
            x += barWidth + gap;
        }
    }
    draw();
}

async function transcribeAudio() {
    if (!recordedFile) {
        showToast('No recording found. Please record audio first.', 'error');
        return;
    }
    const formData = new FormData();
    formData.append('audio', recordedFile);
    showLoading('Transcribing audio with Whisper...');
    try {
        const response = await fetch('/api/transcribe', { method: 'POST', body: formData });
        const data = await parseApiResponse(response);
        if (response.ok) {
            originalTranscript.value = data.original_transcript || '';
            updateWordCount(originalTranscript, originalWordCount);
            updateButtonStates();
            showToast('Transcription complete!', 'success');
        } else {
            throw new Error(getApiErrorMessage(response, data, 'Transcription failed'));
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function cleanTranscript() {
    const text = originalTranscript.value.trim();
    if (!text) {
        showToast('No text to clean', 'error');
        return;
    }
    cleanButton.disabled = true;
    try {
        const response = await fetch('/api/clean', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        });
        const data = await parseApiResponse(response);
        if (response.ok) {
            const report = parseImprovementReport(data.cleaned_transcript);
            cleanedTranscript.value = report.corrected || data.cleaned_transcript;
            updateWordCount(cleanedTranscript, cleanedWordCount);
            updateButtonStates();
            renderImprovementReport(data.cleaned_transcript);
            showToast('Cleaned successfully with Ollama!', 'success');
        } else {
            throw new Error(getApiErrorMessage(response, data, 'Cleaning failed'));
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    } finally {
        cleanButton.disabled = false;
    }
}

function parseImprovementReport(text) {
    const sections = {
        corrected: '',
        improved: '',
        explanations: [],
        vocab: [],
        speaking: '',
        assessment: { grammar: '0', vocabulary: '0', fluency: '0', pronunciation: '0', overall: '0', level: 'N/A' },
        advice: { grammar: [], vocabulary: [], speaking: [], exercise: '' }
    };
    const lines = text.split('\n');
    let currentSection = '';
    let adviceSubSection = '';
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        if (!line) continue;
        let upperLine = line.toUpperCase();
        if (upperLine.startsWith('CORRECTED TRANSCRIPT')) {
            currentSection = 'corrected';
            continue;
        } else if (upperLine.startsWith('IMPROVED ENGLISH')) {
            currentSection = 'improved';
            continue;
        } else if (upperLine.startsWith('CORRECTIONS EXPLAINED')) {
            currentSection = 'explanations';
            continue;
        } else if (upperLine.startsWith('VOCABULARY UPGRADES')) {
            currentSection = 'vocab';
            continue;
        } else if (upperLine.startsWith('SPEAKING PRACTICE VERSION')) {
            currentSection = 'speaking';
            continue;
        } else if (upperLine.startsWith('ENGLISH ASSESSMENT')) {
            currentSection = 'assessment';
            continue;
        } else if (upperLine.startsWith('PERSONALIZED IMPROVEMENT PLAN') || upperLine.startsWith('PERSONALIZED IMPROVEMENT ADVICE')) {
            currentSection = 'advice';
            continue;
        }
        if (currentSection === 'corrected') {
            sections.corrected += (sections.corrected ? '\n' : '') + line;
        } else if (currentSection === 'improved') {
            sections.improved += (sections.improved ? '\n' : '') + line;
        } else if (currentSection === 'explanations') {
            sections.explanations.push(line);
        } else if (currentSection === 'vocab') {
            sections.vocab.push(line);
        } else if (currentSection === 'speaking') {
            sections.speaking += (sections.speaking ? '\n' : '') + line;
        } else if (currentSection === 'assessment') {
            let parts = line.split(':');
            if (parts.length >= 2) {
                let key = parts[0].trim().toLowerCase();
                let val = parts[1].trim();
                if (key.includes('grammar')) sections.assessment.grammar = val.replace('/100', '').trim();
                else if (key.includes('vocabulary')) sections.assessment.vocabulary = val.replace('/100', '').trim();
                else if (key.includes('fluency')) sections.assessment.fluency = val.replace('/100', '').trim();
                else if (key.includes('pronunciation')) sections.assessment.pronunciation = val.replace('/100', '').trim();
                else if (key.includes('overall')) sections.assessment.overall = val.replace('/100', '').trim();
                else if (key.includes('level')) sections.assessment.level = val;
            }
        } else if (currentSection === 'advice') {
            if (line.toLowerCase().startsWith('grammar:')) {
                adviceSubSection = 'grammar';
            } else if (line.toLowerCase().startsWith('vocabulary:')) {
                adviceSubSection = 'vocabulary';
            } else if (line.toLowerCase().startsWith('speaking:')) {
                adviceSubSection = 'speaking';
            } else if (line.toLowerCase().startsWith('daily exercise:') || line.toLowerCase().startsWith('exercise:')) {
                adviceSubSection = 'exercise';
            } else if (line.startsWith('-') || line.startsWith('*')) {
                let item = line.substring(1).trim();
                if (adviceSubSection === 'grammar') sections.advice.grammar.push(item);
                else if (adviceSubSection === 'vocabulary') sections.advice.vocabulary.push(item);
                else if (adviceSubSection === 'speaking') sections.advice.speaking.push(item);
                else if (adviceSubSection === 'exercise') sections.advice.exercise += (sections.advice.exercise ? ' ' : '') + item;
            } else {
                if (adviceSubSection === 'exercise') sections.advice.exercise += (sections.advice.exercise ? ' ' : '') + line;
            }
        }
    }
    return sections;
}

function renderImprovementReport(reportText) {
    const report = parseImprovementReport(reportText);

    document.getElementById('rptCorrected').textContent = report.corrected || 'N/A';
    document.getElementById('rptImproved').textContent = report.improved || 'N/A';

    document.getElementById('rptGrammarScore').textContent = report.assessment.grammar + '/100';
    document.getElementById('rptGrammarBar').style.width = report.assessment.grammar + '%';
    document.getElementById('rptVocabScore').textContent = report.assessment.vocabulary + '/100';
    document.getElementById('rptVocabBar').style.width = report.assessment.vocabulary + '%';
    document.getElementById('rptFluencyScore').textContent = report.assessment.fluency + '/100';
    document.getElementById('rptFluencyBar').style.width = report.assessment.fluency + '%';
    document.getElementById('rptPronScore').textContent = report.assessment.pronunciation + '/100';
    document.getElementById('rptPronBar').style.width = report.assessment.pronunciation + '%';
    document.getElementById('rptOverallScore').textContent = report.assessment.overall + '/100';
    document.getElementById('rptLevel').textContent = report.assessment.level;

    document.getElementById('rptSpeaking').textContent = '💬 "' + (report.speaking || 'N/A') + '"';

    const expList = document.getElementById('rptExplanations');
    expList.innerHTML = '';
    if (report.explanations.length === 0) {
        expList.innerHTML = '<li>No major corrections required. Great job!</li>';
    } else {
        report.explanations.forEach(c => {
            const li = document.createElement('li');
            li.textContent = c;
            expList.appendChild(li);
        });
    }

    const vocabBody = document.getElementById('rptVocabTable');
    vocabBody.innerHTML = '';
    if (report.vocab.length === 0) {
        vocabBody.innerHTML = '<tr><td colspan="3">No specific vocabulary upgrades suggested.</td></tr>';
    } else {
        report.vocab.forEach(v => {
            const parts = v.split('→');
            const tr = document.createElement('tr');
            if (parts.length >= 2) {
                tr.innerHTML = `<td><strong>${escapeHtml(parts[0].trim())}</strong></td><td>➡️</td><td><span class="badge-success">${escapeHtml(parts[1].trim())}</span></td>`;
            } else {
                tr.innerHTML = `<td colspan="3">${escapeHtml(v)}</td>`;
            }
            vocabBody.appendChild(tr);
        });
    }

    const fillList = (id, items) => {
        const el = document.getElementById(id);
        el.innerHTML = '';
        items.forEach(a => {
            const li = document.createElement('li');
            li.textContent = a;
            el.appendChild(li);
        });
    };
    fillList('rptAdviceGrammar', report.advice.grammar);
    fillList('rptAdviceVocab', report.advice.vocabulary);
    fillList('rptAdviceSpeaking', report.advice.speaking);
    document.getElementById('rptExercise').textContent = report.advice.exercise || '';

    document.getElementById('improvementReportCard').classList.remove('hidden');
}

async function copyCleanedTranscript() {
    const text = cleanedTranscript.value;
    if (!text) {
        showToast('No text to copy', 'error');
        return;
    }
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copied to clipboard!', 'success');
    } catch (error) {
        showToast('Failed to copy', 'error');
    }
}

function updateWordCount(textarea, countElement) {
    const text = textarea.value.trim();
    const wordCount = text ? text.split(/\s+/).length : 0;
    countElement.textContent = `${wordCount} words`;
}

function updateButtonStates() {
    const hasOriginal = originalTranscript.value.trim().length > 0;
    cleanButton.disabled = !hasOriginal;
}

function showLoading(message = 'Processing...') {
    loadingText.textContent = message;
    loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
    loadingOverlay.classList.add('hidden');
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
