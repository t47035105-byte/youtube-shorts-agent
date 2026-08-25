from __future__ import annotations
import json, math, subprocess, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFont
from .models import Scene, ShortPlan

WIDTH, HEIGHT = 1080, 1920
INK=(9,10,13); IVORY=(246,242,233); GOLD=(205,174,112); MUTED=(190,187,179)

def _font(size:int,bold:bool=False):
    candidates=["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc","/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in candidates:
        if Path(p).exists(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def _cover(im):
    r=max(WIDTH/im.width,HEIGHT/im.height); im=im.resize((math.ceil(im.width*r),math.ceil(im.height*r)),Image.Resampling.LANCZOS)
    l=(im.width-WIDTH)//2; t=(im.height-HEIGHT)//2
    return im.crop((l,t,l+WIDTH,t+HEIGHT))

def _lines(text,width=12): return textwrap.wrap(" ".join(text.split()),width=width,break_long_words=True,break_on_hyphens=False)[:3]

def make_card(scene:Scene,index:int,total:int,source_image:Path|None,output:Path)->Path:
    if source_image and source_image.exists():
        base=_cover(Image.open(source_image).convert("RGB")); base=ImageEnhance.Contrast(base).enhance(1.12); base=ImageEnhance.Color(base).enhance(.9)
        veil=Image.new("RGBA",(WIDTH,HEIGHT),(0,0,0,0)); v=ImageDraw.Draw(veil); v.rectangle((0,0,WIDTH,HEIGHT),fill=(0,0,0,35)); v.rectangle((0,1050,WIDTH,HEIGHT),fill=(4,5,8,185)); base=Image.alpha_composite(base.convert("RGBA"),veil)
    else:
        base=Image.new("RGBA",(WIDTH,HEIGHT),INK+(255,)); d=ImageDraw.Draw(base)
        for y in range(HEIGHT):
            q=y/HEIGHT; d.line((0,y,WIDTH,y),fill=(9+int(14*q),10+int(12*q),13+int(15*q),255))
        d.polygon([(0,0),(1080,0),(1080,600)],fill=(25,24,23,255))
    d=ImageDraw.Draw(base); kicker=_font(27,True); cap=_font(100,True); sub=_font(30)
    d.text((72,82),"JYP  ·  DISCIPLINE",font=kicker,fill=GOLD); d.line((72,135,260,135),fill=GOLD,width=3)
    y=1260
    for line in _lines(scene.caption,11): d.text((72,y),line,font=cap,fill=IVORY,stroke_width=2,stroke_fill=(0,0,0)); y+=128
    d.text((72,1818),"박진영이 공개한 자기관리 루틴",font=sub,fill=MUTED)
    output.parent.mkdir(parents=True,exist_ok=True); base.convert("RGB").save(output,quality=96); return output

def _duration(p): return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(p)],text=True).strip())

def render(plan:ShortPlan,audio_path:Path,images:list[Path|None],output_path:Path)->Path:
    work=output_path.parent/"render_work"; work.mkdir(parents=True,exist_ok=True)
    fast=work/"voice_1_2x.mp3"; subprocess.run(["ffmpeg","-y","-i",str(audio_path),"-filter:a","atempo=1.2","-vn",str(fast)],check=True)
    ad=_duration(fast); total=sum(s.duration_s for s in plan.scenes); durations=[ad*s.duration_s/total for s in plan.scenes]; clips=[]
    for i,(scene,dur,src) in enumerate(zip(plan.scenes,durations,images),1):
        frame=make_card(scene,i,len(plan.scenes),src,work/f"card_{i:02d}.jpg"); clip=work/f"clip_{i:02d}.mp4"
        # Stable Ken Burns effect: zoompan must generate duration*fps frames, not d=1.
        frames=max(1,int(math.ceil(dur*30)))
        zoom="min(zoom+0.00045,1.05)"
        vf=f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={WIDTH}x{HEIGHT}:fps=30,format=yuv420p"
        subprocess.run(["ffmpeg","-y","-loop","1","-i",str(frame),"-t",f"{dur:.3f}","-vf",vf,"-an","-r","30","-c:v","libx264","-preset","medium","-crf","19",str(clip)],check=True); clips.append(clip)
    cf=work/"clips.txt"; cf.write_text("".join(f"file '{c.resolve()}'\n" for c in clips),encoding="utf-8"); silent=work/"silent.mp4"
    # Re-encode concat for robust timestamps across scene clips.
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(cf),"-c:v","libx264","-preset","medium","-crf","19","-pix_fmt","yuv420p","-an",str(silent)],check=True)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(["ffmpeg","-y","-i",str(silent),"-i",str(fast),"-map","0:v:0","-map","1:a:0","-shortest","-c:v","libx264","-preset","medium","-crf","19","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-movflags","+faststart",str(output_path)],check=True)
    output_path.with_suffix(".json").write_text(json.dumps(plan.to_dict(),ensure_ascii=False,indent=2),encoding="utf-8"); return output_path
