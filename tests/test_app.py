"""API tests with Groq and gTTS mocked, so they run offline and for free."""
import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend import app as storyforge


class FakeGroq:
    def __init__(self):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._chat))
        self.audio = SimpleNamespace(transcriptions=SimpleNamespace(create=self._transcribe))

    def _chat(self, **kwargs):
        msg = SimpleNamespace(content="  Once upon a time, a dragon learned to sing.  ")
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    def _transcribe(self, file, model):
        return SimpleNamespace(text=" dragon ")


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(storyforge, "groq_client", FakeGroq())
    monkeypatch.setattr(storyforge, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(storyforge, "narrate", lambda text, path: open(path, "wb").write(b"ID3"))
    return TestClient(storyforge.app)


def test_generate_story_returns_playable_audio(client):
    res = client.post("/generate_story", json={"keyword": "dragon", "length": "short"})
    assert res.status_code == 200
    body = res.json()
    assert body["story"] == "Once upon a time, a dragon learned to sing."
    audio = client.get(body["mp3_url"])
    assert audio.status_code == 200
    assert audio.headers["content-type"] == "audio/mpeg"


@pytest.mark.parametrize("payload", [{"keyword": ""}, {"keyword": "x" * 101}, {"keyword": "a", "length": "epic"}])
def test_generate_story_rejects_bad_input(client, payload):
    assert client.post("/generate_story", json=payload).status_code == 422


def test_transcribe_returns_text(client):
    res = client.post("/transcribe", files={"file": ("recording.webm", b"fake-audio", "audio/webm")})
    assert res.status_code == 200
    assert res.json() == {"text": "dragon"}


def test_transcribe_rejects_empty_upload(client):
    res = client.post("/transcribe", files={"file": ("recording.webm", b"", "audio/webm")})
    assert res.status_code == 400


@pytest.mark.parametrize("name", ["..%2Fapp.py", "notes.txt", "abc.mp3"])
def test_audio_route_only_serves_generated_files(client, name):
    assert client.get(f"/audio/{name}").status_code == 404


def test_missing_api_key_returns_503(monkeypatch):
    monkeypatch.setattr(storyforge, "groq_client", None)
    res = TestClient(storyforge.app).post("/generate_story", json={"keyword": "dragon"})
    assert res.status_code == 503


def test_frontend_and_health(client):
    assert client.get("/").status_code == 200
    assert client.get("/health").json()["status"] == "ok"
