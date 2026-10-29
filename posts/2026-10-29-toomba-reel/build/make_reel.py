from PIL import Image, ImageDraw, ImageFilter, ImageFont
import subprocess

W, H = 1080, 1920
NAVY, NAVY2, HONEY, WHITE = (20, 33, 61), (30, 47, 85), (255, 200, 61), (255, 255, 255)
F = '/usr/share/fonts/opentype/noto/NotoSansCJK-{}.ttc'
def font(w, s): return ImageFont.truetype(F.format(w), s, index=1)

src = Image.open('hero.jpg').convert('RGB')

# ---- background: blurred cover fill + sharp image scaled 0.88, feathered ----
S, OFFY = 0.86, 45
bg = src.resize((W, H)).filter(ImageFilter.GaussianBlur(40))
sw, sh = int(W * S), int(H * S)
sharp = src.resize((sw, sh), Image.LANCZOS)
mask = Image.new('L', (sw, sh), 0)
ImageDraw.Draw(mask).rectangle([28, 28, sw - 28, sh - 28], fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(22))
bg.paste(sharp, ((W - sw) // 2, OFFY), mask)
bg.save('bg.png')

def ctext(d, y, s, f, fill):
    w = d.textlength(s, font=f); d.text(((W - w) / 2, y), s, font=f, fill=fill)

# ---- overlay (transparent PNG drawn on top of the moving background) ----
ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
# top navy gradient for legibility
grad = Image.new('L', (1, 560))
for y in range(560): grad.putpixel((0, y), int(235 * max(0, 1 - y / 560) ** 1.3))
top = Image.new('RGBA', (W, 560), NAVY + (0,)); top.putalpha(grad.resize((W, 560)))
ov.alpha_composite(top)
d = ImageDraw.Draw(ov)

# 광고 chip (top-left, inside safe area)
d.rounded_rectangle([70, 228, 150, 268], 10, fill=(255, 255, 255, 230))
d.text((84, 231), '광고', font=font('Bold', 24), fill=NAVY)

ctext(d, 228, '가격 이력 직접 확인', font('Bold', 34), HONEY)
ctext(d, 268, '신라면 툼바', font('Black', 92), WHITE)
ctext(d, 380, '1년 중 최저가 떴어요', font('Black', 50), HONEY)

# price card, symmetric 110px margins (clear of IG right rail)
X0, X1, Y0, Y1 = 110, 970, 1376, 1600
d.rounded_rectangle([X0, Y0, X1, Y1], 30, fill=NAVY + (240,), outline=HONEY, width=4)
# badge
bf = font('Black', 30); bw = d.textlength('최저가', font=bf)
d.rounded_rectangle([X0 + 34, Y0 + 26, X0 + 34 + bw + 32, Y0 + 72], 12, fill=HONEY)
d.text((X0 + 50, Y0 + 26), '최저가', font=bf, fill=NAVY)
# big price
pf = font('Black', 112)
d.text((X0 + 30, Y0 + 62), '$5.49', font=pf, fill=HONEY)
# right column
rx = 540
wf = font('Bold', 40)
was = '$7.77'; ww = d.textlength(was, font=wf)
d.text((rx, Y0 + 30), was, font=wf, fill=(200, 205, 220))
d.line([rx - 2, Y0 + 58, rx + ww + 2, Y0 + 58], fill=(200, 205, 220), width=4)
d.text((rx + ww + 18, Y0 + 30), '-29%', font=font('Black', 40), fill=(255, 107, 107))
d.text((rx, Y0 + 90), '가격 추적 1년 중 최저가', font=font('Bold', 30), fill=WHITE)
d.text((rx, Y0 + 134), '4.83oz × 4봉 · ★4.4 (575)', font=font('Medium', 27), fill=(210, 215, 230))
d.text((rx, Y0 + 176), '10/29 오후 기준 · 가격 변동 가능', font=font('Medium', 23), fill=(170, 178, 200))
# shadow for the footer line
ov.save('overlay.png')

# ---- end card ----
ec = Image.new('RGB', (W, H), NAVY); e = ImageDraw.Draw(ec)
e.rounded_rectangle([70, 228, 150, 268], 10, fill=WHITE)
e.text((84, 231), '광고', font=font('Bold', 24), fill=NAVY)
cx, cy, r = W // 2, 600, 130
e.ellipse([cx - r, cy - r, cx + r, cy + r], fill=HONEY)
ctext(e, cy - 66, '꿀템', font('Black', 96), NAVY)
ctext(e, 800, '링크는 프로필에 있어요', font('Black', 70), WHITE)
ctext(e, 910, '신라면 툼바 4봉  $5.49', font('Bold', 48), HONEY)
ctext(e, 985, '10/29 오후 기준 · 가격은 바뀔 수 있어요', font('Medium', 28), (200, 205, 220))
bx = [(170, '저장'), (430, '공유'), (690, '팔로우')]
for x, t in bx:
    e.rounded_rectangle([x, 1110, x + 220, 1200], 45, fill=NAVY2, outline=HONEY, width=3)
    tw = e.textlength(t, font=font('Bold', 38)); e.text((x + 110 - tw / 2, 1128), t, font=font('Bold', 38), fill=WHITE)
ctext(e, 1270, '@migook.kkultem', font('Bold', 44), WHITE)
ec.save('endcard.png')

# ---- video: 5s centered 3% push-in + overlay, then 3s end card ----
fps, n = 30, 150
vf = (f"[0:v]scale=2160:3840,zoompan=z='1+0.03*on/{n-1}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
      f":d={n}:s={W}x{H}:fps={fps}[bgv];[bgv][1:v]overlay=0:0,format=yuv420p[a];"
      f"[2:v]format=yuv420p[b];[a][b]concat=n=2:v=1[v]")
subprocess.run(['ffmpeg', '-y', '-i', 'bg.png', '-loop', '1', '-t', '5', '-i', 'overlay.png',
                '-loop', '1', '-t', '3', '-framerate', str(fps), '-i', 'endcard.png',
                '-filter_complex', vf, '-map', '[v]', '-t', '8', '-r', str(fps),
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart', '2026-10-29-toomba-reel.mp4'], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
