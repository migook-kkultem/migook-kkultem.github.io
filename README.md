# 미국꿀템 publisher

- `docs/` = public website (GitHub Pages): deal page `index.html` + post images in `docs/img/`
- `posts/<date-name>/` = one Instagram post: `caption.txt`, `image_urls.txt`, `story.txt`
- `publish.py` = posts to @migook.kkultem (asks y/n first)
- `.env` = Page ID, IG User ID, token — git-ignored, never commit or share

## Post flow
1. Re-check price → fill every `__` placeholder in caption.txt
2. Save image as JPEG in `docs/img/`, push to GitHub, wait ~1 min → https://migook-kkultem.github.io/img/<file>.jpg
3. `python3 publish.py post posts/<folder> --dry-run`
4. `python3 publish.py post posts/<folder>` → review → type `y`
5. Post the Story with link sticker manually from the phone
