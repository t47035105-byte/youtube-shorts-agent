from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from .elevenlabs_tts import synthesize
from .image_maker import generate_scene_images
from .script_writer import write_plan
from .video_renderer import render


def slugify(value: str) -> str:
    clean = re.sub(r"[^0-9A-Za-z가-힣]+", "-", value).strip("-")
    return clean[:48] or "short"


def produce(topic: str, output_root: Path = Path("output")) -> tuple[Path, Path]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    job_dir = output_root / f"{stamp}-{slugify(topic)}"
    job_dir.mkdir(parents=True, exist_ok=True)

    plan = write_plan(topic)
    images = generate_scene_images(plan, job_dir / "images")
    audio = synthesize(plan.narration, job_dir / "narration.mp3")
    video = render(plan, audio, images, job_dir / "short.mp4")
    return video, video.with_suffix(".json")

