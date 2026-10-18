"""Zero-credit single-item Reels from existing carousel slides.

Usage:
  python3 tools/item_reel.py posts/2026-10-16-deals/slides.json docs/img/2026-10-16-deals [--asof "10/17 오후"] [--out DIR]

For item i (1..N) it uses the rendered slide <prefix>-0{i+1}.jpg, removes the old slide counter
and any "AI 연출" chip (inpaint), and builds a 1080x1920, 9s MP4:
  0-6.5s  blurred backdrop + slide with slow push-in + hook band on top
  6.5-9s  end card (item, price, 링크는 프로필에, 광고 disclosure)
If --asof differs from slides.json asof, the slide's "as of" line is replaced (price must be re-verified!).
"""
import argparse, json, os, subprocess, sys
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

NAVY, NAVY2, HONEY, CREAM, HOT = (20, 33, 61), (30, 47, 85), (255, 200, 61), (255, 246, 224), (229, 72, 77)
W, H, FPS, MAIN, END = 1080, 1920, 30, 6.5, 2.5
FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
FM = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

def font(size, black=True):
    p = FB if black else FM
    for i in range(10):  # pick the KR face inside the collection
        f = ImageFont.truetype(p, size, index=i)
        if "KR" in f.getname()[0]: return f
    return ImageFont.truetype(p, size)

HOOKS = {  # short Reel hook per item (top line = honey kicker, bottom = big white)
    "B0BRYCXRPG": ("최근 1년 최저가", "유산균 지금이 제일 싸요"),
    "B0GVL6RB6Z": ("5개월 중 최저가", "만두소·김치 양념 한 번에"),
    "B0C4M2D1J2": ("역대 최저가 근접", "갈비찜 넣고 출근하면 끝"),
    "B0BZHG5VQL": ("역대 최저가 근접", "미국 첫 살림 냄비 한 번에"),
    "B091FXQQMQ": ("평균보다 저렴", "가습기, 앱으로 켜고 끄기"),
}

def clean_slide(path, asof_old, asof_new):
    img = cv2.imread(path)
    mask = np.zeros(img.shape[:2], np.uint8)
    mask[110:170, 36:132] = 255      # "n/5" counter pill
    mask[110:168, 884:1044] = 255    # "AI 연출 이미지" chip
    img = cv2.inpaint(img, mask, 9, cv2.INPAINT_TELEA)
    im = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    if asof_new and asof_new != asof_old:   # replace the as-of line (solid navy zone at the bottom)
        d = ImageDraw.Draw(im)
        bg = im.getpixel((1040, 1300))
        d.rectangle((40, 1255, 1060, 1305), fill=bg)
        d.text((56, 1262), f"{asof_new} 아마존 가격 기준 · 가격은 바뀔 수 있어요", font=font(24, False), fill=(169, 178, 200))
    return im

def centered(d, y, text, f, fill):
    w = d.textlength(text, font=f); d.text(((W - w) / 2, y), text, font=f, fill=fill)

def pill(d, cx, y, text, f, fg, bg, padx=26, pady=10):
    w = d.textlength(text, font=f); b = f.getbbox(text)
    d.rounded_rectangle((cx - w / 2 - padx, y, cx + w / 2 + padx, y + b[3] + pady * 2), 18, fill=bg)
    d.text((cx - w / 2, y + pady), text, font=f, fill=fg)

def brand(d, x, y, r=34):
    d.ellipse((x, y, x + 2 * r, y + 2 * r), fill=HONEY)
    fs, fb = font(9), font(20)
    d.text((x + r - d.textlength("MIGOOK", font=fs) / 2, y + 14), "MIGOOK", font=fs, fill=NAVY)
    d.text((x + r - d.textlength("꿀템", font=fb) / 2, y + 24), "꿀템", font=fb, fill=NAVY)
    d.text((x + 2 * r + 14, y + r - 20), "미국꿀템", font=font(30), fill="white")

def backdrop(slide):
    bg = slide.resize((int(W * 1.5), int(1350 * 1.5))).crop((int(W * .25), 60, int(W * 1.25), 60 + H))
    bg = bg.resize((W, H)).filter(ImageFilter.GaussianBlur(40))
    return Image.blend(bg, Image.new("RGB", (W, H), NAVY), .55)

def hook_layer(it, idx, n):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    k, h = HOOKS.get(it["asin"], (it["badge"], it["who"]))
    # slide (with its own brand row + 광고 chip) sits at y=430..1645, scaled to 90%
    d.rounded_rectangle((50, 426, W - 50, 1649), 34, outline=HONEY, width=4)
    pill(d, W / 2, 222, k, font(40), NAVY, HONEY)
    centered(d, 304, h, font(66), (255, 255, 255))
    centered(d, 1682, "링크는 프로필 '오늘의 딜'에 있어요", font(36), HONEY)
    return lay

def endcard(it, asof):
    im = Image.new("RGB", (W, H), NAVY); d = ImageDraw.Draw(im)
    d.ellipse((W / 2 - 95, 330, W / 2 + 95, 520), fill=HONEY)
    centered(d, 372, "MIGOOK", font(22), NAVY); centered(d, 398, "꿀템", font(64), NAVY)
    centered(d, 590, it["name"] if len(it["name"]) <= 18 else it["short"].replace("\n", " "), font(52), (255, 255, 255))
    pill(d, W / 2, 680, it["badge"], font(34), NAVY if it["badge"] != "핫딜" else (255, 255, 255),
         HOT if it["badge"] == "핫딜" else HONEY)
    centered(d, 770, it["price"], font(170), HONEY)
    ref = f"{it['was_label']} {it['was']}  ·  -{it['off']}%"
    centered(d, 990, ref, font(40, False), (169, 178, 200))
    centered(d, 1060, it["history"], font(34, False), (244, 241, 232))
    d.rounded_rectangle((110, 1180, W - 110, 1300), 28, fill=HONEY)
    centered(d, 1208, "링크는 프로필에 있어요", font(50), NAVY)
    centered(d, 1350, "저장해두고 블프 전에 다시 보기 · @migook.kkultem", font(30, False), (169, 178, 200))
    centered(d, 1440, f"광고 · 아마존 제휴링크 포함 · {asof} 기준", font(24, False), (169, 178, 200))
    return im

def build(slides_json, prefix, asof_new, outdir):
    d = json.load(open(slides_json, encoding="utf-8")); os.makedirs(outdir, exist_ok=True)
    asof = asof_new or d["asof"]; n = len(d["items"]); outs = []
    for i, it in enumerate(d["items"], 1):
        slug = f"{d['slug'].replace('-deals', '')}-reel-item{i}"
        tmp = os.path.join(outdir, slug); os.makedirs(tmp, exist_ok=True)
        slide = clean_slide(f"{prefix}-0{i + 1}.jpg", d["asof"], asof_new)
        slide.save(f"{tmp}/slide.png"); backdrop(slide).save(f"{tmp}/bg.png")
        hook_layer(it, i, n).save(f"{tmp}/hook.png"); endcard(it, asof).save(f"{tmp}/end.png")
        frames = int(MAIN * FPS)
        # slide scaled to 972x1215, placed at (54,430) with a slow push-in (1.00 -> 1.06), centered on product area
        fc = (f"[1:v]scale=1080*4:1350*4,zoompan=z='1+0.06*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih*0.42-(ih/zoom*0.42)'"
              f":d={frames}:s=972x1215:fps={FPS}[z];"
              f"[0:v][z]overlay=54:430[a];[a][2:v]overlay=0:0,format=yuv420p,trim=duration={MAIN}[m];"
              f"[3:v]fps={FPS},format=yuv420p,fade=t=in:st=0:d=0.3[e];[m][e]concat=n=2:v=1:a=0[v]")
        mp4 = os.path.join(outdir, slug + ".mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                        "-loop", "1", "-framerate", str(FPS), "-t", str(MAIN), "-i", f"{tmp}/bg.png",
                        "-loop", "1", "-framerate", "1", "-t", "1", "-i", f"{tmp}/slide.png",
                        "-loop", "1", "-framerate", str(FPS), "-t", str(MAIN), "-i", f"{tmp}/hook.png",
                        "-loop", "1", "-framerate", str(FPS), "-t", str(END), "-i", f"{tmp}/end.png",
                        "-f", "lavfi", "-t", str(MAIN + END), "-i", "anullsrc=r=44100:cl=stereo",
                        "-filter_complex", fc, "-map", "[v]", "-map", "4:a",
                        "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", "20",
                        "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", mp4], check=True)
        cover = os.path.join(outdir, slug + "-cover.jpg")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", mp4, "-frames:v", "1", "-q:v", "3", cover], check=True)
        outs.append(mp4); print(mp4)
    return outs

if __name__ == "__main__":
    a = argparse.ArgumentParser(); a.add_argument("slides_json"); a.add_argument("prefix")
    a.add_argument("--asof"); a.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    o = a.parse_args(); build(o.slides_json, o.prefix, o.asof, o.out)
