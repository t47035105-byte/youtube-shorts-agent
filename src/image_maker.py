from __future__ import annotations

import base64
import os
from pathlib import Path

from .models import ShortPlan


STYLE = """
Premium Korean editorial advertising photograph, vertical 9:16 composition,
realistic materials, clean modern lighting, restrained navy and warm amber palette,
strong central subject, generous negative space for later captions, no text, no logo,
no watermark, no split screen.
""".strip()


def generate_scene_images(plan: ShortPlan, output_dir: Path) -> list[Path | None]:
    from openai import OpenAI

    output_dir.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("OPENAI_API_KEY")
    image_count = max(0, min(len(plan.scenes), int(os.environ.get("IMAGE_COUNT", "4"))))
    if not api_key or image_count == 0:
        return [None] * len(plan.scenes)

    client = OpenAI(api_key=api_key)
    result: list[Path | None] = []
    for index, scene in enumerate(plan.scenes):
        if index >= image_count:
            result.append(None)
            continue
        try:
            image = client.images.generate(
                model=os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2"),
                prompt=f"{STYLE}\nScene: {scene.visual_prompt}",
                size="1024x1536",
                quality=os.environ.get("OPENAI_IMAGE_QUALITY", "medium"),
                n=1,
            )
            path = output_dir / f"scene_{index + 1:02d}.png"
            path.write_bytes(base64.b64decode(image.data[0].b64_json))
            result.append(path)
        except Exception:
            result.append(None)
    return result
