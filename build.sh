#!/bin/sh
# Baut index.html (für Vercel/GitHub Pages) aus src/content.html
set -e
cd "$(dirname "$0")"
{
  printf '<!doctype html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
  cat src/content.html
  printf '\n</html>\n'
} > index.html
