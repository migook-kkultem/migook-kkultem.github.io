"""Build 미국꿀템 carousel slides (1080x1350 JPEG) from AI scene images + verified deal data."""
import json, os, sys, html
from playwright.sync_api import sync_playwright
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

BASE_CSS = """
:root{--navy:#14213D;--navy2:#1E2F55;--honey:#FFC83D;--cream:#FFF6E0;--hot:#E5484D;--mute:#A9B2C8}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1350px;overflow:hidden}
body{font-family:"Noto Sans CJK KR",sans-serif;word-break:keep-all;background:var(--navy);color:#fff;position:relative}
.bg{position:absolute;inset:0;background-size:cover;background-position:center}
.ad{position:absolute;top:40px;right:44px;font-size:24px;font-weight:700;color:var(--navy);background:#fff;border-radius:10px;padding:4px 14px;z-index:5}
.ai{position:absolute;font-size:20px;font-weight:500;color:rgba(255,255,255,.85);background:rgba(20,33,61,.55);padding:4px 12px;border-radius:8px;z-index:5}
.brand{position:absolute;top:36px;left:44px;display:flex;align-items:center;gap:12px;z-index:5}
.dot{width:58px;height:58px;border-radius:50%;background:var(--honey);display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--navy);box-shadow:0 2px 10px rgba(0,0,0,.25)}
.dot small{font-size:8px;letter-spacing:2px;font-weight:700;line-height:1}
.dot b{font-size:19px;font-weight:900;line-height:1.1}
.brand span{font-size:26px;font-weight:900;text-shadow:0 2px 8px rgba(0,0,0,.45)}
.badge{display:inline-block;font-size:28px;font-weight:900;padding:6px 18px;border-radius:12px}
.b-hot{background:var(--hot);color:#fff}.b-low{background:var(--honey);color:var(--navy)}.b-good{background:#fff;color:var(--navy)}
"""

def esc(s): return html.escape(str(s))

def badge_cls(b): return {"핫딜":"b-hot","최저가":"b-low"}.get(b, "b-low" if "최저" in b else "b-good")

def ref_html(it):
    # strike=false -> plain reference (e.g. "1년 최저 $64.99") for 세일 대기 items
    if it.get("strike", True): return f"{esc(it['was_label'])} <s>{esc(it['was'])}</s>"
    return f"{esc(it['was_label'])} {esc(it['was'])}"

def off_txt(it):
    return f"-{it['off']}%" if it.get("off") is not None else esc(it.get("off_text", ""))

def hook_html(d, img):
    tiles = "".join(f"""
      <div class="tile">
        <div class="tn">{i+1}</div>
        <div class="tname">{esc(it['short'])}</div>
        <div class="tp">{esc(it['price'])}</div>
        <div class="tw">{ref_html(it)}</div>
        <div class="toff">{off_txt(it)}</div>
      </div>""" for i, it in enumerate(d["items"]))
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}
    .bg{{background-image:url('{img}')}}
    .shade{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(20,33,61,.96) 0%,rgba(20,33,61,.85) 24%,rgba(20,33,61,0) 36%,rgba(20,33,61,0) 66%,rgba(20,33,61,.9) 80%,rgba(20,33,61,1) 100%)}}
    .head{{position:absolute;top:104px;left:0;right:0;text-align:center;z-index:4}}
    .kicker{{display:inline-block;font-size:34px;font-weight:900;color:var(--navy);background:var(--honey);padding:6px 22px;border-radius:14px;transform:rotate(-2deg)}}
    h1{{margin-top:10px;font-size:132px;font-weight:900;letter-spacing:-6px;line-height:1;text-shadow:0 6px 24px rgba(0,0,0,.45)}}
    h1 em{{font-style:normal;color:var(--honey)}}
    .sub{{margin-top:8px;font-size:30px;font-weight:700;color:#fff;text-shadow:0 2px 10px rgba(0,0,0,.6)}}
    .strip{{position:absolute;left:28px;right:28px;bottom:70px;display:grid;grid-template-columns:repeat({len(d['items'])},1fr);gap:12px;z-index:4}}
    .tile{{background:var(--cream);color:var(--navy);border-radius:20px;padding:16px 10px 14px;text-align:center;position:relative;box-shadow:0 8px 24px rgba(0,0,0,.35)}}
    .tn{{position:absolute;top:-16px;left:50%;transform:translateX(-50%);width:34px;height:34px;border-radius:50%;background:var(--navy);color:var(--honey);font-size:20px;font-weight:900;display:flex;align-items:center;justify-content:center;border:3px solid var(--honey)}}
    .tname{{white-space:pre-line;margin-top:12px;font-size:21px;font-weight:700;line-height:1.25;height:54px;display:flex;align-items:center;justify-content:center}}
    .tp{{margin-top:6px;font-size:36px;font-weight:900;letter-spacing:-1px;color:var(--hot)}}
    .tw{{font-size:17px;color:#6B7389}}
    .toff{{margin-top:6px;display:inline-block;font-size:20px;font-weight:900;background:var(--navy);color:var(--honey);border-radius:8px;padding:1px 10px}}
    .foot{{position:absolute;left:0;right:0;bottom:22px;text-align:center;font-size:22px;color:var(--mute);z-index:4}}
    .ai{{left:44px;top:1000px}}
    </style></head><body>
    <div class="bg"></div><div class="shade"></div>
    <div class="brand"><div class="dot"><small>MIGOOK</small><b>꿀템</b></div><span>미국꿀템</span></div>
    <div class="ad">광고</div>
    <div class="head"><div class="kicker">{esc(d['kicker'])}</div><h1>{d['title_html']}</h1><div class="sub">{esc(d['sub'])}</div></div>
    <div class="strip">{tiles}</div>
    <div class="foot">{esc(d['asof'])} 아마존 가격 기준 · 가격은 바뀔 수 있어요 · 옆으로 넘겨보세요 →</div>
    </body></html>"""

def item_html(d, it, idx, n, img):
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}
    .bg{{background-image:url('{img}')}}
    .shade{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(20,33,61,.55) 0%,rgba(20,33,61,0) 16%,rgba(20,33,61,0) 50%,rgba(20,33,61,.85) 64%,rgba(20,33,61,1) 76%)}}
    .num{{position:absolute;top:118px;left:44px;font-size:26px;font-weight:900;color:var(--navy);background:var(--honey);border-radius:999px;padding:4px 18px;z-index:5}}
    .ai{{right:44px;top:120px}}
    .panel{{position:absolute;left:56px;right:56px;bottom:58px;z-index:4}}
    .name{{margin-top:18px;font-size:58px;font-weight:900;letter-spacing:-2px;line-height:1.12}}
    .who{{margin-top:12px;font-size:32px;font-weight:500;color:#DCE2EF}}
    .row{{margin-top:26px;display:flex;align-items:flex-end;gap:24px}}
    .p{{font-size:128px;font-weight:900;color:var(--honey);letter-spacing:-5px;line-height:.9}}
    .side{{padding-bottom:10px}}
    .w{{font-size:30px;color:var(--mute)}}.w s{{color:var(--mute)}}
    .off{{margin-top:4px;font-size:38px;font-weight:900}}
    .hist{{margin-top:22px;font-size:26px;font-weight:700;color:var(--navy);background:var(--cream);display:inline-block;padding:8px 18px;border-radius:12px}}
    .asof{{margin-top:14px;font-size:22px;color:var(--mute)}}
    </style></head><body>
    <div class="bg"></div><div class="shade"></div>
    <div class="brand"><div class="dot"><small>MIGOOK</small><b>꿀템</b></div><span>미국꿀템</span></div>
    <div class="ad">광고</div>
    <div class="num">{idx}/{n}</div>
    <div class="panel">
      <span class="badge {badge_cls(it['badge'])}">{esc(it['badge'])}</span>
      <div class="name">{esc(it['name'])}</div>
      <div class="who">{esc(it['who'])}</div>
      <div class="row"><div class="p">{esc(it['price'])}</div>
        <div class="side"><div class="w">{ref_html(it)}</div><div class="off">{off_txt(it)}</div></div></div>
      <div class="hist">📈 {esc(it['history'])}</div>
      <div class="asof">{esc(d['asof'])} 아마존 가격 기준 · 가격은 바뀔 수 있어요</div>
    </div></body></html>"""

def cta_html(d):
    rows = "".join(f"<li><span>{i+1}. {esc(it['short'])}</span><b>{esc(it['price'])}</b></li>" for i, it in enumerate(d["items"]))
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}
    .wrap{{position:absolute;inset:0;padding:200px 80px 0}}
    .big{{width:150px;height:150px;border-radius:50%;background:var(--honey);color:var(--navy);display:flex;flex-direction:column;align-items:center;justify-content:center;margin:0 auto}}
    .big small{{font-size:18px;letter-spacing:4px;font-weight:700}}.big b{{font-size:50px;font-weight:900;line-height:1.05}}
    h2{{margin-top:36px;text-align:center;font-size:72px;font-weight:900;letter-spacing:-2px;line-height:1.15}}
    h2 em{{font-style:normal;color:var(--honey)}}
    ul{{margin-top:44px;list-style:none;background:var(--navy2);border-radius:28px;padding:22px 36px}}
    li{{display:flex;justify-content:space-between;font-size:32px;padding:12px 0;border-bottom:1px solid rgba(255,255,255,.08)}}
    li:last-child{{border:none}} li b{{color:var(--honey);font-weight:900}}
    .acts{{margin-top:48px;display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}
    .act{{background:var(--honey);color:var(--navy);border-radius:20px;text-align:center;padding:22px 8px;font-size:30px;font-weight:900;line-height:1.3}}
    .act small{{display:block;font-size:22px;font-weight:700}}
    .note{{position:absolute;left:0;right:0;bottom:40px;text-align:center;font-size:20px;color:var(--mute)}}
    </style></head><body><div class="wrap">
      <div class="big"><small>MIGOOK</small><b>꿀템</b></div>
      <h2>링크는 <em>프로필</em>에 있어요</h2>
      <ul>{rows}</ul>
      <div class="acts"><div class="act">🔖 저장<small>블프 전에 다시 보기</small></div><div class="act">📤 공유<small>필요한 친구에게</small></div><div class="act">➕ 팔로우<small>매일 진짜 딜만</small></div></div>
    </div>
    <div class="note">광고 · 아마존 제휴링크 포함 · {esc(d['asof'])} 기준</div>
    </body></html>"""

def render(html_str, name, page):
    path = os.path.join(OUT, name + ".html")
    open(path, "w", encoding="utf-8").write(html_str)
    page.goto("file://" + path); page.wait_for_timeout(700)
    png = os.path.join(OUT, name + ".png"); page.screenshot(path=png)
    jpg = os.path.join(OUT, name + ".jpg")
    Image.open(png).convert("RGB").save(jpg, "JPEG", quality=92, optimize=True); os.remove(png)
    return jpg

if __name__ == "__main__":
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    absp = lambda x: "file://" + os.path.join(HERE, x)
    d["hook_img"] = absp(d["hook_img"])
    for it in d["items"]: it["img"] = absp(it["img"])
    prefix = d["slug"]
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width":1080,"height":1350})
        files = [render(hook_html(d, d["hook_img"]), f"{prefix}-01", pg)]
        for i, it in enumerate(d["items"], 1):
            files.append(render(item_html(d, it, i, len(d["items"]), it["img"]), f"{prefix}-{i+1:02d}", pg))
        files.append(render(cta_html(d), f"{prefix}-{len(d['items'])+2:02d}", pg))
        b.close()
    print("\n".join(files))
