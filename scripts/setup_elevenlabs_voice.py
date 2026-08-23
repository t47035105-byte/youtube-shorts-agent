from __future__ import annotations

import os
from pathlib import Path

import requests


API_ROOT = "https://api.elevenlabs.io/v1"
VOICE_SEARCH_URL = "https://api.elevenlabs.io/v2/voices"
PREFERRED_DEFAULT_VOICES = (
    "Jessica",
    "Matilda",
    "Sarah",
    "Talia",
    "Elara",
    "Florence",
    "Clara",
    "Janet",
    "Riley",
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


def _list_default_voices(api_key: str) -> list[dict]:
    params = {
        "voice_type": "default",
        "page_size": 100,
        "sort": "name",
        "sort_direction": "asc",
        "include_total_count": "false",
    }
    response = requests.get(
        VOICE_SEARCH_URL,
        headers={"xi-api-key": api_key},
        params=params,
        timeout=60,
    )

    # A restricted API key can allow Text to Speech while denying voice-list
    # access. Default voices are public, so retry without the restricted key.
    if response.status_code in {401, 403}:
        response = requests.get(VOICE_SEARCH_URL, params=params, timeout=60)

    response.raise_for_status()
    voices = response.json().get("voices", [])
    if not voices:
        raise RuntimeError("ElevenLabs returned no free default voices")
    return voices


def _choose_default_voice(voices: list[dict]) -> dict:
    for preferred_name in PREFERRED_DEFAULT_VOICES:
        for voice in voices:
            display_name = str(voice.get("name", ""))
            base_name = display_name.split(" - ", 1)[0]
            if base_name.casefold() == preferred_name.casefold():
                return voice

    female_voices = [
        voice
        for voice in voices
        if str(voice.get("labels", {}).get("gender", "")).casefold() == "female"
    ]
    if female_voices:
        return female_voices[0]
    return voices[0]


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
    response.raise_for_status()
    return response.content


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

    selected = _choose_default_voice(_list_default_voices(api_key))
    voice_id = selected["voice_id"]

    PREVIEW_FILE.parent.mkdir(parents=True, exist_ok=True)
    PREVIEW_FILE.write_bytes(_create_preview(api_key, voice_id))

    VOICE_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
    VOICE_ID_FILE.write_text(voice_id + "\n", encoding="utf-8")
    print(f"Configured free ElevenLabs default voice: {selected['name']}")


if __name__ == "__main__":
    main()
