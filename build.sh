#!/bin/sh
# 1. setzt tools/lgtv.py (HTML-maskiert) in src/content.html ein
# 2. baut daraus index.html (für Vercel/GitHub Pages)
set -e
cd "$(dirname "$0")"
python3 - <<'PY'
import html, re
src = "src/content.html"
s = open(src, encoding="utf-8").read()
code = html.escape(open("tools/lgtv.py", encoding="utf-8").read(), quote=False)
s = re.sub(r"<!--LGTV_PY_START-->.*?<!--LGTV_PY_END-->",
           lambda m: "<!--LGTV_PY_START-->" + code + "<!--LGTV_PY_END-->", s, flags=re.S)
open(src, "w", encoding="utf-8").write(s)
PY
{
  printf '<!doctype html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
  cat src/content.html
  printf '\n</html>\n'
} > index.html
