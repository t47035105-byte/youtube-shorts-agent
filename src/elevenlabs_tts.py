from __future__ import annotations

import os
from pathlib import Path


DEFAULT_VOICE_ID_FILE = Path("config/elevenlabs_voice_id.txt")


def resolve_voice_id() -> str:
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
    if voice_id:
        return voice_id

    voice_id_file = Path(
        os.environ.get("ELEVENLABS_VOICE_ID_FILE", str(DEFAULT_VOICE_ID_FILE))
    )
    if voice_id_file.exists():
        voice_id = voice_id_file.read_text(encoding="utf-8").strip()
        if voice_id:
            return voice_id

    raise RuntimeError(
        "ELEVENLABS_VOICE_ID is required, or run the ElevenLabs voice setup workflow"
    )


def synthesize(text: str, output_path: Path) -> Path:
    import requests

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    voice_id = resolve_voice_id()
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is required")

    endpoint = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    response = requests.post(
        endpoint,
        params={"output_format": "mp3_44100_128"},
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        json={
            "text": text,
            "model_id": os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
            "voice_settings": {
                "stability": 0.42,
                "similarity_boost": 0.78,
                "style": 0.18,
                "use_speaker_boost": True,
            },
        },
        timeout=180,
    )
    response.raise_for_status()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    return output_path
