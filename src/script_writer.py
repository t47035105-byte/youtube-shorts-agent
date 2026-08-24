from __future__ import annotations

import json
import os
import re

import requests

from .models import ShortPlan


PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "hook": {"type": "string"},
        "narration": {"type": "string"},
        "description": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 7},
        "scenes": {
            "type": "array", "minItems": 4, "maxItems": 8,
            "items": {
                "type": "object",
                "properties": {
                    "caption": {"type": "string"},
                    "visual_prompt": {"type": "string"},
                    "duration_s": {"type": "number"},
                },
                "required": ["caption", "visual_prompt", "duration_s"],
                "additionalProperties": False,
            },
        },
        "sources": {
            "type": "array", "minItems": 0, "maxItems": 6,
            "items": {
                "type": "object",
                "properties": {"title": {"type": "string"}, "url": {"type": "string"}},
                "required": ["title", "url"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "hook", "narration", "description", "hashtags", "scenes", "sources"],
    "additionalProperties": False,
}


INSTRUCTIONS = """
당신은 한국의 50대 이상 시청자가 즉시 이해하는 유튜브 쇼츠 편집장이다.
45~58초 분량의 세로형 쇼츠 기획안을 만든다.
한국어 구어체와 짧은 문장을 사용하고 첫 1.5초에 강한 훅을 둔다.
내레이션은 장면 순서와 일치해야 한다. 각 캡션은 한눈에 읽히게 짧게 쓴다.
visual_prompt는 이미지 안에 글자를 넣지 않는 세로형 사진/영상 지시문으로 쓴다.
설명란 끝에는 '정보는 게시 시점 기준이며 변경될 수 있습니다.'를 넣는다.
사실 확인이 필요한 내용을 임의로 꾸며내지 않는다.
반드시 JSON 하나만 출력하고 마크다운 코드블록은 쓰지 않는다.
""".strip()


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise RuntimeError(f"Gemini did not return JSON: {text[:300]}")
    return json.loads(text[start:end + 1])


def write_plan(topic: str) -> ShortPlan:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required")

    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    prompt = (
        INSTRUCTIONS
        + "\n\n다음 주제로 쇼츠 기획안을 작성하세요: " + topic
        + "\n\nJSON 구조는 다음 JSON Schema를 따르세요:\n"
        + json.dumps(PLAN_SCHEMA, ensure_ascii=False)
    )
    response = requests.post(
        url,
        params={"key": api_key},
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4},
        },
        timeout=90,
    )
    if not response.ok:
        raise RuntimeError(f"Gemini API error {response.status_code}: {response.text[:1000]}")
    data = response.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected Gemini response: {data}") from exc
    return ShortPlan.from_dict(_extract_json(text))
