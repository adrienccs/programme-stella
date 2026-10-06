#!/usr/bin/env python3
"""
Bloc « Ciné-Kids » de l'affiche A3 (proposition V2 validée par Adrien le 06/10/2026) :
fond blanc, rangée de crayons de couleur vectoriels qui pendent du haut, « CINÉ-KIDS » en lettres
multicolores qui sautillent (Fredoka Bold), dates en rouge cinéma + infos goûter, photo d'un film
jeunesse à droite fondue dans le blanc, cadre rouge.

  python3 outils/bloc_cinekids.py --photo PHOTO.jpg --dates "du 17 oct. au 2 nov." \
     --ligne1 "Goûter offert par Super U" --ligne2 "aux séances soulignées · 4,50 €" \
     --sortie "mois/…/images/7EA bloc cine kids.png" [--cadrage-y 0.48] [--couleur "#D41818"]
→ PNG 273 × 36 mm à 400 ppp (+ .svg et .pdf pour retouche). À déclarer dans mois.json :
  "visuel_affiche": "7EA bloc cine kids.png" sur l'événement vedette.
Polices : assets/polices-logo (Fredoka, Advent Pro — licence OFL).
"""
import argparse, base64, io, os, random
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from PIL import Image
import cairosvg

HERE = os.path.dirname(os.path.abspath(__file__))
PF = os.path.join(HERE, '..', 'assets', 'polices-logo')
FRED7, FRED5 = os.path.join(PF, 'fredoka-latin-700-normal.woff'), os.path.join(PF, 'fredoka-latin-500-normal.woff')
ADV7 = os.path.join(PF, 'advent-pro-latin-700-normal.woff')
COLS = ['#F6B800', '#E8432E', '#F28C28', '#E2457A', '#8E44AD', '#2F7FD0', '#2BB0C9', '#3BAA5A', '#8BC34A', '#5D4037']
_F = {}


def font(p):
    if p not in _F:
        _F[p] = TTFont(p)
    return _F[p]


def text_path(txt, fp, size, x, y, track=0.0):
    tt = font(fp); gs = tt.getGlyphSet(); cmap = tt.getBestCmap(); s = size / tt['head'].unitsPerEm
    sp = SVGPathPen(gs); cx = x
    for c in txt:
        g = cmap[ord(c)]
        gs[g].draw(TransformPen(sp, (s, 0, 0, -s, cx, y)))
        cx += tt['hmtx'][g][0] * s + track
    return sp.getCommands()


def letters(txt, size, x, y, bounce=10, rot=6, track=12, seed=3):
    rnd = random.Random(seed)
    tt = font(FRED7); gs = tt.getGlyphSet(); cmap = tt.getBestCmap(); s = size / tt['head'].unitsPerEm
    out, cx, k = [], x, 0
    for c in txt:
        g = cmap[ord(c)]; adv = tt['hmtx'][g][0] * s
        sp = SVGPathPen(gs); gs[g].draw(TransformPen(sp, (s, 0, 0, -s, 0, 0)))
        dy = (bounce if k % 2 else -bounce * 0.6) + rnd.uniform(-5, 5)
        out.append(f'<path fill="{COLS[k % len(COLS)]}" transform="translate({cx:.1f},{y + dy:.1f}) '
                   f'rotate({rnd.uniform(-rot, rot):.1f} {adv / 2:.1f} {-size * 0.35:.1f})" d="{sp.getCommands()}"/>')
        cx += adv + track; k += 1
    return ''.join(out)


def pencil(x, top, length, w, col):
    cone = w * 1.15; bb = top + length - cone; tip = cone * 0.38
    return (f'<rect x="{x:.1f}" y="{top:.1f}" width="{w:.1f}" height="{bb - top:.1f}" fill="{col}"/>'
            f'<rect x="{x + w * .62:.1f}" y="{top:.1f}" width="{w * .38:.1f}" height="{bb - top:.1f}" fill="#000" opacity=".18"/>'
            f'<rect x="{x + w * .12:.1f}" y="{top:.1f}" width="{w * .12:.1f}" height="{bb - top:.1f}" fill="#fff" opacity=".22"/>'
            f'<path fill="#F3D3A2" d="M{x:.1f},{bb:.1f} L{x + w * .25:.1f},{bb + 5:.1f} L{x + w * .5:.1f},{bb:.1f} L{x + w * .75:.1f},{bb + 5:.1f} '
            f'L{x + w:.1f},{bb:.1f} L{x + w * .5:.1f},{bb + cone:.1f} Z"/>'
            f'<path fill="#000" opacity=".12" d="M{x + w * .5:.1f},{bb:.1f} L{x + w:.1f},{bb:.1f} L{x + w * .5:.1f},{bb + cone:.1f} Z"/>'
            f'<path fill="{col}" d="M{x + w * .5 - w * .19:.1f},{bb + cone - tip:.1f} L{x + w * .5 + w * .19:.1f},{bb + cone - tip:.1f} '
            f'L{x + w * .5:.1f},{bb + cone:.1f} Z"/>')


def build_portrait(a, W, H):
    """format vertical (colonne gauche de l'affiche) : crayons en haut, titre, infos, photo en bas fondue vers le haut"""
    # 1. textes d'abord : la photo prend la place restante sous les textes (jamais de chevauchement)
    tt = font(FRED7); cmap = tt.getBestCmap(); upm = tt['head'].unitsPerEm
    t = a.titre.upper(); adv = sum(tt['hmtx'][cmap[ord(ch)]][0] for ch in t) / upm
    size = (W * 0.88 - 10 * (len(t) - 1)) / adv           # titre : ~88 % de la largeur
    x0 = (W - (adv * size + 10 * (len(t) - 1))) / 2
    tb = f'<path fill="#555" d="{text_path(a.surtitre.upper(), ADV7, 40, x0 + 4, 250, 7)}"/>'
    tb += letters(t, size, x0, 250 + size * 0.95, bounce=12, rot=6, track=10)
    def fit(txt, fp, want):                       # taille ≤ want qui tient dans 88 % de la largeur
        f_ = font(fp); cm = f_.getBestCmap()
        w1 = sum(f_['hmtx'][cm[ord(ch)]][0] for ch in txt) / f_['head'].unitsPerEm
        return min(want, W * 0.88 / w1)
    sd = fit(a.dates, FRED7, 90); sl = min(fit(a.ligne1, FRED5, 56), fit(a.ligne2, FRED5, 56))
    y = 250 + size * 0.95 + 40 + sd
    tb += f'<path fill="{a.couleur}" d="{text_path(a.dates, FRED7, sd, x0 + 4, y)}"/>'
    tb += f'<path fill="#333" d="{text_path(a.ligne1, FRED5, sl, x0 + 4, y + sl * 1.45)}"/>'
    tb += f'<path fill="#333" d="{text_path(a.ligne2, FRED5, sl, x0 + 4, y + sl * 2.7)}"/>'
    text_bot = y + sl * 2.7 + sl * 0.35
    # 2. photo en bas, fondue vers le haut
    sh = Image.open(a.photo).convert('RGB'); sw, shh = sh.size
    ph_h = int(min(H * 0.46, H - text_bot - 15)); r = W / ph_h
    if sw / shh > r:
        cw = int(shh * r); cx = int(sw * a.cadrage_x); x0c = min(max(0, cx - cw // 2), sw - cw); c = sh.crop((x0c, 0, x0c + cw, shh))
    else:
        ch = int(sw / r); cy = int(shh * a.cadrage_y); y0 = min(max(0, cy - ch // 2), shh - ch); c = sh.crop((0, y0, sw, y0 + ch))
    bio = io.BytesIO(); c.save(bio, 'JPEG', quality=92)
    href = 'data:image/jpeg;base64,' + base64.b64encode(bio.getvalue()).decode()
    b = ('<defs><linearGradient id="fadev" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="1"/>'
         '<stop offset="0.3" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>'
         f'<rect width="{W}" height="{H}" fill="#fff"/>'
         f'<image x="0" y="{H - ph_h}" width="{W}" height="{ph_h}" xlink:href="{href}" preserveAspectRatio="xMidYMid slice"/>'
         f'<rect x="0" y="{H - ph_h}" width="{W}" height="{ph_h}" fill="url(#fadev)"/>')
    rnd = random.Random(5); x = 12; k = 0
    while x + 40 <= W - 10:
        b += pencil(x, -30, rnd.uniform(70, 130), 40, COLS[k % len(COLS)]); x += 47; k += 1
    b += tb
    b += f'<rect x="4" y="4" width="{W - 8}" height="{H - 8}" fill="none" stroke="{a.couleur}" stroke-width="8"/>'
    return b


def build(a):
    W, H = int(a.largeur * 10), int(a.hauteur * 10)            # unités : 0,1 mm
    if W / H < 1.5:
        return finish(a, W, H, build_portrait(a, W, H))
    sh = Image.open(a.photo).convert('RGB'); sw, shh = sh.size
    ph_w = int(W * (0.40 if W / H < 4 else 0.385)); crop_h = int(sw * H / ph_w)
    r = ph_w / H                                   # ratio de la zone photo
    if sw / shh > r:                               # photo plus large : on rogne en largeur
        cw = int(shh * r); cx = int(sw * a.cadrage_x); x0 = min(max(0, cx - cw // 2), sw - cw)
        c = sh.crop((x0, 0, x0 + cw, shh))
    else:                                          # photo plus haute : on rogne en hauteur
        cy = int(shh * a.cadrage_y); y0 = min(max(0, cy - crop_h // 2), max(0, shh - crop_h))
        c = sh.crop((0, y0, sw, y0 + crop_h))
    bio = io.BytesIO(); c.save(bio, 'JPEG', quality=92)
    href = 'data:image/jpeg;base64,' + base64.b64encode(bio.getvalue()).decode()
    b = ('<defs><linearGradient id="fade" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="1"/>'
         '<stop offset="0.35" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>'
         f'<rect width="{W}" height="{H}" fill="#fff"/>'
         f'<image x="{W - ph_w}" y="0" width="{ph_w}" height="{H}" xlink:href="{href}" preserveAspectRatio="xMidYMid slice"/>'
         f'<rect x="{W - ph_w}" y="0" width="{ph_w}" height="{H}" fill="url(#fade)"/>')
    rnd = random.Random(5); x = 10; k = 0
    compact = W / H < 4                      # format programme (89,7 × 31,5 mm) : tout empilé à gauche
    pw, pg_, lmin, lmax = (28, 5, 45, 80) if compact else (46, 8, 80, 140)
    while x + pw <= W - ph_w + (90 if compact else 200):
        b += pencil(x, -25 if compact else -40, rnd.uniform(lmin, lmax), pw, COLS[k % len(COLS)]); x += pw + pg_; k += 1
    if compact:
        b += f'<path fill="#555" d="{text_path(a.surtitre.upper(), ADV7, 19, 30, 112, 3)}"/>'
        b += letters(a.titre.upper(), 78, 26, 190, bounce=6, rot=5, track=6)
        b += f'<path fill="{a.couleur}" d="{text_path(a.dates, FRED7, 34, 30, 238)}"/>'
        b += f'<path fill="#333" d="{text_path(a.ligne1, FRED5, 21, 30, 268)}"/>'
        b += f'<path fill="#333" d="{text_path(a.ligne2, FRED5, 21, 30, 294)}"/>'
        b += f'<rect x="2" y="2" width="{W - 4}" height="{H - 4}" fill="none" stroke="{a.couleur}" stroke-width="4"/>'
    else:
        b += f'<path fill="#555" d="{text_path(a.surtitre.upper(), ADV7, 30, 64, 172, 6)}"/>'
        b += letters(a.titre.upper(), 140, 60, 312)
        xt = int(W * 0.385)
        b += f'<path fill="{a.couleur}" d="{text_path(a.dates, FRED7, 64, xt, 245)}"/>'
        b += f'<path fill="#333" d="{text_path(a.ligne1, FRED5, 40, xt, 298)}"/>'
        b += f'<path fill="#333" d="{text_path(a.ligne2, FRED5, 40, xt, 344)}"/>'
        b += f'<rect x="3" y="3" width="{W - 6}" height="{H - 6}" fill="none" stroke="{a.couleur}" stroke-width="6"/>'
    return finish(a, W, H, b)


def finish(a, W, H, b):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" '
           f'width="{a.largeur}mm" height="{a.hauteur}mm">{b}</svg>')
    base = os.path.splitext(a.sortie)[0]
    open(base + '.svg', 'w').write(svg)
    cairosvg.svg2pdf(bytestring=svg.encode(), write_to=base + '.pdf')
    px = int(a.largeur / 25.4 * a.ppp)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=a.sortie, output_width=px)
    Image.open(a.sortie).convert('RGB').save(a.sortie, dpi=(72, 72))      # 1 px = 1 pt côté IDML, comme les autres liens
    print(a.sortie, px, 'px')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--photo', required=True); ap.add_argument('--dates', required=True)
    ap.add_argument('--ligne1', required=True); ap.add_argument('--ligne2', required=True)
    ap.add_argument('--sortie', required=True)
    ap.add_argument('--titre', default='CINÉ-KIDS'); ap.add_argument('--surtitre', default='Vacances de la Toussaint')
    ap.add_argument('--couleur', default='#D41818'); ap.add_argument('--cadrage-y', type=float, default=0.48)
    ap.add_argument('--cadrage-x', type=float, default=0.5)
    ap.add_argument('--largeur', type=float, default=273.0); ap.add_argument('--hauteur', type=float, default=36.0)
    ap.add_argument('--ppp', type=int, default=400)
    build(ap.parse_args())
