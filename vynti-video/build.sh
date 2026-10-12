#!/usr/bin/env bash
# Reconstruit la vidéo complète : assets -> images (Chromium, flou de mouvement) -> bande-son -> mp4.
#
#   ./build.sh                 4K UHD 60 i/s : VYNTI-motion-design-4K.mp4, version 1080p
#                              VYNTI-motion-design.mp4 (réduite depuis la 4K) et miniature
#   SCALE=1 ./build.sh         rendu direct en 1080p (plus rapide, moins net)
#   EXPORTS=1 ./build.sh       ajoute les exports du script : H.264 1080p 18 Mbit/s en deux passes
#                              et maître ProRes 422 HQ + PCM 24 bits (à la définition du rendu)
set -euo pipefail
cd "$(dirname "$0")"

FPS="${FPS:-60}" WORKERS="${WORKERS:-3}" SCALE="${SCALE:-2}" MB="${MB:-12}"
TAGS=(-colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv)

python3 prepare.py
node render.mjs --video --fps "$FPS" --workers "$WORKERS" --scale "$SCALE" --mb "$MB"
python3 audio.py

if [[ "$SCALE" == "2" ]]; then
  # maître 4K (qualité constante, son AAC 320 kbit/s)
  ffmpeg -y -loglevel error -i out/video-noaudio.mp4 -i out/audio.wav -map 0:v -map 1:a \
    -c:v libx264 -preset slow -crf "${CRF4K:-20}" -profile:v high -level 5.2 -pix_fmt yuv420p "${TAGS[@]}" -movflags +faststart \
    -c:a aac -b:a 320k -ar 48000 -shortest VYNTI-motion-design-4K.mp4
fi
# version 1080p pour le partage (réduite depuis le rendu, filtre Lanczos)
ffmpeg -y -loglevel error -i out/video-noaudio.mp4 -i out/audio.wav -map 0:v -map 1:a \
  -vf "scale=1920:1080:flags=lanczos+accurate_rnd" -c:v libx264 -preset slow -crf 18 -profile:v high -pix_fmt yuv420p "${TAGS[@]}" -movflags +faststart \
  -c:a aac -b:a 320k -ar 48000 -shortest VYNTI-motion-design.mp4
# miniature : le plan de signature
ffmpeg -y -loglevel error -ss 59.0 -i VYNTI-motion-design.mp4 -frames:v 1 VYNTI-miniature.png

if [[ "${EXPORTS:-0}" == "1" ]]; then
  mkdir -p exports
  # site et réseaux : H.264 1080p60, 18 Mbit/s en deux passes, AAC 320 kbit/s
  ffmpeg -y -loglevel error -i out/video-noaudio.mp4 -vf "scale=1920:1080:flags=lanczos" -c:v libx264 -preset slow -b:v 18M -pass 1 -passlogfile out/x264 -an -f mp4 /dev/null
  ffmpeg -y -loglevel error -i out/video-noaudio.mp4 -i out/audio.wav -map 0:v -map 1:a -vf "scale=1920:1080:flags=lanczos" -c:v libx264 -preset slow -b:v 18M -pass 2 -passlogfile out/x264 \
    -pix_fmt yuv420p "${TAGS[@]}" -movflags +faststart -c:a aac -b:a 320k -ar 48000 -shortest exports/VYNTI-web-18M.mp4
  # maître : ProRes 422 HQ, son PCM 48 kHz 24 bits
  ffmpeg -y -loglevel error -i out/video-noaudio.mp4 -i out/audio.wav -map 0:v -map 1:a -c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le \
    -c:a pcm_s24le -ar 48000 -shortest exports/VYNTI-master-prores.mov
fi
echo "OK -> VYNTI-motion-design.mp4"
