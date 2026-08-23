from __future__ import annotations

import base64
import os
from pathlib import Path

import requests


API_ROOT = "https://api.elevenlabs.io/v1"
VOICE_NAME = "Jenny_Korean_Shorts"
VOICE_DESCRIPTION = (
    "A magnetic and trustworthy Korean female narrator in her late thirties. "
    "She has crisp standard Seoul Korean pronunciation, a warm premium tone, "
    "confident delivery, and a natural conversational rhythm. Her opening lines "
    "create immediate curiosity for viral YouTube Shorts without sounding loud, "
    "salesy, childish, robotic, or overly cheerful. She sounds intelligent, modern, "
    "friendly, and authoritative, ideal for consumer fact-checking and practical "
    "money-saving stories."
)
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


def main() -> None:
    configured_voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
    if configured_voice_id:
        VOICE_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
        VOICE_ID_FILE.write_text(configured_voice_id + "\n", encoding="utf-8")
        print("Using the existing ELEVENLABS_VOICE_ID secret.")
        return

    if VOICE_ID_FILE.exists() and VOICE_ID_FILE.read_text(encoding="utf-8").strip():
        print("The generated ElevenLabs voice is already configured.")
        return

    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is required")

    design_response = requests.post(
        f"{API_ROOT}/text-to-voice/design",
        headers=_headers(api_key),
        json={
            "voice_description": VOICE_DESCRIPTION,
            "text": PREVIEW_TEXT,
            "auto_generate_text": False,
            "quality": 0.95,
            "guidance_scale": 4.0,
            "seed": 47035105,
        },
        timeout=180,
    )
    design_response.raise_for_status()
    previews = design_response.json().get("previews", [])
    if not previews:
        raise RuntimeError("ElevenLabs returned no voice previews")

    # The prompt tightly specifies the desired production voice. Select the first
    # high-quality result deterministically so setup is fully automatic.
    selected = previews[0]
    generated_voice_id = selected["generated_voice_id"]

    PREVIEW_FILE.parent.mkdir(parents=True, exist_ok=True)
    PREVIEW_FILE.write_bytes(base64.b64decode(selected["audio_base_64"]))

    create_response = requests.post(
        f"{API_ROOT}/text-to-voice",
        headers=_headers(api_key),
        json={
            "voice_name": VOICE_NAME,
            "voice_description": VOICE_DESCRIPTION,
            "generated_voice_id": generated_voice_id,
            "labels": {
                "language": "ko",
                "gender": "female",
                "use_case": "social_media",
            },
        },
        timeout=180,
    )
    create_response.raise_for_status()
    voice_id = create_response.json()["voice_id"]

    VOICE_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
    VOICE_ID_FILE.write_text(voice_id + "\n", encoding="utf-8")
    print(f"Created and configured ElevenLabs voice: {VOICE_NAME}")


if __name__ == "__main__":
    main()
