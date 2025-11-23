🎙️ StoryForge — AI-Powered Voice Story Narrator

A modern, voice-controlled storytelling app with a beautiful glassmorphism UI, animated particles, and real-time audio generation.

🚀 Overview

StoryForge is a full-stack demo application that:

Captures a voice keyword from the user

Transcribes it (optional — manual input supported)

Generates a cinematic story using an LLM

Converts the story into speech (TTS)

Streams the MP3 back into a custom audio player

It includes:

🧠 FastAPI backend (Python)

🖥️ Advanced glassmorphism frontend (HTML + CSS + JS)

🎙️ Voice recording & waveform animation

🌗 Dark/Light theme toggle (saved in localStorage)

✨ Animated background particle system

🔊 Modern custom audio player

🗣️ gTTS for TTS (backend unchanged)

No backend modifications required — runs exactly as shipped.

⭐ Features
🖥️ Frontend

Beautiful glassmorphism UI

Soft gradient background + animated particles

Animated mic button with pulse effect

Real-time waveform animation

Custom modern audio player (play, pause, download, progress)

Theme toggle (light/dark) — remembers user preference

SVG branding logo included

Fully mobile-responsive

Works without any API key (manual input mode)

⚙️ Backend

FastAPI server

/transcribe endpoint (optional Whisper support)

/generate_story using your LLM (Groq/OpenAI/etc.)

gTTS-based MP3 generation

Static audio serving via /audio/...

Your backend works as-is — no changes needed.

🧩 Project Structure
storyforge_project/
│
├── backend/
│   └── app.py           # FastAPI backend (unchanged)
│
├── frontend/
│   └── index.html       # Fully upgraded UI
│
├── requirements.txt
├── LICENSE
└── README.md

⚡ Quick Start
1️⃣ Create virtual environment
python -m venv venv
source venv/bin/activate        # mac/linux
venv\Scripts\activate           # windows

2️⃣ Install dependencies
pip install -r requirements.txt

3️⃣ Start backend
uvicorn backend.app:app --reload --port 8000

4️⃣ Open frontend

Simply open:

frontend/index.html


Or visit:

http://127.0.0.1:8000/

📡 API Endpoints (Backend)
🔹 POST /transcribe

Accepts:

multipart/form-data: file=<audio>


Returns:

{ "text": "keyword" }

🔹 POST /generate_story

Accepts:

{ "keyword": "dragon", "length": "short|medium|long" }


Returns:

{ "mp3_url": "/audio/<file>.mp3" }

🔹 GET /audio/<filename>

Direct MP3 file serving.

🛠️ How It Works Internally (Simple)

User records keyword → browser captures audio

Audio sent to /transcribe

Resulting keyword (or manual input) sent to /generate_story

Backend:

Generates story with LLM

Converts story → MP3 (gTTS)

MP3 streamed back to custom audio player

User hears narrated story

🔧 Extending the Project

You can upgrade the backend to support:

✔ Higher-quality TTS

Coqui TTS

Amazon Polly

ElevenLabs

Azure TTS

✔ Better ASR

Whisper (OpenAI)

Whisper.cpp (local)

Vosk (offline)

✔ Story modes

Choose genre

Choose narrator voice

Multi-scene stories

Story continuation

✔ Real-time streaming

Streaming LLM output → streaming TTS

Ask anytime if you want help adding any of these.

📄 License

MIT License — free to use, modify, and distribute.