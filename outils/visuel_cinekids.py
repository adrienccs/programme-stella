#!/usr/bin/env python3
"""
Visuel « Ciné-Kids » de l'affiche A3 (proposition V2 validée par Adrien le 06/10/2026) :
crayons de couleur vectoriels qui pendent du haut, « CINÉ-KIDS » en lettres multicolores (Fredoka),
dates + infos goûter, photo d'un film jeunesse à droite fondue vers le blanc, cadre couleur du cinéma.
Format 273 × 36 mm (bandeau vedette de l'affiche).

  python3 outils/visuel_cinekids.py --photo PHOTO.jpg --dates "du 17 oct. au 2 nov." \
      --ligne1 "Goûter offert par Super U" --ligne2 "aux séances soulignées · 4,50 €" \
      --surtitre "VACANCES DE LA TOUSSAINT" --couleur "#D41818" --out "mois/…/images/7EA visuel cine kids"
→ .svg + .png 400 dpi (à placer dans l'affiche : clé « visuel_affiche » de l'événement vedette).
"""
import io, random, base64, os, argparse
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
import cairosvg
from PIL import Image

POL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'polices-logo')
AP = os.path.join(POL, 'advent-pro-latin-%d-normal.woff')
W, H = 2730, 360                     # 273 × 36 mm à 10 px/mm
COLS = ['#F6B800', '#E8432E', '#F28C28', '#E2457A', '#8E44AD', '#2F7FD0', '#2BB0C9', '#3BAA5A', '#8BC34A', '#5D4037']
_F = {}


def font(p):
    if p not in _F:
        _F[p] = TTFont(p)
    return _F[p]


def text_path(txt, fp, size, x, y_base, anchor='l', track=0.0):
    tt = font(fp); gs = tt.getGlyphSet(); cmap = tt.getBestCmap(); upm = tt['head'].unitsPerEm
    s = size / upm
    hm = tt['hmtx']
    adv = sum(hm[cmap[ord(c)]][0] for c in txt) * s + track * (len(txt) - 1)
    if anchor == 'm': x -= adv / 2
    if anchor == 'r': x -= adv
    sp = SVGPathPen(gs); cx = x
    for c in txt:
        g = cmap[ord(c)]
        gs[g].draw(TransformPen(sp, (s, 0, 0, -s, cx, y_base)))
        cx += hm[g][0] * s + track
    return sp.getCommands(), adv


def letters(txt, fp, size, x, y_base, cols, bounce=18, rot=6, track=10, seed=3):
    """lettres multicolores qui « sautillent » (comme l'ancien visuel)"""
    rnd = random.Random(seed)
    tt = font(fp); gs = tt.getGlyphSet(); cmap = tt.getBestCmap(); upm = tt['head'].unitsPerEm; s = size / upm
    out, cx, k = [], x, 0
    for c in txt:
        if c == ' ':
            cx += size * 0.35; continue
        g = cmap[ord(c)]; adv = tt['hmtx'][g][0] * s
        sp = SVGPathPen(gs)
        dy = (bounce if k % 2 else -bounce * 0.6) + rnd.uniform(-5, 5)
        gs[g].draw(TransformPen(sp, (s, 0, 0, -s, 0, 0)))
        r = rnd.uniform(-rot, rot)
        out.append(f'<path fill="{cols[k % len(cols)]}" transform="translate({cx:.1f},{y_base + dy:.1f}) '
                   f'rotate({r:.1f} {adv / 2:.1f} {-size * 0.35:.1f})" d="{sp.getCommands()}"/>')
        cx += adv + track; k += 1
    return ''.join(out), cx - x


def pencil(x, top, length, w, col, tip_down=True):
    """crayon de couleur vectoriel : corps hexagonal ombré, bois, mine"""
    cone = w * 1.15
    body_b = top + length - cone
    h = []
    h.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{w:.1f}" height="{body_b - top:.1f}" fill="{col}"/>')
    h.append(f'<rect x="{x + w * 0.62:.1f}" y="{top:.1f}" width="{w * 0.38:.1f}" height="{body_b - top:.1f}" fill="#000" opacity="0.18"/>')
    h.append(f'<rect x="{x + w * 0.12:.1f}" y="{top:.1f}" width="{w * 0.12:.1f}" height="{body_b - top:.1f}" fill="#fff" opacity="0.22"/>')
    # bois (festonné) + mine
    h.append(f'<path fill="#F3D3A2" d="M{x:.1f},{body_b:.1f} L{x + w * 0.25:.1f},{body_b + 5:.1f} L{x + w * 0.5:.1f},{body_b:.1f} '
             f'L{x + w * 0.75:.1f},{body_b + 5:.1f} L{x + w:.1f},{body_b:.1f} L{x + w * 0.5:.1f},{body_b + cone:.1f} Z"/>')
    h.append(f'<path fill="#000" opacity="0.12" d="M{x + w * 0.5:.1f},{body_b:.1f} L{x + w:.1f},{body_b:.1f} L{x + w * 0.5:.1f},{body_b + cone:.1f} Z"/>')
    tip = cone * 0.38
    h.append(f'<path fill="{col}" d="M{x + w * 0.5 - w * 0.5 * 0.38:.1f},{body_b + cone - tip:.1f} '
             f'L{x + w * 0.5 + w * 0.5 * 0.38:.1f},{body_b + cone - tip:.1f} L{x + w * 0.5:.1f},{body_b + cone:.1f} Z"/>')
    return ''.join(h)


def pencil_row(x0, x1, top, seed=7, w=46, gap=8, lmin=70, lmax=150, cols=COLS):
    rnd = random.Random(seed); out = []; x = x0; k = 0
    while x + w <= x1:
        out.append(pencil(x, top, rnd.uniform(lmin, lmax), w, cols[k % len(cols)])); x += w + gap; k += 1
    return ''.join(out)


def svg(body, bg='#FFFFFF'):
    return f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="{bg}"/>{body}</svg>'


def save(out, s, dpi=400):
    open(out + '.svg', 'w').write(s)
    cairosvg.svg2png(bytestring=s.encode(), write_to=out + '.png', output_width=int(273 / 25.4 * dpi))



FRED = os.path.join(POL, 'fredoka-latin-700-normal.woff')
FRED5 = os.path.join(POL, 'fredoka-latin-500-normal.woff')
ADV7 = AP % 700

ap = argparse.ArgumentParser()
ap.add_argument('--photo', required=True); ap.add_argument('--dates', required=True)
ap.add_argument('--ligne1', default='Goûter offert par Super U'); ap.add_argument('--ligne2', default='aux séances soulignées · 4,50 €')
ap.add_argument('--surtitre', default='VACANCES DE LA TOUSSAINT'); ap.add_argument('--couleur', default='#D41818')
ap.add_argument('--cadrage-y', type=float, default=0.48); ap.add_argument('--out', required=True)
a = ap.parse_args()
RED = a.couleur

ph = Image.open(a.photo).convert('RGB')
sw, sh = ph.size; ph_w = 1050; crop_h = int(sw * H / ph_w)
cy = int(sh * a.cadrage_y); y0 = min(max(0, cy - crop_h // 2), sh - crop_h)
c = ph.crop((0, y0, sw, y0 + crop_h)).resize((ph_w * 2, H * 2))
bio = io.BytesIO(); c.save(bio, 'JPEG', quality=92); href = 'data:image/jpeg;base64,' + base64.b64encode(bio.getvalue()).decode()
b = '<defs><linearGradient id="fade" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="1"/><stop offset="0.35" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>'
b += f'<image x="{W - ph_w}" y="0" width="{ph_w}" height="{H}" xlink:href="{href}" preserveAspectRatio="none"/>'
b += f'<rect x="{W - ph_w}" y="0" width="{ph_w}" height="{H}" fill="url(#fade)"/>'
b += pencil_row(10, W - ph_w + 200, -40, seed=5, lmin=80, lmax=140)
t, _ = letters('CINÉ-KIDS', FRED, 140, 60, 312, COLS, bounce=10, track=12); b += t
p, _ = text_path(a.dates, FRED, 64, 1050, 245); b += f'<path fill="{RED}" d="{p}"/>'
p, _ = text_path(a.ligne1, FRED5, 40, 1050, 298); b += f'<path fill="#333" d="{p}"/>'
p, _ = text_path(a.ligne2, FRED5, 40, 1050, 344); b += f'<path fill="#333" d="{p}"/>'
p, _ = text_path(a.surtitre, ADV7, 30, 64, 172, track=6); b += f'<path fill="#555" d="{p}"/>'
b += f'<rect x="3" y="3" width="{W - 6}" height="{H - 6}" fill="none" stroke="{RED}" stroke-width="6"/>'
save(a.out, svg(b))
print(a.out + '.png')
