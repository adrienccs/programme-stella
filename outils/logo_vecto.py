#!/usr/bin/env python3
"""Vectorise les mots du logo (masques 1200 dpi extraits du PDF de l'ancien programme) et compose
le logo du cinéma : SVG + PDF vectoriels, et PNG HD (utilisé par le moteur).
  python3 outils/logo_vecto.py MOT1.png MOT2.png SORTIE_SANS_EXT [#couleur_mot2]
MOT1 = nom (blanc, sur fond noir de couverture), MOT2 = ville (couleur du cinéma), aligné à droite."""
import sys
import numpy as np, potrace, cairosvg
from PIL import Image


def trace(png):
    im = Image.open(png).convert('L')
    a = np.array(im) > 127
    ys, xs = np.where(a)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    paths = potrace.Bitmap(~a).trace(turdsize=4, alphamax=1.0, opticurve=True, opttolerance=0.2)
    d = []
    for c in paths:
        s = c.start_point
        d.append(f'M{s.x:.2f},{s.y:.2f}')
        for seg in c.segments:
            if seg.is_corner:
                d.append(f'L{seg.c.x:.2f},{seg.c.y:.2f}L{seg.end_point.x:.2f},{seg.end_point.y:.2f}')
            else:
                d.append(f'C{seg.c1.x:.2f},{seg.c1.y:.2f} {seg.c2.x:.2f},{seg.c2.y:.2f} {seg.end_point.x:.2f},{seg.end_point.y:.2f}')
        d.append('Z')
    return ''.join(d), a.shape[1], a.shape[0]


m1, m2, out = sys.argv[1:4]
col = sys.argv[4] if len(sys.argv) > 4 else '#D41818'
d1, w1, h1 = trace(m1)
d2, w2, h2 = trace(m2)
gap = int(h1 * 0.28)
W = max(w1, w2); H = h1 + gap + h2
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W/1200*25.4:.2f}mm" height="{H/1200*25.4:.2f}mm">'
       f'<path fill="#FFFFFF" fill-rule="evenodd" transform="translate({W - w1},0)" d="{d1}"/>'
       f'<path fill="{col}" fill-rule="evenodd" transform="translate({W - w2},{h1 + gap})" d="{d2}"/></svg>')
open(out + '.svg', 'w').write(svg)
cairosvg.svg2pdf(bytestring=svg.encode(), write_to=out + '.pdf')
cairosvg.svg2png(bytestring=svg.encode(), write_to=out + '.png', output_width=3576)
print(out, W, H)
