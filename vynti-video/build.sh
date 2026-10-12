#!/usr/bin/env bash
# Reconstruit la vidéo complète : assets -> images (Chromium, flou de mouvement) -> bande-son -> mp4.
#
#   ./build.sh                 1080p60 (VYNTI-motion-design.mp4 + miniature)
#   SCALE=2 ./build.sh         rendu 4K (3840 × 2160) pour YouTube
#   EXPORTS=1 ./build.sh       ajoute les exports du script : H.264 18 Mbit/s en deux passes
#                              (site et réseaux) et maître ProRes 422 HQ + PCM 24 bits
set -euo pipefail
cd "$(dirname "$0")"

FPS="${FPS:-60}" WORKERS="${WORKERS:-3}" SCALE="${SCALE:-1}" MB="${MB:-6}"

python3 prepare.py
node render.mjs --video --fps "$FPS" --workers "$WORKERS" --scale "$SCALE" --mb "$MB"
python3 audio.py

# version légère pour le dépôt et le partage (qualité constante, son AAC 320 kbit/s)
ffmpeg -y -loglevel error -i out/video-noaudio.mp4 -i out/audio.wav -map 0:v -map 1:a \
  -c:v libx264 -preset slow -crf 18 -profile:v high -pix_fmt yuv420p -movflags +faststart \
  -c:a aac -b:a 320k -ar 48000 -shortest VYNTI-motion-design.mp4
# miniature : le plan de signature (les 2,6 dernières secondes)
ffmpeg -y -loglevel error -ss 59.0 -i VYNTI-motion-design.mp4 -frames:v 1 VYNTI-miniature.png

if [[ "${EXPORTS:-0}" == "1" ]]; then
  mkdir -p exports
  # site et réseaux : H.264 1080p60, 18 Mbit/s en deux passes, AAC 320 kbit/s
  ffmpeg -y -loglevel error -i out/video-noaudio.mp4 -c:v libx264 -preset slow -b:v 18M -pass 1 -passlogfile out/x264 -an -f mp4 /dev/null
  ffmpeg -y -loglevel error -i out/video-noaudio.mp4 -i out/audio.wav -map 0:v -map 1:a -c:v libx264 -preset slow -b:v 18M -pass 2 -passlogfile out/x264 \
    -pix_fmt yuv420p -movflags +faststart -c:a aac -b:a 320k -ar 48000 -shortest exports/VYNTI-web-18M.mp4
  # maître : ProRes 422 HQ, son PCM 48 kHz 24 bits
  ffmpeg -y -loglevel error -i out/video-noaudio.mp4 -i out/audio.wav -map 0:v -map 1:a -c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le \
    -c:a pcm_s24le -ar 48000 -shortest exports/VYNTI-master-prores.mov
fi
echo "OK -> VYNTI-motion-design.mp4"
