from __future__ import annotations

import json
import math
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from .models import Scene, ShortPlan


WIDTH = 1080
HEIGHT = 1920
NAVY = (10, 20, 38)
AMBER = (255, 194, 66)
WHITE = (248, 249, 252)
MUTED = (184, 196, 214)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _cover(image: Image.Image) -> Image.Image:
    ratio = max(WIDTH / image.width, HEIGHT / image.height)
    resized = image.resize((math.ceil(image.width * ratio), math.ceil(image.height * ratio)), Image.Resampling.LANCZOS)
    left = (resized.width - WIDTH) // 2
    top = (resized.height - HEIGHT) // 2
    return resized.crop((left, top, left + WIDTH, top + HEIGHT))


def wrap_caption(text: str, width: int = 13) -> list[str]:
    compact = " ".join(text.split())
    return textwrap.wrap(compact, width=width, break_long_words=True, break_on_hyphens=False)[:3]


def make_card(scene: Scene, index: int, total: int, source_image: Path | None, output: Path) -> Path:
    if source_image and source_image.exists():
        base = _cover(Image.open(source_image).convert("RGB"))
        base = ImageEnhance.Contrast(base).enhance(1.08)
        blurred = base.filter(ImageFilter.GaussianBlur(18))
        base = Image.blend(blurred, base, 0.88)
    else:
        base = Image.new("RGB", (WIDTH, HEIGHT), NAVY)
        draw = ImageDraw.Draw(base)
        for y in range(HEIGHT):
            p = y / HEIGHT
            draw.line((0, y, WIDTH, y), fill=(10 + int(24 * p), 20 + int(18 * p), 38 + int(36 * p)))
        draw.ellipse((570, 140, 1190, 760), fill=(32, 62, 101))
        draw.ellipse((-250, 1150, 580, 1980), fill=(91, 57, 32))

    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.rectangle((0, 0, WIDTH, HEIGHT), fill=(4, 10, 22, 88))
    odraw.rectangle((0, 0, WIDTH, 360), fill=(4, 10, 22, 105))
    odraw.rectangle((0, 1260, WIDTH, HEIGHT), fill=(4, 10, 22, 180))
    base = Image.alpha_composite(base.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(base)

    label_font = _font(36, bold=True)
    number_font = _font(88, bold=True)
    caption_font = _font(92, bold=True)
    small_font = _font(34)

    draw.rounded_rectangle((62, 78, 480, 150), radius=34, fill=(10, 20, 38, 215), outline=AMBER, width=3)
    draw.text((92, 91), "생활비 소비검증", font=label_font, fill=AMBER)
    draw.text((70, 210), f"{index:02d}", font=number_font, fill=WHITE)

    lines = wrap_caption(scene.caption)
    y = 1320
    for line_no, line in enumerate(lines):
        fill = AMBER if line_no == 0 else WHITE
        draw.text((72, y), line, font=caption_font, fill=fill, stroke_width=2, stroke_fill=(0, 0, 0))
        y += 120

    bar_x1, bar_x2, bar_y = 72, 1008, 1810
    draw.rounded_rectangle((bar_x1, bar_y, bar_x2, bar_y + 15), radius=7, fill=(255, 255, 255, 55))
    progress = bar_x1 + int((bar_x2 - bar_x1) * index / total)
    draw.rounded_rectangle((bar_x1, bar_y, progress, bar_y + 15), radius=7, fill=AMBER)
    draw.text((72, 1842), "게시 시점 기준 · 조건은 변경될 수 있음", font=small_font, fill=MUTED)

    output.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(output, quality=95)
    return output


def _duration(audio_path: Path) -> float:
    command = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path),
    ]
    return float(subprocess.check_output(command, text=True).strip())


def render(plan: ShortPlan, audio_path: Path, images: list[Path | None], output_path: Path) -> Path:
    work = output_path.parent / "render_work"
    work.mkdir(parents=True, exist_ok=True)
    audio_duration = _duration(audio_path)
    original_total = sum(scene.duration_s for scene in plan.scenes)
    durations = [audio_duration * scene.duration_s / original_total for scene in plan.scenes]

    clips: list[Path] = []
    for index, (scene, duration, source) in enumerate(zip(plan.scenes, durations, images), start=1):
        frame = make_card(scene, index, len(plan.scenes), source, work / f"card_{index:02d}.jpg")
        clip = work / f"clip_{index:02d}.mp4"
        zoom = "min(zoom+0.0008,1.08)" if index % 2 else "if(eq(on,1),1.08,max(zoom-0.0008,1.0))"
        vf = (
            f"scale=1200:2134,crop={WIDTH}:{HEIGHT},"
            f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=1:s={WIDTH}x{HEIGHT}:fps=30,format=yuv420p,"
            "fade=t=in:st=0:d=0.18,"
            f"fade=t=out:st={max(0.0, duration - 0.18):.3f}:d=0.18"
        )
        subprocess.run(
            [
                "ffmpeg", "-y", "-loop", "1", "-i", str(frame),
                "-t", f"{duration:.3f}", "-vf", vf,
                "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "21", str(clip),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        clips.append(clip)

    concat_file = work / "clips.txt"
    concat_file.write_text("".join(f"file '{clip.resolve()}'\n" for clip in clips), encoding="utf-8")
    silent = work / "silent.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(silent)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(silent), "-i", str(audio_path),
            "-map", "0:v:0", "-map", "1:a:0", "-shortest",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(output_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    metadata = output_path.with_suffix(".json")
    metadata.write_text(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path
