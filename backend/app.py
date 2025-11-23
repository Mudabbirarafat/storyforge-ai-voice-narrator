import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydub import AudioSegment
from gtts import gTTS
import aiofiles

# ---------- GROQ (FREE LLM) ----------
from groq import Groq

app = FastAPI(title="StoryForge Backend")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Output directory for generated mp3 files
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "generated")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load Groq API key
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("⚠️ GROQ_API_KEY not found! Set it with: setx GROQ_API_KEY \"your_key\"")

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY)


# -----------------------------
# Transcription (optional later)
# -----------------------------
@app.post('/transcribe')
async def transcribe(file: UploadFile = File(...)):
    """ 
    Placeholder for ASR. Returns empty text so frontend can use typed input. 
    """
    return {"text": ""}


# -----------------------------
# Build LLM Prompt
# -----------------------------
def build_prompt(keyword: str, length: str = "medium"):
    mapping = {"short": 180, "medium": 320, "long": 550}
    target_words = mapping.get(length, 320)

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


# -----------------------------
# Story Generator using GROQ
# -----------------------------
@app.post('/generate_story')
async def generate_story(payload: dict):
    keyword = payload.get("keyword", "").strip()
    length = payload.get("length", "medium")

    if not keyword:
        raise HTTPException(status_code=400, detail="Keyword is required")

    prompt = build_prompt(keyword, length)

    # ----- Generate Story using Groq llama-3.3-70b-versatile -----
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",   # UPDATED MODEL
            messages=[{"role": "user", "content": prompt}],
            max_tokens=900,
            temperature=0.9,
        )
        story_text = response.choices[0].message.content.strip()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Groq LLM Generation Failed: {e}")

    # ----- Convert Story to Speech -----
    filename = f"{uuid.uuid4().hex}.mp3"
    filepath = os.path.join(OUTPUT_DIR, filename)

    try:
        tts = gTTS(text=story_text, lang="en")
        tts.save(filepath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {e}")

    return {"mp3_url": f"/audio/{filename}"}


# -----------------------------
# Serve Audio Files
# ------------
@app.get('/audio/{filename}')
async def serve_audio(filename: str):
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(path, media_type="audio/mpeg", filename=filename)


# -----------------------------
# Serve Frontend (FIXED VERSION)
# -----------------------------
@app.get("/")
async def root():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Navigate to ../frontend/index.html
    frontend_path = os.path.abspath(
        os.path.join(base_dir, "..", "frontend", "index.html")
    )

    print("📄 Serving frontend from:", frontend_path)

    if not os.path.exists(frontend_path):
        raise HTTPException(status_code=500, detail="Frontend index.html not found")

    return FileResponse(frontend_path, media_type="text/html")
