import os
import re
import uuid
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from gtts import gTTS
from groq import Groq
from pydantic import BaseModel, Field

STORY_MODEL = os.environ.get("STORY_MODEL", "llama-3.3-70b-versatile")
TRANSCRIBE_MODEL = os.environ.get("TRANSCRIBE_MODEL", "whisper-large-v3-turbo")
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB is plenty for a spoken keyword
TARGET_WORDS = {"short": 180, "medium": 320, "long": 550}

app = FastAPI(title="StoryForge Backend")

# Allowed origins come from the environment (comma-separated). The frontend is
# normally served by this same app, so cross-origin access is only for local dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "http://localhost:8000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Output directory for generated mp3 files
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "generated")
os.makedirs(OUTPUT_DIR, exist_ok=True)
AUDIO_NAME = re.compile(r"^[0-9a-f]{32}\.mp3$")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("GROQ_API_KEY is not set: /generate_story and /transcribe will return 503")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def require_llm() -> Groq:
    if groq_client is None:
        raise HTTPException(status_code=503, detail="Server is missing GROQ_API_KEY")
    return groq_client


class StoryRequest(BaseModel):
    keyword: str = Field(min_length=1, max_length=100)
    length: Literal["short", "medium", "long"] = "medium"


# -----------------------------
# Speech-to-text (Whisper via Groq)
# -----------------------------
@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    client = require_llm()
    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=400, detail="Empty audio upload")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio file too large")

    try:
        result = await run_in_threadpool(
            client.audio.transcriptions.create,
            file=(file.filename or "recording.webm", audio),
            model=TRANSCRIBE_MODEL,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Transcription failed: {e}")

    return {"text": result.text.strip()}


# -----------------------------
# Build LLM Prompt
# -----------------------------
def build_prompt(keyword: str, length: str = "medium"):
    target_words = TARGET_WORDS.get(length, 320)

    prompt = f"""
Write a vivid, immersive narrated story inspired by the keyword: "{keyword}".

Requirements:
- Around {target_words} words
- Strong hook in the first 2 sentences
- Clear setting, protagonist, conflict, and resolution
- Cinematic narration style
- No meta comments, no lists
Just return the story text.
"""
    return prompt


def write_story(client: Groq, prompt: str) -> str:
    response = client.chat.completions.create(
        model=STORY_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=900,
        temperature=0.9,
    )
    return response.choices[0].message.content.strip()


def narrate(text: str, filepath: str) -> None:
    gTTS(text=text, lang="en").save(filepath)


# -----------------------------
# Story Generator
# -----------------------------
@app.post("/generate_story")
async def generate_story(req: StoryRequest):
    client = require_llm()
    keyword = req.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="Keyword is required")

    # The Groq and gTTS clients are blocking, so run them off the event loop
    # to keep the server responsive while a story is being generated.
    try:
        story_text = await run_in_threadpool(write_story, client, build_prompt(keyword, req.length))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Story generation failed: {e}")

    filename = f"{uuid.uuid4().hex}.mp3"
    try:
        await run_in_threadpool(narrate, story_text, os.path.join(OUTPUT_DIR, filename))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Text-to-speech failed: {e}")

    return {"mp3_url": f"/audio/{filename}", "story": story_text}


# -----------------------------
# Serve Audio Files
# -----------------------------
@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    # Only serve files this app generated (uuid4 hex names), never arbitrary paths
    if not AUDIO_NAME.match(filename):
        raise HTTPException(status_code=404, detail="Audio not found")
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(path, media_type="audio/mpeg", filename=filename)


@app.get("/health")
async def health():
    return {"status": "ok", "llm_configured": groq_client is not None}


# -----------------------------
# Serve Frontend
# -----------------------------
@app.get("/")
async def root():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_path = os.path.abspath(os.path.join(base_dir, "..", "frontend", "index.html"))
    if not os.path.exists(frontend_path):
        raise HTTPException(status_code=500, detail="Frontend index.html not found")
    return FileResponse(frontend_path, media_type="text/html")
