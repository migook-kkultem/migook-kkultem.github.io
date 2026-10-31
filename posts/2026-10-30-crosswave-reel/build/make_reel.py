from PIL import Image, ImageDraw, ImageFilter, ImageFont
import subprocess

W, H = 1080, 1920
NAVY, NAVY2, HONEY, WHITE = (20, 33, 61), (30, 47, 85), (255, 200, 61), (255, 255, 255)
F = '/usr/share/fonts/opentype/noto/NotoSansCJK-{}.ttc'
def font(w, s): return ImageFont.truetype(F.format(w), s, index=1)
OUT = '2026-10-30-crosswave-reel'
ASOF = '10/30 밤 기준'

src = Image.open('hero.jpg').convert('RGB')

# ---- background: blurred fill + sharp scene at 0.86, top-aligned so the floor head clears the price card ----
S, OFFY = 0.86, 0
bg = src.resize((W, H)).filter(ImageFilter.GaussianBlur(40))
sw, sh = int(W * S), int(H * S)
sharp = src.resize((sw, sh), Image.LANCZOS)
mask = Image.new('L', (sw, sh), 0)
ImageDraw.Draw(mask).rectangle([28, 28, sw - 28, sh - 28], fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(22))
bg.paste(sharp, ((W - sw) // 2, OFFY), mask)
bg.save('bg.png')

def ctext(d, y, s, f, fill):
    w = d.textlength(s, font=f); d.text(((W - w) / 2, y), s, font=f, fill=fill); return w

ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
grad = Image.new('L', (1, 600))
for y in range(600): grad.putpixel((0, y), int(240 * max(0, 1 - y / 600) ** 1.2))
top = Image.new('RGBA', (W, 600), NAVY + (0,)); top.putalpha(grad.resize((W, 600)))
ov.alpha_composite(top)
d = ImageDraw.Draw(ov)

d.rounded_rectangle([70, 228, 150, 268], 10, fill=(255, 255, 255, 230))
d.text((84, 231), '광고', font=font('Bold', 24), fill=NAVY)

ctext(d, 228, '가격 이력 직접 확인', font('Bold', 34), HONEY)
ctext(d, 268, '비셀 크로스웨이브', font('Black', 88), WHITE)
ctext(d, 378, '역대 최저가 떴어요', font('Black', 52), HONEY)

X0, X1, Y0, Y1 = 110, 970, 1376, 1600
d.rounded_rectangle([X0, Y0, X1, Y1], 30, fill=NAVY + (240,), outline=HONEY, width=4)
bf = font('Black', 30); badge = '역대 최저가'; bw = d.textlength(badge, font=bf)
d.rounded_rectangle([X0 + 34, Y0 + 26, X0 + 34 + bw + 32, Y0 + 72], 12, fill=HONEY)
d.text((X0 + 50, Y0 + 26), badge, font=bf, fill=NAVY)
pf = font('Black', 100); price = '$140.39'
pw = d.textlength(price, font=pf)
d.text((X0 + 30, Y0 + 72), price, font=pf, fill=HONEY)
rx = int(X0 + 30 + pw + 36)
wf = font('Bold', 40); was = '$219.99'; ww = d.textlength(was, font=wf)
d.text((rx, Y0 + 30), was, font=wf, fill=(200, 205, 220))
d.line([rx - 2, Y0 + 58, rx + ww + 2, Y0 + 58], fill=(200, 205, 220), width=4)
d.text((rx + ww + 18, Y0 + 30), '-36%', font=font('Black', 40), fill=(255, 107, 107))
lines = [('2018년 추적 이래 최저가', font('Bold', 29), WHITE, 92),
         ('청소기+물걸레 · ★4.2 (2.5만)', font('Medium', 26), (210, 215, 230), 136),
         (ASOF + ' · 가격 변동 가능', font('Medium', 23), (170, 178, 200), 178)]
for t, f, c, dy in lines:
    d.text((rx, Y0 + dy), t, font=f, fill=c)
    assert rx + d.textlength(t, font=f) < X1 - 24, ('overflow', t, rx + d.textlength(t, font=f))
assert rx + ww + 18 + d.textlength('-36%', font=font('Black', 40)) < X1 - 24
print('price right edge', X0 + 30 + pw, 'rx', rx)
ov.save('overlay.png')

ec = Image.new('RGB', (W, H), NAVY); e = ImageDraw.Draw(ec)
e.rounded_rectangle([70, 228, 150, 268], 10, fill=WHITE)
e.text((84, 231), '광고', font=font('Bold', 24), fill=NAVY)
cx, cy, r = W // 2, 600, 130
e.ellipse([cx - r, cy - r, cx + r, cy + r], fill=HONEY)
ctext(e, cy - 66, '꿀템', font('Black', 96), NAVY)
ctext(e, 800, '링크는 프로필에 있어요', font('Black', 70), WHITE)
ctext(e, 910, '비셀 크로스웨이브  $140.39', font('Bold', 48), HONEY)
ctext(e, 985, ASOF + ' · 가격은 바뀔 수 있어요', font('Medium', 28), (200, 205, 220))
for x, t in [(170, '저장'), (430, '공유'), (690, '팔로우')]:
    e.rounded_rectangle([x, 1110, x + 220, 1200], 45, fill=NAVY2, outline=HONEY, width=3)
    tw = e.textlength(t, font=font('Bold', 38)); e.text((x + 110 - tw / 2, 1128), t, font=font('Bold', 38), fill=WHITE)
ctext(e, 1270, '@migook.kkultem', font('Bold', 44), WHITE)
ec.save('endcard.png')

# cover = first frame composite
cov = Image.open('bg.png').convert('RGBA'); cov.alpha_composite(ov)
cov.convert('RGB').save(OUT + '-cover.jpg', quality=90)

fps, n = 30, 150
vf = (f"[0:v]scale=2160:3840,zoompan=z='1+0.03*on/{n-1}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
      f":d={n}:s={W}x{H}:fps={fps}[bgv];[bgv][1:v]overlay=0:0,format=yuv420p[a];"
      f"[2:v]format=yuv420p[b];[a][b]concat=n=2:v=1[v]")
subprocess.run(['ffmpeg', '-y', '-i', 'bg.png', '-loop', '1', '-t', '5', '-i', 'overlay.png',
                '-loop', '1', '-t', '3', '-framerate', str(fps), '-i', 'endcard.png',
                '-filter_complex', vf, '-map', '[v]', '-t', '8', '-r', str(fps),
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart', OUT + '.mp4'], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
