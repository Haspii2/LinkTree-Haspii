#!/usr/bin/env bash
# Reconstruit la vidéo complète : assets -> images (Chromium) -> bande-son -> mp4 final
set -euo pipefail
cd "$(dirname "$0")"

python3 prepare.py
node render.mjs --video --fps "${FPS:-60}" --workers "${WORKERS:-3}"
python3 audio.py
ffmpeg -y -loglevel error -i out/video-noaudio.mp4 -i out/audio.wav \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart \
  VYNTI-motion-design.mp4
ffmpeg -y -loglevel error -ss 44.6 -i VYNTI-motion-design.mp4 -frames:v 1 VYNTI-miniature.png
echo "OK -> VYNTI-motion-design.mp4"
