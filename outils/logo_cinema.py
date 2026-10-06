#!/usr/bin/env python3
"""
Logo uniforme des cinémas du réseau (règle validée par Adrien le 06/10/2026) :
  ligne 1 = nom du cinéma, Advent Pro Light (300), blanc ;
  ligne 2 = ville en minuscules avec capitale initiale, Advent Pro Bold (700), couleur du cinéma,
            alignée à droite sur le nom ; pas de mot « cinéma » dans le logo.
Proportions reprises du logo du Commynes (référence) : « Le Commynes » / « Argentonnay ».

  python3 outils/logo_cinema.py "Le 7e Art" "Cerizay" "#D41818" SORTIE_SANS_EXT [--blanc COULEUR_NOM]
→ SORTIE.svg + SORTIE.pdf (vectoriels, textes vectorisés) + SORTIE.png (3576 px de large, fond transparent).
Police : assets/polices-logo/advent-pro-latin-*-normal.woff (Google Fonts, licence OFL).
"""
import argparse, os
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
import cairosvg

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, '..', 'assets', 'polices-logo')
# référence Commynes (PNG 3576 px) : hauteur d'encre du nom 613 px, de la ville 435 px, ville commence à y=687
REF = {'name': ('Le Commynes', 300, 613.0), 'city': ('Argentonnay', 700, 435.0), 'city_top': 687.0,
       'name_w': 3576.0, 'city_w': 2360.0}      # largeurs d'encre → interlettrage de la référence


_CACHE = {}


def font(w):
    if w not in _CACHE:
        import io
        tt = TTFont(os.path.join(FONTS, f'advent-pro-latin-{w}-normal.woff'))
        tt.flavor = None                      # WOFF → TTF (harfbuzz ne lit pas le WOFF)
        bio = io.BytesIO(); tt.save(bio)
        _CACHE[w] = (TTFont(io.BytesIO(bio.getvalue())), bio.getvalue())
    return _CACHE[w]


def shape(text, w, track=0.0):
    tt, data = font(w)
    face = hb.Face(data); f = hb.Font(face)
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
    hb.shape(f, buf, {'kern': True, 'liga': True})
    gs = tt.getGlyphSet(); order = tt.getGlyphOrder()
    out, x = [], 0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        out.append((order[info.codepoint], x + pos.x_offset, pos.y_offset))
        x += pos.x_advance + track
    return tt, gs, out


def ink(text, w, track=0.0):
    tt, gs, gl = shape(text, w, track)
    bp = BoundsPen(gs)
    for g, x, y in gl:
        gs[g].draw(TransformPen(bp, (1, 0, 0, 1, x, y)))
    return bp.bounds        # xmin, ymin, xmax, ymax en unités police


def path(text, w, s, ox, base, track=0.0):
    """chemin SVG du texte : échelle s, encre gauche en ox, ligne de base en base (y vers le bas)"""
    tt, gs, gl = shape(text, w, track)
    x0 = ink(text, w, track)[0]
    sp = SVGPathPen(gs)
    for g, x, y in gl:
        gs[g].draw(TransformPen(sp, (s, 0, 0, -s, ox + (x - x0) * s, base - y * s)))
    return sp.getCommands()


# échelles et lignes de base calées sur la référence
_n = ink(*REF['name'][:2]); S1 = REF['name'][2] / (_n[3] - _n[1]); B1 = _n[3] * S1
_c = ink(*REF['city'][:2]); S2 = REF['city'][2] / (_c[3] - _c[1]); B2 = REF['city_top'] + _c[3] * S2
CAP = _c[3]          # haut de la capitale de la ville (A), pour caler toute ville au même niveau
T1 = (REF['name_w'] / S1 - (_n[2] - _n[0])) / (len(REF['name'][0]) - 1)   # interlettrage (unités police)
T2 = (REF['city_w'] / S2 - (_c[2] - _c[0])) / (len(REF['city'][0]) - 1)


def build(nom, ville, couleur, out, couleur_nom='#FFFFFF'):
    bn, bc = ink(nom, 300, T1), ink(ville, 700, T2)
    wn, wc = (bn[2] - bn[0]) * S1, (bc[2] - bc[0]) * S2
    W = max(wn, wc)
    pn = path(nom, 300, S1, W - wn, B1, T1)
    pc = path(ville, 700, S2, W - wc, REF['city_top'] + CAP * S2, T2)
    top = min(B1 - bn[3] * S1, 0)
    H = max(REF['city_top'] + CAP * S2 - bc[1] * S2, B1 - bn[1] * S1)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 {top:.1f} {W:.1f} {H - top:.1f}" '
           f'width="{W / 30:.1f}mm" height="{(H - top) / 30:.1f}mm">'
           f'<path fill="{couleur_nom}" d="{pn}"/><path fill="{couleur}" d="{pc}"/></svg>')
    open(out + '.svg', 'w').write(svg)
    cairosvg.svg2pdf(bytestring=svg.encode(), write_to=out + '.pdf')
    cairosvg.svg2png(bytestring=svg.encode(), write_to=out + '.png', output_width=3576)
    print(out, f'{W:.0f}×{H - top:.0f}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('nom'); ap.add_argument('ville'); ap.add_argument('couleur'); ap.add_argument('sortie')
    ap.add_argument('--couleur-nom', default='#FFFFFF')
    a = ap.parse_args()
    build(a.nom, a.ville, a.couleur, a.sortie, a.couleur_nom)
