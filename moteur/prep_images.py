#!/usr/bin/env python3
"""
Préparation des images d'un mois.

  bandeau  : recadre une photo au format d'un bandeau événement (89,7 mm de large)
             et assombrit les zones de texte (gauche) et de date (droite).
             python3 prep_images.py bandeau SOURCE SORTIE --haut-mm 35 [--x 0.55 --y 0.4 --zoom 1.0 --sombre 0.3]
               --x/--y  : point de l'image à placer au centre de la zone claire (0..1)
               --zoom   : >1 pour resserrer le cadrage
  normalise: convertit une affiche/photo (webp, png...) en JPEG RVB 72 ppi (1 px = 1 pt dans l'IDML)
             python3 prep_images.py normalise SOURCE SORTIE
"""
import sys, argparse
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument('mode', choices=['bandeau', 'normalise'])
ap.add_argument('src'); ap.add_argument('dst')
ap.add_argument('--haut-mm', type=float, default=35.0)
ap.add_argument('--larg-mm', type=float, default=89.7)
ap.add_argument('--x', type=float, default=0.55)
ap.add_argument('--y', type=float, default=0.45)
ap.add_argument('--zoom', type=float, default=1.0)
ap.add_argument('--sombre', type=float, default=0.3)
ap.add_argument('--clair-de', type=float, default=0.36, help='début de la zone claire (0..1 de la largeur)')
ap.add_argument('--clair-a', type=float, default=0.76, help='fin de la zone claire')
a = ap.parse_args()

im = Image.open(a.src).convert('RGB')
if a.mode == 'normalise':
    im.save(a.dst, quality=93, dpi=(72, 72))
    print(a.dst, im.size)
    sys.exit()

R = a.larg_mm / a.haut_mm
W, H = im.size
w = min(W, H * R) / a.zoom
h = w / R
# la zone claire est centrée à 56 % de la largeur du bandeau
cx = a.x * W; cy = a.y * H
x0 = min(max(0, cx - ((a.clair_de + a.clair_a) / 2) * w), W - w)
y0 = min(max(0, cy - 0.5 * h), H - h)
im = im.crop((int(x0), int(y0), int(x0 + w), int(y0 + h)))
OUTW = 2400
im = im.resize((OUTW, int(OUTW / R)), Image.LANCZOS)
arr = np.asarray(im).astype(float)
x = np.linspace(0, 1, arr.shape[1])
up = np.clip((x - a.clair_de) / 0.16, 0, 1)
down = np.clip((a.clair_a - x) / 0.12, 0, 1)
mult = a.sombre + (1 - a.sombre) * np.minimum(up, down)
arr = arr * mult[None, :, None]
Image.fromarray(arr.clip(0, 255).astype('uint8')).save(a.dst, quality=92, dpi=(72, 72))
print(a.dst, f'source {W}x{H} -> recadrage {int(w)}x{int(h)} px ({int(w / a.larg_mm * 25.4)} ppi réels)')
