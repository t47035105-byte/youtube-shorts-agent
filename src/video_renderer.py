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
BG = (14, 17, 24)
ACCENT = (86, 232, 186)
ACCENT2 = (255, 207, 84)
WHITE = (250, 251, 253)
MUTED = (190, 198, 211)


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


def wrap_caption(text: str, width: int = 11) -> list[str]:
    return textwrap.wrap(" ".join(text.split()), width=width, break_long_words=True, break_on_hyphens=False)[:3]


def make_card(scene: Scene, index: int, total: int, source_image: Path | None, output: Path) -> Path:
    if source_image and source_image.exists():
        base = _cover(Image.open(source_image).convert("RGB"))
        base = ImageEnhance.Contrast(base).enhance(1.10)
        base = ImageEnhance.Color(base).enhance(0.88)
    else:
        base = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(base)
        for y in range(HEIGHT):
            p = y / HEIGHT
            draw.line((0, y, WIDTH, y), fill=(14 + int(14*p), 17 + int(19*p), 24 + int(28*p)))
        draw.ellipse((650, 80, 1280, 710), fill=(25, 73, 68))
        draw.ellipse((-340, 1190, 520, 2050), fill=(66, 48, 28))

    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.rectangle((0, 0, WIDTH, HEIGHT), fill=(5, 8, 14, 62))
    odraw.rectangle((0, 0, WIDTH, 330), fill=(5, 8, 14, 125))
    odraw.rounded_rectangle((45, 1210, 1035, 1775), radius=48, fill=(7, 11, 18, 215))
    base = Image.alpha_composite(base.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(base)

    label_font = _font(34, True)
    number_font = _font(58, True)
    caption_font = _font(96, True)
    small_font = _font(31)

    draw.rounded_rectangle((58, 70, 465, 142), radius=32, fill=(8, 13, 21, 225), outline=ACCENT, width=3)
    draw.text((88, 86), "박진영 자기관리 루틴", font=label_font, fill=ACCENT)
    draw.text((900, 78), f"{index:02d}", font=number_font, fill=WHITE)

    lines = wrap_caption(scene.caption)
    y = 1290
    for i, line in enumerate(lines):
        draw.text((78, y), line, font=caption_font, fill=ACCENT2 if i == 0 else WHITE, stroke_width=3, stroke_fill=(0,0,0))
        y += 125

    bar_x1, bar_x2, bar_y = 78, 1002, 1815
    draw.rounded_rectangle((bar_x1, bar_y, bar_x2, bar_y + 12), radius=6, fill=(255,255,255,55))
    progress = bar_x1 + int((bar_x2-bar_x1)*index/total)
    draw.rounded_rectangle((bar_x1, bar_y, progress, bar_y + 12), radius=6, fill=ACCENT)
    draw.text((78, 1850), "공개 방송·인터뷰 기준  |  개인 루틴", font=small_font, fill=MUTED)

    output.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(output, quality=96)
    return output


def _duration(audio_path: Path) -> float:
    command = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)]
    return float(subprocess.check_output(command, text=True).strip())


def render(plan: ShortPlan, audio_path: Path, images: list[Path | None], output_path: Path) -> Path:
    work = output_path.parent / "render_work"
    work.mkdir(parents=True, exist_ok=True)

    # Reporter-style pacing: speed narration to 1.2x before timing the scenes.
    fast_audio = work / "voice_1_2x.mp3"
    subprocess.run(["ffmpeg", "-y", "-i", str(audio_path), "-filter:a", "atempo=1.2", "-vn", str(fast_audio)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    audio_duration = _duration(fast_audio)
    original_total = sum(scene.duration_s for scene in plan.scenes)
    durations = [audio_duration * scene.duration_s / original_total for scene in plan.scenes]

    clips = []
    for index, (scene, duration, source) in enumerate(zip(plan.scenes, durations, images), start=1):
        frame = make_card(scene, index, len(plan.scenes), source, work / f"card_{index:02d}.jpg")
        clip = work / f"clip_{index:02d}.mp4"
        zoom = "min(zoom+0.0008,1.08)" if index % 2 else "if(eq(on,1),1.08,max(zoom-0.0008,1.0))"
        vf = f"scale=1200:2134,crop={WIDTH}:{HEIGHT},zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={WIDTH}x{HEIGHT}:fps=30,format=yuv420p,fade=t=in:st=0:d=0.14,fade=t=out:st={max(0.0,duration-0.14):.3f}:d=0.14"
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(frame), "-t", f"{duration:.3f}", "-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20", str(clip)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        clips.append(clip)

    concat_file = work / "clips.txt"
    concat_file.write_text("".join(f"file '{clip.resolve()}'\n" for clip in clips), encoding="utf-8")
    silent = work / "silent.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(silent)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-i", str(silent), "-i", str(fast_audio), "-map", "0:v:0", "-map", "1:a:0", "-shortest", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(output_path)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    output_path.with_suffix(".json").write_text(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path
