"""Feature-intro 미국꿀템 Reel: several AI clips/stills, each with a caption, + end card -> 1080x1920 MP4.

Usage: python3 tools/feature_reel.py posts/<folder>/reel.json
Overlays are drawn with Pillow (Noto Sans CJK KR), so it runs without Playwright.
All text, prices and ratings come from reel.json (verified data) — never from the AI.
"""
import json, os, sys, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
NAVY, HONEY, CREAM, MUTE, WHITE = (20, 33, 61), (255, 200, 61), (255, 246, 224), (169, 178, 200), (255, 255, 255)
FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
for cand in ["/System/Library/Fonts/AppleSDGothicNeo.ttc"]:
    if not os.path.exists(FB) and os.path.exists(cand): FB = FR = cand
def font(sz, bold=True): return ImageFont.truetype(FB if bold else FR, sz, index=1 if "Noto" in FB else 0)

SIDE = 110          # symmetric side margin (clear of IG right rail)
TOP_Y = 250         # hook headline area (below IG top bar)
LOW_Y = 1180        # feature captions band (above IG caption/username area)

def tw(d, s, f): b = d.textbbox((0, 0), s, font=f); return b[2] - b[0], b[3] - b[1]

def ctext(d, y, s, f, fill, stroke=0, sfill=None, shadow=True):
    w, h = tw(d, s, f); x = (W - w) // 2
    if shadow: d.text((x + 3, y + 5), s, font=f, fill=(0, 0, 0, 140))
    d.text((x, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=sfill or fill)
    return h

def pill(d, cy, s, f, bg, fg, padx=28, pady=12, r=18):
    w, h = tw(d, s, f); x0 = (W - w) // 2 - padx; y0 = cy
    d.rounded_rectangle([x0, y0, x0 + w + 2 * padx, y0 + h + 2 * pady + 8], r, fill=bg)
    d.text(((W - w) // 2, y0 + pady - 2), s, font=f, fill=fg, stroke_width=1, stroke_fill=fg)
    return h + 2 * pady + 8

def brand(d):
    # logo dot + name (top-left), 광고 chip (top-right) — inside IG safe area
    d.ellipse([60, 150, 128, 218], fill=HONEY)
    d.text((94, 166), "MIGOOK", font=font(9), fill=NAVY, anchor="mm")
    d.text((94, 192), "꿀템", font=font(22), fill=NAVY, anchor="mm")
    d.text((142, 165), "미국꿀템", font=font(30), fill=WHITE, stroke_width=1, stroke_fill=WHITE)
    f = font(26); w, h = tw(d, "광고", f)
    d.rounded_rectangle([W - 60 - w - 28, 160, W - 60, 160 + h + 22], 10, fill=WHITE)
    d.text((W - 60 - w - 14, 164), "광고", font=f, fill=NAVY)

def wrap_lines(d, s, f, maxw):
    out = []
    for para in s.split("\n"):
        if tw(d, para, f)[0] <= maxw: out.append(para); continue
        words, cur = para.split(" "), ""
        for wd in words:
            t = (cur + " " + wd).strip()
            if tw(d, t, f)[0] <= maxw: cur = t
            else: out.append(cur); cur = wd
        out.append(cur)
    return out

def overlay(seg, path):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # soft navy shade top & behind the caption band
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
    for y in range(0, 420): sd.line([(0, y), (W, y)], fill=NAVY + (int(200 * (1 - y / 420) ** 1.3),))
    if seg.get("pos") == "band":
        # soft navy band only behind the caption, so the product above/below stays visible
        cy0, cy1 = seg["y"] - 40, seg["y"] + 200
        for y in range(cy0 - 120, cy1 + 120):
            dist = max(0, cy0 - y, y - cy1)
            sd.line([(0, y), (W, y)], fill=NAVY + (int(185 * max(0, 1 - dist / 120)),))
    elif seg.get("pos") == "low":
        for y in range(LOW_Y - 220, H): sd.line([(0, y), (W, y)], fill=NAVY + (int(225 * min(1, (y - LOW_Y + 220) / 300)),))
    else:
        for y in range(0, 760): sd.line([(0, y), (W, y)], fill=NAVY + (int(210 * (1 - y / 760) ** 1.1),))
    im = Image.alpha_composite(im, sh); d = ImageDraw.Draw(im)
    brand(d)
    maxw = W - 2 * SIDE
    if seg.get("pos") in ("low", "band"):
        y = seg["y"] if seg.get("pos") == "band" else LOW_Y
        for ln in wrap_lines(d, seg["title"], font(64), maxw):
            y += ctext(d, y, ln, font(64), WHITE, stroke=1) + 22
        if seg.get("sub"):
            y += 14; pill(d, y, seg["sub"], font(32), CREAM, NAVY)
    else:
        y = TOP_Y + 20
        if seg.get("kicker"): y += pill(d, y, seg["kicker"], font(40), HONEY, NAVY) + 26
        for ln in wrap_lines(d, seg["title"], font(84), maxw):
            y += ctext(d, y, ln, font(84), WHITE, stroke=2) + 26
    im.save(path)

def endcard(e, asof, path):
    im = Image.new("RGB", (W, H), NAVY); d = ImageDraw.Draw(im)
    brand(d)
    y = 380
    d.ellipse([W // 2 - 80, y, W // 2 + 80, y + 160], fill=HONEY)
    d.text((W // 2, y + 52), "MIGOOK", font=font(18), fill=NAVY, anchor="mm")
    d.text((W // 2, y + 100), "꿀템", font=font(50), fill=NAVY, anchor="mm")
    y += 196
    y += pill(d, y, e["badge"], font(34), CREAM, NAVY) + 22
    y += ctext(d, y, e["name"], font(44), WHITE, stroke=1, shadow=False) + 26
    y += ctext(d, y, e["price"], font(132), HONEY, stroke=3, shadow=False) + 34
    y += ctext(d, y, f"{asof} 아마존 가격 기준 · 가격은 바뀔 수 있어요", font(26, False), MUTE, shadow=False) + 20
    y += pill(d, y, e["history"], font(30), CREAM, NAVY) + 34
    y += ctext(d, y, e["rating"], font(38), HONEY, shadow=False) + 18
    for ln in wrap_lines(d, e["review"], font(29, False), W - 2 * SIDE):
        y += ctext(d, y, ln, font(29, False), WHITE, shadow=False) + 12
    y += ctext(d, y, e["con"], font(29, False), MUTE, shadow=False) + 40
    y += pill(d, y, e["cta"], font(50), HONEY, NAVY, padx=60, pady=24, r=26) + 26
    ctext(d, y, e["save"], font(30, False), WHITE, shadow=False)
    ctext(d, H - 360, "광고 · 아마존 제휴링크 포함", font(24, False), MUTE, shadow=False)
    im.save(path)

def run(cmd): subprocess.run(cmd, check=True)

if __name__ == "__main__":
    cfg_path = sys.argv[1]; cfg = json.load(open(cfg_path, encoding="utf-8"))
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(cfg_path))))
    out = os.path.join(os.path.dirname(os.path.abspath(cfg_path)), "build"); os.makedirs(out, exist_ok=True)
    parts = []
    for i, seg in enumerate(cfg["segments"]):
        ov = os.path.join(out, f"ov{i}.png"); overlay(seg, ov)
        src = os.path.join(root, seg["src"]); part = os.path.join(out, f"part{i}.mp4"); dur = seg["dur"]
        z = seg.get("zoom", 1.0)
        if src.lower().endswith((".png", ".jpg", ".jpeg")):
            n = int(dur * FPS)
            vin = ["-loop", "1", "-i", src]
            # optional focus for stills: fx/fy = point to center on (0-1), z0->z1 = zoom over the segment
            fx, fy = seg.get("fx", 0.5), seg.get("fy", 0.5); z0, z1 = seg.get("z0", 1.0), seg.get("z1", 1.04)
            base = (f"[0:v]scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
                    f"zoompan=z='{z0}+({z1}-{z0})*on/{n}':x='max(0,min(iw-iw/zoom,{fx}*iw-iw/zoom/2))':"
                    f"y='max(0,min(ih-ih/zoom,{fy}*ih-ih/zoom/2))':d={n}:s={W}x{H}:fps={FPS}")
        else:
            vin = ["-ss", str(seg.get("start", 0)), "-t", str(dur), "-i", src]
            base = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                    f"scale={int(W*z)//2*2}:{int(H*z)//2*2},crop={W}:{H},fps={FPS}")
        fc = f"{base},setsar=1[bg];[bg][1:v]overlay=0:0,format=yuv420p" + ("" if i == 0 else ",fade=t=in:st=0:d=0.15")
        run(["ffmpeg", "-y", "-loglevel", "error", *vin, "-loop", "1", "-i", ov, "-filter_complex", fc,
             "-t", str(dur), "-an", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", part])
        parts.append(part)
    ec = os.path.join(out, "end.png"); endcard(cfg["end"], cfg["asof"], ec)
    ep = os.path.join(out, "partend.mp4")
    run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", ec, "-t", str(cfg["end"]["dur"]), "-vf",
         f"fps={FPS},format=yuv420p,fade=t=in:st=0:d=0.3", "-c:v", "libx264", "-crf", "18", ep])
    parts.append(ep)
    lst = os.path.join(out, "list.txt"); open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    total = sum(s["dur"] for s in cfg["segments"]) + cfg["end"]["dur"]
    mp4 = os.path.join(os.path.dirname(os.path.abspath(cfg_path)), cfg["slug"] + ".mp4")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
         "-f", "lavfi", "-t", str(total), "-i", "anullsrc=r=44100:cl=stereo",
         "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-profile:v", "high", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", mp4])
    cover = mp4.replace(".mp4", "-cover.jpg")
    run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1.0", "-i", mp4, "-frames:v", "1", "-q:v", "3", cover])
    print(mp4); print(cover); print(f"{total:.1f}s")
