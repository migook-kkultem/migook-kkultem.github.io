"""Multi-item 미국꿀템 Reel: one product per beat (zoom punch + price pop-in), quick intro, end card.

Usage: python3 tools/multi_reel.py posts/<folder>/reel.json
reel.json: slug, asof, intro{kicker,title,dur}, items[{src,bg?,badge,name,sub,reason,price,ref,history,rating,dur}], end{dur,cta}
All text, prices and ratings come from reel.json (verified data) — never from the AI image.
"""
import json, os, sys, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
NAVY, HONEY, CREAM, MUTE, WHITE, HOT = (20, 33, 61), (255, 200, 61), (255, 246, 224), (169, 178, 200), (255, 255, 255), (229, 72, 77)
FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
def font(sz, bold=True): return ImageFont.truetype(FB if bold else FR, sz, index=1)
def tw(d, s, f): b = d.textbbox((0, 0), s, font=f); return b[2] - b[0], b[3] - b[1]

def ctext(d, y, s, f, fill, stroke=0, shadow=True, x=None):
    w, h = tw(d, s, f); x = (W - w) // 2 if x is None else x
    if shadow: d.text((x + 3, y + 5), s, font=f, fill=(0, 0, 0, 150))
    d.text((x, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=fill)
    return h

def pill(d, y, s, f, bg, fg, padx=28, pady=12, r=18, cx=None):
    w, h = tw(d, s, f); cx = W // 2 if cx is None else cx; x0 = cx - w // 2 - padx
    d.rounded_rectangle([x0, y, x0 + w + 2 * padx, y + h + 2 * pady + 8], r, fill=bg)
    d.text((cx - w // 2, y + pady - 2), s, font=f, fill=fg, stroke_width=1, stroke_fill=fg)
    return h + 2 * pady + 8

def brand(d):
    d.ellipse([60, 150, 128, 218], fill=HONEY)
    d.text((94, 166), "MIGOOK", font=font(9), fill=NAVY, anchor="mm")
    d.text((94, 192), "꿀템", font=font(22), fill=NAVY, anchor="mm")
    d.text((142, 165), "미국꿀템", font=font(30), fill=WHITE, stroke_width=1, stroke_fill=WHITE)
    f = font(26); w, h = tw(d, "광고", f)
    d.rounded_rectangle([W - 60 - w - 28, 160, W - 60, 160 + h + 22], 10, fill=WHITE)
    d.text((W - 60 - w - 14, 164), "광고", font=f, fill=NAVY)

def plate(src, out, scale=0.68, top=70):
    """Product image shrunk and lifted over a blurred copy of itself, so the product sits clear of the text."""
    im = Image.open(src).convert("RGB")
    # backdrop from the image's own left/right edge columns (no product in it -> no ghosting)
    e = im.resize((W, H)); a = __import__("numpy").asarray(e).astype("float32")
    col = (a[:, :40].mean(1) + a[:, -40:].mean(1)) / 2
    bg = Image.fromarray(__import__("numpy").repeat(col[:, None, :], W, 1).astype("uint8")).filter(ImageFilter.GaussianBlur(30))
    fw = int(W * scale); fh = int(im.height * fw / im.width)
    fg = im.resize((fw, fh), Image.LANCZOS)
    m = Image.new("L", (fw, fh), 0); md = ImageDraw.Draw(m); fe = 120
    for i in range(fe): md.rectangle([i, i, fw - i, fh - i], outline=int(255 * (i / fe) ** 1.6))
    md.rectangle([fe, fe, fw - fe, fh - fe], fill=255)
    bg.paste(fg, ((W - fw) // 2, top), m)
    bg.save(out, quality=95)

def shade(sd, y0, y1, a0, a1):
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0); sd.line([(0, y), (W, y)], fill=NAVY + (int(a0 + (a1 - a0) * t),))

def item_overlays(it, i, n, asof, out):
    """Base overlay (badge, counter, name) and pop overlay (reason, price, history) drawn separately."""
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(base)
    shade(sd, 0, 330, 200, 0); shade(sd, 1060, 1250, 0, 215); shade(sd, 1250, H, 215, 235)
    d = ImageDraw.Draw(base); brand(d)
    hot = it["badge"] != "꿀템"
    pill(d, 250, it["badge"], font(42), HOT if hot else CREAM, WHITE if hot else NAVY, padx=34, pady=14, r=22)
    pill(d, 252, f"{i}/{n}", font(26), NAVY + (190,), WHITE, padx=16, pady=8, r=14, cx=W - 120)
    y = 1150
    y += ctext(d, y, it["name"], font(62), WHITE, stroke=1) + 18
    ctext(d, y, it["sub"], font(34, False), CREAM)
    base.save(os.path.join(out, f"b{i}.png"))

    pop = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(pop)
    y = 1290
    y += pill(d, y, it["reason"], font(32), CREAM, NAVY) + 22
    fp, fr = font(118), font(44, False)
    pw, ph = tw(d, it["price"], fp); rw, rh = tw(d, it["ref"], fr); gap = 30
    x0 = (W - pw - gap - rw) // 2
    ctext(d, y, it["price"], fp, HONEY, stroke=3, x=x0)
    ry = y + ph - rh + 6
    ctext(d, ry, it["ref"], fr, MUTE, x=x0 + pw + gap, shadow=False)
    d.line([(x0 + pw + gap - 4, ry + rh // 2 + 10), (x0 + pw + gap + rw + 4, ry + rh // 2 + 10)], fill=HOT, width=5)
    y += ph + 44
    y += ctext(d, y, it["history"], font(30), WHITE) + 14
    ctext(d, y, f"{it['rating']} · {asof} 아마존 가격 기준", font(26, False), MUTE)
    pop.save(os.path.join(out, f"p{i}.png"))

def intro_overlay(cfg, out):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(im)
    shade(sd, 0, 900, 225, 40); shade(sd, 900, H, 40, 120)
    d = ImageDraw.Draw(im); brand(d)
    y = 300
    y += pill(d, y, cfg["kicker"], font(42), HONEY, NAVY, padx=34, pady=14, r=22) + 30
    for ln in cfg["title"].split("\n"):
        y += ctext(d, y, ln, font(96), WHITE, stroke=3) + 28
    im.save(os.path.join(out, "intro.png"))

def endcard(cfg, out):
    im = Image.new("RGB", (W, H), NAVY); d = ImageDraw.Draw(im); brand(d)
    y = 290
    y += pill(d, y, "가격 이력 직접 확인", font(36), HONEY, NAVY) + 26
    y += ctext(d, y, cfg["end"]["title"], font(70), WHITE, stroke=2, shadow=False) + 50
    for it in cfg["items"]:
        d.rounded_rectangle([90, y, W - 90, y + 150], 24, fill=(30, 47, 85))
        hot = it["badge"] != "꿀템"
        pill(d, y + 22, it["badge"], font(24), HOT if hot else CREAM, WHITE if hot else NAVY, padx=16, pady=6, r=12, cx=90 + 30 + tw(d, it["badge"], font(24))[0] // 2 + 16)
        d.text((122, y + 78), it["short"], font=font(38), fill=WHITE)
        f = font(56); pw, _ = tw(d, it["price"], f)
        d.text((W - 122 - pw, y + 30), it["price"], font=f, fill=HONEY, stroke_width=1, stroke_fill=HONEY)
        f2 = font(26, False); rw, _ = tw(d, it["ref"], f2)
        d.text((W - 122 - rw, y + 106), it["ref"], font=f2, fill=MUTE)
        y += 172
    y += 16
    y += ctext(d, y, f"{cfg['asof']} 아마존 가격 기준 · 가격은 바뀔 수 있어요", font(26, False), MUTE, shadow=False) + 34
    y += pill(d, y, cfg["end"]["cta"], font(50), HONEY, NAVY, padx=60, pady=24, r=26) + 26
    ctext(d, y, "저장해두고 블프 전에 다시 보기", font(30, False), WHITE, shadow=False)
    ctext(d, H - 330, "광고 · 아마존 제휴링크 포함", font(24, False), MUTE, shadow=False)
    im.save(os.path.join(out, "end.png"))

def run(cmd): subprocess.run(cmd, check=True)
def enc(): return ["-an", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p"]

def zoom_still(src, dur, out_mp4, overlays, punch=True, fy=0.4):
    """src still -> zoompan (fast punch-in settle, then slow push), with overlays [(png, fade_in_start or None)]."""
    n = int(dur * FPS); k = 9
    z = f"if(lt(on,{k}),1.16-0.16*on/{k},1+0.05*(on-{k})/{n - k})" if punch else f"1+0.05*on/{n}"
    fc = (f"[0:v]scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
          f"zoompan=z='{z}':x='iw/2-iw/zoom/2':y='max(0,min(ih-ih/zoom,{fy}*ih-ih/zoom/2))':d={n}:s={W}x{H}:fps={FPS},setsar=1[v0]")
    ins = ["-loop", "1", "-i", src]; last = "v0"
    for j, (png, st) in enumerate(overlays, start=1):
        ins += ["-loop", "1", "-i", png]
        if st is None: fc += f";[{last}][{j}:v]overlay=0:0[v{j}]"
        else: fc += f";[{j}:v]format=rgba,fade=t=in:st={st}:d=0.18:alpha=1[o{j}];[{last}][o{j}]overlay=0:0[v{j}]"
        last = f"v{j}"
    fc += f";[{last}]format=yuv420p[vout]"
    run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", fc, "-map", "[vout]", "-t", str(dur), *enc(), out_mp4])

if __name__ == "__main__":
    cfg_path = sys.argv[1]; cfg = json.load(open(cfg_path, encoding="utf-8"))
    post = os.path.dirname(os.path.abspath(cfg_path)); root = os.path.dirname(os.path.dirname(post))
    out = os.path.join(post, "build"); os.makedirs(out, exist_ok=True)
    items, n, parts = cfg["items"], len(cfg["items"]), []
    plates = []
    for i, it in enumerate(items, start=1):
        p = os.path.join(out, f"plate{i}.jpg"); plate(os.path.join(root, it["src"]), p); plates.append(p)
        item_overlays(it, i, n, cfg["asof"], out)
    # intro: quick flash-cut through all products under the hook headline
    intro_overlay(cfg["intro"], out)
    beat = cfg["intro"]["dur"] / n
    for i, p in enumerate(plates, start=1):
        o = os.path.join(out, f"intro{i}.mp4")
        zoom_still(p, beat, o, [(os.path.join(out, "intro.png"), None)], punch=True); parts.append(o)
    for i, (it, p) in enumerate(zip(items, plates), start=1):
        o = os.path.join(out, f"item{i}.mp4")
        zoom_still(p, it.get("dur", 3.0), o, [(os.path.join(out, f"b{i}.png"), None), (os.path.join(out, f"p{i}.png"), 0.35)])
        parts.append(o)
    endcard(cfg, out); ep = os.path.join(out, "end.mp4")
    run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", os.path.join(out, "end.png"), "-t", str(cfg["end"]["dur"]),
         "-vf", f"fps={FPS},format=yuv420p,fade=t=in:st=0:d=0.25", *enc(), ep]); parts.append(ep)
    lst = os.path.join(out, "list.txt"); open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    total = cfg["intro"]["dur"] + sum(it.get("dur", 3.0) for it in items) + cfg["end"]["dur"]
    mp4 = os.path.join(post, cfg["slug"] + ".mp4")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
         "-f", "lavfi", "-t", str(total), "-i", "anullsrc=r=44100:cl=stereo",
         "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-profile:v", "high", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", mp4])
    cover = mp4.replace(".mp4", "-cover.jpg")
    run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(cfg["intro"]["dur"] + 1.5), "-i", mp4, "-frames:v", "1", "-q:v", "3", cover])
    print(mp4); print(cover); print(f"{total:.1f}s")
