from __future__ import annotations

import os
from pathlib import Path

import requests


API_ROOT = "https://api.elevenlabs.io/v1"
DEFAULT_VOICE_ID = "7GJLtfswFrmju7j66Puy"
DEFAULT_VOICE_NAME = "제니 쇼츠 진행자"
PREVIEW_TEXT = (
    "쿠팡 와우와 네이버플러스, 둘 다 내면 한 달 만 이천 칠백 구십 원. "
    "일 년이면 십오만 삼천 사백 팔십 원. 둘 다 정말 필요할까요? "
    "쿠팡 와우는 월 칠천 팔백 구십 원. 로켓배송과 무료반품을 자주 쓰면 유리합니다. "
    "배송비를 건당 삼천 원으로 가정하면, 한 달 세 번부터 회비를 넘깁니다. "
    "네이버플러스는 월 사천 구백 원. 연간권은 월 환산 삼천 구백 원입니다. "
    "최대 오 퍼센트 적립이라면, 월간권은 구만 팔천 원, 연간권은 칠만 팔천 원부터 본전입니다. "
    "소액 로켓배송은 쿠팡. 네이버 쇼핑과 디지털 콘텐츠는 네이버가 유리합니다. "
    "최근 한 달 사용내역을 확인하세요. 구독은 습관이 아니라 계산입니다."
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
