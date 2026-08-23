from __future__ import annotations

import os
from pathlib import Path

import requests


API_ROOT = "https://api.elevenlabs.io/v1"
DEFAULT_VOICE_ID = "7GJLtfswFrmju7j66Puy"
DEFAULT_VOICE_NAME = "제니 쇼츠 진행자"
PREVIEW_TEXT = (
    "잠깐만요. 매달 무심코 빠져나가는 이 돈, 정말 그만한 가치가 있을까요? "
    "광고 문구는 잠시 내려놓고 가격과 혜택, 실제 사용 조건을 하나씩 확인해 보겠습니다. "
    "끝까지 보시면 무엇을 남기고 무엇을 끊어야 하는지 분명해집니다. "
    "복잡한 설명은 빼고, 생활비를 지키는 핵심만 정확하고 쉽게 알려드릴게요."
)
VOICE_ID_FILE = Path("config/elevenlabs_voice_id.txt")
PREVIEW_FILE = Path("output/voice-preview-jenny-korean-shorts.mp3")


def _headers(api_key: str) -> dict[str, str]:
    return {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }


def _create_preview(api_key: str, voice_id: str) -> bytes:
    response = requests.post(
        f"{API_ROOT}/text-to-speech/{voice_id}",
        params={"output_format": "mp3_44100_128"},
        headers={
            **_headers(api_key),
            "Accept": "audio/mpeg",
        },
        json={
            "text": PREVIEW_TEXT,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.42,
                "similarity_boost": 0.78,
                "style": 0.18,
                "use_speaker_boost": True,
            },
        },
        timeout=180,
    )
    if not response.ok:
        raise RuntimeError(
            f"ElevenLabs TTS failed ({response.status_code}): {response.text}"
        )
    return response.content


def main() -> None:
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is required")

    configured_voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
    saved_voice_id = (
        VOICE_ID_FILE.read_text(encoding="utf-8").strip()
        if VOICE_ID_FILE.exists()
        else ""
    )
    voice_id = configured_voice_id or saved_voice_id or DEFAULT_VOICE_ID
    voice_name = (
        "ELEVENLABS_VOICE_ID secret"
        if configured_voice_id
        else DEFAULT_VOICE_NAME
    )

    PREVIEW_FILE.parent.mkdir(parents=True, exist_ok=True)
    PREVIEW_FILE.write_bytes(_create_preview(api_key, voice_id))

    VOICE_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
    VOICE_ID_FILE.write_text(voice_id + "\n", encoding="utf-8")
    print(f"Configured ElevenLabs Shorts voice: {voice_name}")


if __name__ == "__main__":
    main()
