import unittest

from src.models import ShortPlan
from src.telegram_agent import parse_command
from src.video_renderer import wrap_caption


SAMPLE_PLAN = {
    "title": "구독료, 둘 다 내세요?",
    "hook": "매달 새는 돈부터 확인하세요.",
    "narration": "구독료는 습관이 아니라 계산입니다.",
    "description": "검증용 예시입니다.",
    "hashtags": ["생활비", "소비검증", "구독료"],
    "scenes": [
        {"caption": f"장면 {i}", "visual_prompt": "깔끔한 소비 장면", "duration_s": 5}
        for i in range(1, 6)
    ],
    "sources": [
        {"title": "공식 자료 1", "url": "https://example.com/1"},
        {"title": "공식 자료 2", "url": "https://example.com/2"},
    ],
}


class CoreTests(unittest.TestCase):
    def test_parse_command(self) -> None:
        self.assertEqual(parse_command("/make 쿠팡 구독료"), ("/make", "쿠팡 구독료"))
        self.assertEqual(parse_command("/make@my_bot 주제"), ("/make", "주제"))
        self.assertEqual(parse_command("일반 대화"), ("", ""))

    def test_wrap_caption_limits_lines(self) -> None:
        lines = wrap_caption("구독료를 둘 다 내고 계신가요 정말 필요한지 계산해봅니다")
        self.assertGreaterEqual(len(lines), 1)
        self.assertLessEqual(len(lines), 3)

    def test_plan_validation(self) -> None:
        plan = ShortPlan.from_dict(SAMPLE_PLAN)
        self.assertEqual(len(plan.scenes), 5)
        self.assertEqual(plan.hashtags[0], "생활비")


if __name__ == "__main__":
    unittest.main()

