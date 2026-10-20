"""Compose the 미국꿀템 hook Reel: AI clip + text overlay + end card -> 1080x1920 MP4 (H.264/AAC)."""
import json, os, sys, subprocess
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from carousel import BASE_CSS, esc, off_txt

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out")

def overlay_html(d):
    tiles = "".join(f"""<div class="tile"><div class="tn">{i+1}</div><div class="tname">{esc(it['short'])}</div>
      <div class="tp">{esc(it['price'])}</div><div class="toff">{off_txt(it)}</div></div>""" for i, it in enumerate(d["items"]))
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}
    html,body{{width:1080px;height:1920px;background:transparent}}
    .shade{{position:absolute;left:0;right:0;top:0;height:640px;background:linear-gradient(180deg,rgba(20,33,61,.95),rgba(20,33,61,.75) 60%,rgba(20,33,61,0))}}
    .shade2{{position:absolute;left:0;right:0;bottom:0;height:760px;background:linear-gradient(0deg,rgba(20,33,61,.97),rgba(20,33,61,.8) 55%,rgba(20,33,61,0))}}
    .brand{{top:120px}} .ad{{top:126px}}
    .head{{position:absolute;top:230px;left:0;right:0;text-align:center}}
    .kicker{{display:inline-block;font-size:40px;font-weight:900;color:var(--navy);background:var(--honey);padding:8px 26px;border-radius:16px;transform:rotate(-2deg)}}
    h1{{margin-top:14px;font-size:150px;font-weight:900;letter-spacing:-6px;line-height:1;text-shadow:0 6px 24px rgba(0,0,0,.45)}}
    h1 em{{font-style:normal;color:var(--honey)}}
    .strip{{position:absolute;left:110px;right:110px;bottom:420px;display:grid;grid-template-columns:repeat({len(d['items'])},1fr);gap:12px}}
    .tile{{background:var(--cream);color:var(--navy);border-radius:20px;padding:20px 8px 16px;text-align:center;position:relative}}
    .tn{{position:absolute;top:-18px;left:50%;transform:translateX(-50%);width:38px;height:38px;border-radius:50%;background:var(--navy);color:var(--honey);font-size:22px;font-weight:900;display:flex;align-items:center;justify-content:center;border:3px solid var(--honey)}}
    .tname{{white-space:pre-line;margin-top:10px;font-size:20px;font-weight:700;line-height:1.25;height:58px;display:flex;align-items:center;justify-content:center}}
    .tp{{margin-top:6px;font-size:32px;font-weight:900;color:var(--hot);letter-spacing:-1px}}
    .toff{{margin-top:6px;display:inline-block;font-size:22px;font-weight:900;background:var(--navy);color:var(--honey);border-radius:8px;padding:1px 10px}}
    .ai{{left:44px;bottom:660px}}
    .foot{{position:absolute;left:60px;right:60px;bottom:350px;font-size:26px !important;text-align:center;font-size:30px;font-weight:700;color:#fff}}
    .foot2{{position:absolute;left:60px;right:60px;bottom:318px;text-align:center;font-size:22px;color:var(--mute)}}
    </style></head><body>
    <div class="shade"></div><div class="shade2"></div>
    <div class="brand"><div class="dot"><small>MIGOOK</small><b>꿀템</b></div><span>미국꿀템</span></div>
    <div class="ad">광고</div>
    <div class="head"><div class="kicker">{esc(d['kicker'])}</div><h1>{d['title_html']}</h1></div>
    <div class="strip">{tiles}</div>
    <div class="foot">🔗 링크는 프로필에 · 자세한 가격 이력은 피드에</div>
    <div class="foot2">{esc(d['asof'])} 아마존 가격 기준 · 가격은 바뀔 수 있어요</div>
    </body></html>"""

def endcard_html(d):
    rows = "".join(f"<li><span>{i+1}. {esc(it['short'].replace(chr(10),' '))}</span><b>{esc(it['price'])}</b></li>" for i, it in enumerate(d["items"]))
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}
    html,body{{width:1080px;height:1920px}}
    .wrap{{position:absolute;inset:0;padding:330px 80px 0}}
    .big{{width:170px;height:170px;border-radius:50%;background:var(--honey);color:var(--navy);display:flex;flex-direction:column;align-items:center;justify-content:center;margin:0 auto}}
    .big small{{font-size:20px;letter-spacing:4px;font-weight:700}}.big b{{font-size:56px;font-weight:900;line-height:1.05}}
    h2{{margin-top:40px;text-align:center;font-size:84px;font-weight:900;letter-spacing:-2px;line-height:1.15}} h2 em{{font-style:normal;color:var(--honey)}}
    ul{{margin-top:50px;list-style:none;background:var(--navy2);border-radius:28px;padding:26px 40px}}
    li{{display:flex;justify-content:space-between;font-size:38px;padding:14px 0;border-bottom:1px solid rgba(255,255,255,.08)}} li:last-child{{border:none}} li b{{color:var(--honey);font-weight:900}}
    .cta{{margin-top:56px;text-align:center;font-size:44px;font-weight:900;color:var(--navy);background:var(--honey);border-radius:24px;padding:26px}}
    .note{{position:absolute;left:0;right:0;bottom:220px;text-align:center;font-size:24px;color:var(--mute)}}
    </style></head><body><div class="wrap">
      <div class="big"><small>MIGOOK</small><b>꿀템</b></div>
      <h2>링크는 <em>프로필</em>에</h2><ul>{rows}</ul>
      <div class="cta">팔로우하면 매일 진짜 딜만 🛒</div></div>
      <div class="note">광고 · 아마존 제휴링크 포함 · {esc(d['asof'])} 기준</div></body></html>"""

def shot(page, html_str, path, transparent=False):
    hp = path.replace(".png", ".html"); open(hp, "w", encoding="utf-8").write(html_str)
    page.goto("file://" + hp); page.wait_for_timeout(600)
    page.screenshot(path=path, omit_background=transparent)

if __name__ == "__main__":
    d = json.load(open(sys.argv[1], encoding="utf-8")); clip = sys.argv[2]; slug = d["slug"].replace("-deals", "-reel") if d["slug"].endswith("-deals") else d["slug"] + "-reel"
    ov, ec = os.path.join(OUT, slug + "-overlay.png"), os.path.join(OUT, slug + "-end.png")
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 1920})
        shot(pg, overlay_html(d), ov, transparent=True); shot(pg, endcard_html(d), ec); b.close()
    mp4 = os.path.join(OUT, slug + ".mp4")
    fc = ("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1[bg];"
          "[bg][1:v]overlay=0:0,format=yuv420p[a];"
          "[2:v]scale=1080:1920,fps=30,setsar=1,format=yuv420p,fade=t=in:st=0:d=0.3[b];"
          "[a][b]concat=n=2:v=1:a=0[v]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", clip, "-loop", "1", "-i", ov,
                    "-loop", "1", "-t", "3", "-i", ec, "-f", "lavfi", "-t", "8", "-i", "anullsrc=r=44100:cl=stereo",
                    "-filter_complex", fc.replace("[1:v]overlay=0:0", "[1:v]overlay=0:0:shortest=1"),
                    "-map", "[v]", "-map", "3:a", "-c:v", "libx264", "-profile:v", "high", "-preset", "medium",
                    "-crf", "20", "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", mp4], check=True)
    # cover = first frame with overlay
    cover = os.path.join(OUT, slug + "-cover.jpg")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.5", "-i", mp4, "-frames:v", "1", "-q:v", "3", cover], check=True)
    print(mp4); print(cover)
