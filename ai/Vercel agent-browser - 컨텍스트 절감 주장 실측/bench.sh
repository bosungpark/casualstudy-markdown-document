#!/usr/bin/env bash
# agent-browser 컨텍스트 절감 주장 검증
# "snapshot ~200-400 tokens vs full DOM ~3,000-5,000 tokens" (agent-browser.dev)
set -u
AB=./node_modules/.bin/agent-browser
OUT=out
mkdir -p "$OUT"

URLS=(
  "https://example.com"
  "https://news.ycombinator.com"
  "https://github.com/vercel-labs/agent-browser"
  "https://en.wikipedia.org/wiki/Web_browser"
)

for url in "${URLS[@]}"; do
  slug=$(echo "$url" | sed -E 's#https?://##; s#[^a-zA-Z0-9]+#_#g' | cut -c1-40)
  echo "### $url  ($slug)" >&2
  timeout 120 $AB open "$url" >/dev/null 2>&1
  timeout 60  $AB wait --load networkidle >/dev/null 2>&1
  sleep 2

  timeout 60 $AB eval "document.documentElement.outerHTML" --max-output 100000000 > "$OUT/${slug}__rawdom.txt"  2>&1
  timeout 60 $AB read                                      --max-output 100000000 > "$OUT/${slug}__read.txt"    2>&1
  timeout 60 $AB snapshot                                  --max-output 100000000 > "$OUT/${slug}__snap.txt"    2>&1
  timeout 60 $AB snapshot -c                               --max-output 100000000 > "$OUT/${slug}__snap_c.txt"  2>&1
  timeout 60 $AB snapshot -i                               --max-output 100000000 > "$OUT/${slug}__snap_i.txt"  2>&1
  timeout 60 $AB snapshot -i -c                            --max-output 100000000 > "$OUT/${slug}__snap_ic.txt" 2>&1
done

$AB close >/dev/null 2>&1
echo "done" >&2
