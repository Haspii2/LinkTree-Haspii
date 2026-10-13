#!/usr/bin/env bash
# Encode les images rendues (render_all.py) en MP4 4K 60 i/s, H.264 High 4:2:0, qualité quasi sans perte.
# usage : ./encode.sh <dossier_images> <sortie.mp4>
set -euo pipefail
IN="${1:?dossier d'images}"; OUT="${2:?fichier mp4}"
ffmpeg -y -framerate 60 -i "$IN/f%04d.png" \
  -vf "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p" \
  -c:v libx264 -preset slow -crf 10 -profile:v high -level:v 5.2 \
  -x264-params "aq-mode=3:aq-strength=0.8:deblock=-1,-1" \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -movflags +faststart -an "$OUT"
