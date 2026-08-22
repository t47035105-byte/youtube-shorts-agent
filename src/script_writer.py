from __future__ import annotations

import json
import os

from .models import ShortPlan


PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "hook": {"type": "string"},
        "narration": {"type": "string"},
        "description": {"type": "string"},
        "hashtags": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 7,
        },
        "scenes": {
            "type": "array",
            "minItems": 4,
            "maxItems": 8,
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
            "type": "array",
            "minItems": 2,
            "maxItems": 6,
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "url": {"type": "string"},
                },
                "required": ["title", "url"],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "title",
        "hook",
        "narration",
        "description",
        "hashtags",
        "scenes",
        "sources",
    ],
    "additionalProperties": False,
}


INSTRUCTIONS = """
당신은 한국의 50대 이상 시청자도 즉시 이해하는 소비 검증형 유튜브 쇼츠 편집장이다.
반드시 실시간 웹 검색으로 현재 정보를 확인하고, 기업 공식 페이지·정부·공공기관·주요 언론처럼
신뢰 가능한 출처를 우선한다. 날짜·가격·조건을 근거 없이 추정하지 않는다.

완성물 규칙:
- 45~58초 분량, 첫 1.5초에 강한 질문이나 손실 회피형 훅
- 한국어 구어체, 짧은 문장, 과장·공포 조장·투자 권유 금지
- 숫자는 비교가 바로 되게 말하고 적용 조건을 생략하지 않는다
- 내레이션은 장면 순서와 정확히 일치
- 각 캡션은 한눈에 읽히는 18자 안팎
- visual_prompt는 이미지 안에 글자를 넣지 않는 세로형 광고 사진 지시문
- 설명란 끝에 '가격과 조건은 게시 시점 기준이며 변경될 수 있습니다.' 포함
- sources에는 실제로 확인한 URL만 기록
""".strip()


def write_plan(topic: str) -> ShortPlan:
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for researched script generation")

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-5.6"),
        reasoning={"effort": os.environ.get("OPENAI_REASONING", "low")},
        instructions=INSTRUCTIONS,
        tools=[{"type": "web_search", "external_web_access": True}],
        tool_choice="required",
        input=f"다음 주제를 검증해서 쇼츠 기획안을 JSON으로 작성하세요: {topic}",
        text={
            "format": {
                "type": "json_schema",
                "name": "consumer_short_plan",
                "strict": True,
                "schema": PLAN_SCHEMA,
            }
        },
    )
    return ShortPlan.from_dict(json.loads(response.output_text))
