"""Moyenne des sous-images du flou de mouvement.

Lit sur l'entrée standard une suite d'images de sortie, chacune sous la forme
  [n : uint32] puis n fois [taille : uint32][JPEG ou PNG]
et écrit sur la sortie standard les images RVB 24 bits brutes (une par groupe),
moyenne des n sous-images (n = 1 : image telle quelle).
"""
import io
import struct
import sys

import numpy as np
from PIL import Image


def read_exact(f, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = f.read(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return bytes(buf)


def main():
    src, out = sys.stdin.buffer, sys.stdout.buffer
    acc = None
    while True:
        head = read_exact(src, 4)
        if head is None:
            break
        (n,) = struct.unpack("<I", head)
        for i in range(n):
            (size,) = struct.unpack("<I", read_exact(src, 4))
            img = np.asarray(Image.open(io.BytesIO(read_exact(src, size))).convert("RGB"))
            if n == 1:
                out.write(img.tobytes())
                break
            if i == 0:
                acc = img.astype(np.uint16)
            else:
                np.add(acc, img, out=acc, casting="unsafe")
        if n > 1:
            acc += n // 2                      # arrondi
            out.write((acc // n).astype(np.uint8).tobytes())
    out.flush()


if __name__ == "__main__":
    main()
