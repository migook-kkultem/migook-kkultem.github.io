#!/usr/bin/env python3
"""
미국꿀템 (@migook.kkultem) Instagram publisher.

Usage (run from this folder in Terminal):
  python3 publish.py check                      # token + account + daily quota check
  python3 publish.py post posts/<post-folder>   # preview, ask y/n, then publish
  python3 publish.py post posts/<post-folder> --dry-run   # preview + validate only, no API calls

A post folder contains:
  caption.txt      the full caption (must start with "#광고")
  image_urls.txt   1 public JPEG URL per line (1 line = single post, 2-10 lines = carousel)
  -- or, for a Reel --
  video_url.txt    1 public MP4 URL (H.264/AAC, 9:16, 3-90s)
  cover_url.txt    (optional) 1 public JPEG URL used as the Reel cover

Nothing is posted until you type "y" at the prompt.
Only Python's standard library is used — no pip install needed.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API_VERSION = "v26.0"
GRAPH = f"https://graph.facebook.com/{API_VERSION}"
HERE = os.path.dirname(os.path.abspath(__file__))
REQUIRED_DISCLOSURE = "#광고"


# ---------- helpers ----------
def load_env(path=os.path.join(HERE, ".env")):
    if not os.path.exists(path):
        sys.exit(f"✗ .env not found at {path}")
    env = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    for key in ("MIGOOK_IG_USER_ID", "MIGOOK_IG_TOKEN"):
        if not env.get(key):
            sys.exit(f"✗ {key} is missing in .env")
    return env


def graph(method, path, token, params=None):
    params = dict(params or {})
    params["access_token"] = token
    url = f"{GRAPH}/{path.lstrip('/')}"
    data = None
    if method == "GET":
        url += "?" + urllib.parse.urlencode(params)
    else:
        data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode()).get("error", {})
            msg = f"{err.get('type')} {err.get('code')}: {err.get('message')}"
        except Exception:
            msg = str(e)
        sys.exit(f"✗ Meta API error on {path.split('?')[0]} → {msg}")
    except urllib.error.URLError as e:
        hint = ""
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            hint = ("\n  Fix (once): open /Applications/Python\\ 3*/Install\\ Certificates.command"
                    "\n  If that file doesn't exist: python3 -m pip install --upgrade certifi"
                    " && export SSL_CERT_FILE=$(python3 -m certifi)")
        sys.exit(f"✗ Network error: {e.reason}{hint}")


def check_image_url(url, want="image"):
    """Instagram fetches the media itself: it must be public, https, and JPEG (image) or MP4 (video)."""
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            ctype = r.headers.get("Content-Type", "")
    except Exception as e:
        return f"not reachable ({e})"
    if want == "video":
        return None if "mp4" in ctype else f"is {ctype or 'unknown type'} — Reels need MP4"
    if "jpeg" not in ctype and "jpg" not in ctype:
        return f"is {ctype or 'unknown type'} — Instagram API only accepts JPEG"
    return None


def read_post(folder):
    folder = os.path.join(HERE, folder) if not os.path.isabs(folder) else folder
    cap_path = os.path.join(folder, "caption.txt")
    vid_path = os.path.join(folder, "video_url.txt")
    url_path = vid_path if os.path.exists(vid_path) else os.path.join(folder, "image_urls.txt")
    for p in (cap_path, url_path):
        if not os.path.exists(p):
            sys.exit(f"✗ Missing {p}")
    caption = open(cap_path, encoding="utf-8").read().strip()
    rd = lambda p: [l.strip() for l in open(p, encoding="utf-8") if l.strip() and not l.strip().startswith("#")]
    urls = rd(url_path)
    cover = None
    if url_path == vid_path:
        cp = os.path.join(folder, "cover_url.txt")
        cover = (rd(cp) or [None])[0] if os.path.exists(cp) else None
    return folder, caption, urls, (url_path == vid_path), cover


def validate(caption, urls):
    problems = []
    if not caption.startswith(REQUIRED_DISCLOSURE):
        problems.append(f'caption must start with "{REQUIRED_DISCLOSURE}" (ad disclosure)')
    if len(caption) > 2200:
        problems.append(f"caption is {len(caption)} chars (max 2,200)")
    tags = [w for w in caption.split() if w.startswith("#")]
    if len(tags) > 5:
        problems.append(f"{len(tags)} hashtags (Instagram now allows max 5, incl. #광고)")
    if "__" in caption:
        problems.append('caption still has a "__" placeholder (unverified price/date?)')
    if not urls:
        problems.append("image_urls.txt has no URLs")
    if len(urls) > 10:
        problems.append(f"{len(urls)} images (carousel max 10)")
    for u in urls:
        if not u.startswith("https://"):
            problems.append(f"not an https URL: {u}")
        if "YOUR-GITHUB" in u:
            problems.append(f"placeholder URL not replaced: {u}")
    return problems


def wait_ready(container_id, token, label, tries=30):
    for _ in range(tries):  # 2s each
        st = graph("GET", container_id, token, {"fields": "status_code,status"})
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            sys.exit(f"✗ {label} failed to process: {st.get('status')}")
        time.sleep(2)
    sys.exit(f"✗ {label} still processing after {tries*2}s — nothing was published. Try again.")


# ---------- commands ----------
def cmd_check():
    env = load_env()
    tok, ig = env["MIGOOK_IG_TOKEN"], env["MIGOOK_IG_USER_ID"]
    acct = graph("GET", ig, tok, {"fields": "id,username,media_count,followers_count"})
    print(f"✓ Account: @{acct.get('username')}  (posts {acct.get('media_count')}, "
          f"followers {acct.get('followers_count')})")
    if acct.get("username") != "migook.kkultem":
        print("⚠ This is NOT @migook.kkultem — check MIGOOK_IG_USER_ID / token.")
    dbg = graph("GET", "debug_token", tok, {"input_token": tok}).get("data", {})
    exp = dbg.get("expires_at")
    print(f"✓ Token valid: {dbg.get('is_valid')}  app: {dbg.get('application')}  "
          f"expires: {'never' if not exp else time.strftime('%Y-%m-%d', time.localtime(exp))}")
    scopes = set(dbg.get("scopes", []))
    missing = {"instagram_basic", "instagram_content_publish"} - scopes
    print("✓ Publish permission OK" if not missing else f"✗ Missing scopes: {', '.join(missing)}")
    q = graph("GET", f"{ig}/content_publishing_limit", tok, {"fields": "config,quota_usage"})
    d = (q.get("data") or [{}])[0]
    print(f"✓ Posts used in last 24h: {d.get('quota_usage')} / {d.get('config', {}).get('quota_total')}")


def cmd_post(folder, dry_run=False, force=False):
    env = load_env()
    tok, ig = env["MIGOOK_IG_TOKEN"], env["MIGOOK_IG_USER_ID"]
    folder, caption, urls, is_reel, cover = read_post(folder)

    log_path = os.path.join(folder, "published.json")
    if os.path.exists(log_path) and not force:
        sys.exit(f"✗ Already published (see {log_path}). Use --force to post again.")

    problems = validate(caption, urls)
    if not dry_run:
        for u in urls:
            err = check_image_url(u, "video" if is_reel else "image")
            if err:
                problems.append(f"media {u} {err}")
        if cover:
            err = check_image_url(cover)
            if err:
                problems.append(f"cover {cover} {err}")
    if problems:
        print("✗ Fix these before posting:")
        for p in problems:
            print("   -", p)
        sys.exit(1)

    if is_reel and len(urls) != 1:
        sys.exit("✗ video_url.txt must contain exactly 1 URL")
    kind = "Reel (video)" if is_reel else ("single image" if len(urls) == 1 else f"carousel ({len(urls)} images)")
    print("=" * 60)
    print(f"Account : @migook.kkultem (IG {ig})")
    print(f"Type    : {kind}")
    for i, u in enumerate(urls, 1):
        print(f"{'Video' if is_reel else 'Image'} {i} : {u}")
    if cover:
        print(f"Cover   : {cover}")
    print(f"Caption : {len(caption)} chars")
    print("-" * 60)
    print(caption)
    print("=" * 60)

    if dry_run:
        print("✓ Dry run passed — nothing was sent to Instagram.")
        return

    if input('Post this to @migook.kkultem? Type "y" to publish: ').strip().lower() != "y":
        print("Cancelled. Nothing was posted.")
        return

    if is_reel:
        params = {"media_type": "REELS", "video_url": urls[0], "caption": caption, "share_to_feed": "true"}
        if cover:
            params["cover_url"] = cover
        c = graph("POST", f"{ig}/media", tok, params)
        creation_id = c["id"]
        wait_ready(creation_id, tok, "Reel", tries=90)
    elif len(urls) == 1:
        c = graph("POST", f"{ig}/media", tok, {"image_url": urls[0], "caption": caption})
        creation_id = c["id"]
        wait_ready(creation_id, tok, "Image")
    else:
        children = []
        for i, u in enumerate(urls, 1):
            c = graph("POST", f"{ig}/media", tok, {"image_url": u, "is_carousel_item": "true"})
            wait_ready(c["id"], tok, f"Image {i}")
            children.append(c["id"])
        c = graph("POST", f"{ig}/media", tok,
                  {"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption})
        creation_id = c["id"]
        wait_ready(creation_id, tok, "Carousel")

    pub = graph("POST", f"{ig}/media_publish", tok, {"creation_id": creation_id})
    media_id = pub["id"]
    info = graph("GET", media_id, tok, {"fields": "permalink,timestamp"})
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({"media_id": media_id, **info, "images": urls}, f, ensure_ascii=False, indent=2)
    print(f"✓ Published: {info.get('permalink')}")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    if args[0] == "check":
        cmd_check()
    elif args[0] == "post" and len(args) >= 2:
        cmd_post(args[1], dry_run="--dry-run" in args, force="--force" in args)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
