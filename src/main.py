from __future__ import annotations

import argparse
import json
from pathlib import Path

from .models import ShortPlan
from .pipeline import produce


def main() -> None:
    parser = argparse.ArgumentParser(description="Research and render a Korean YouTube Short")
    parser.add_argument("topic", nargs="?", help="Shorts topic")
    parser.add_argument("--validate-plan", type=Path, help="Validate a local plan JSON")
    args = parser.parse_args()

    if args.validate_plan:
        ShortPlan.from_dict(json.loads(args.validate_plan.read_text(encoding="utf-8")))
        print("plan-ok")
        return
    if not args.topic:
        parser.error("topic is required")
    video, metadata = produce(args.topic)
    print(video)
    print(metadata)


if __name__ == "__main__":
    main()

