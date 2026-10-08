#!/usr/bin/env python3
"""
Affiche A3 (portrait, fonds perdus 3 mm) du programme du mois — même charte que le programme 3 volets.

Construite à partir du MÊME gabarit et des MÊMES fiches JSON que programme.py :
  python3 moteur/affiche.py --kit . --cinema cinemas/commynes.json --mois mois/<id>-AAAA-MM/mois.json \
          --images mois/<id>-AAAA-MM/images --out SORTIE_AFFICHE

Contenu (repris de l'ancienne affiche Publisher, mis à la charte du nouveau programme) :
  - en-tête « projecteurs » : logo, slogan, fauteuil ; bande noire avec les 6 affiches de couverture ;
  - bandeau « PROGRAMME du … au … » ;
  - colonne gauche : événement spécial (soirée…) + « prochainement » (0 à 3 bandeaux) ;
  - colonne droite : une grille horaire par week-end (titre bleu + grille, bas arrondi) ;
  - tarifs / abonnements + bandeau « réservations » ; pied de page projecteurs avec l'adresse.

Réutilisable pour un autre cinéma du réseau construit sur le MÊME gabarit (maquette Fauteuil Rouge) :
copier moteur/affiche.py (+ render.py et assembler.py à jour) dans le dépôt de ce cinéma. Tout ce qui
change (couleur, logo, fauteuil, slogan, adresse, tarifs, abonnements, bandeau bas, titre « prochainement »)
vient de sa fiche cinemas/<id>.json ; option « photo_projecteurs » pour une autre photo d'en-tête/pied.
"""
import sys, os, json, shutil, copy, zipfile, urllib.parse, argparse, re, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from idmllib import *
import grid
import adapt
from PIL import Image

ap_ = argparse.ArgumentParser()
ap_.add_argument('--kit', required=True)
ap_.add_argument('--cinema', required=True)
ap_.add_argument('--mois', required=True)
ap_.add_argument('--images', required=True)
ap_.add_argument('--out', required=True)
A = ap_.parse_args()

CIN = json.load(open(A.cinema, encoding='utf-8'))
MOIS = json.load(open(A.mois, encoding='utf-8'))
IMG_DIRS = [A.images, os.path.join(A.kit, 'assets', 'cinemas', CIN['id']),
            os.path.join(A.kit, 'assets', 'communs-hd'), os.path.join(A.kit, 'assets', 'communs')]

ROOT = os.path.join(A.out, '_idml')
shutil.rmtree(ROOT, ignore_errors=True)
with zipfile.ZipFile(os.path.join(A.kit, 'assets', 'gabarit', 'GABARIT_3_VOLETS.idml')) as z:
    z.extractall(ROOT)
d = Doc(ROOT)
SP1, SP2 = 'Spreads/Spread_u2a1b.xml', 'Spreads/Spread_uc313.xml'
BLUE = 'Color/C=0 M=100 J=100 N=0'
LINKDIR = CIN.get('dossier_liens_mac') or 'file:/Volumes/Clients/Links/'
if not LINKDIR.endswith('/'):
    LINKDIR += '/'
USED, WARN, KEEP = set(), [], set()

PHOTO_PROJ = CIN.get('photo_projecteurs', 'beam-of-stage-lights-shining-in-hazy-night-2026-03-24-15-27-16-utc.JPG')
W_PAGE, H_PAGE = 297.0, 420.0          # A3 portrait
BL = 3.0                               # fonds perdus
X0, X1 = 9.8, 287.2                    # marges du contenu

d._image_template = copy.deepcopy(d.el('u8423').find('Image'))
grid.capture(d)
grid.ROUGE = 'Color/Grille rouge' if 'rouge' in CIN.get('couleurs_grille', {}) else None
grid.TITRE_UNE_LIGNE = bool(CIN.get('titres_grille_entiers'))   # Stella 08/10/2026 : titres jamais en « gros + petit »

# ---------------------------------------------------------------- page A3
pg = d.spreads[SP1].getroot().find('Spread/Page')
pg.set('GeometricBounds', f'0 0 {H_PAGE * PT} {W_PAGE * PT}')
pg.set('AppliedMaster', 'n')
mp = pg.find('MarginPreference')
if mp is not None:
    mp.set('ColumnsPositions', f'0 {W_PAGE * PT - 72}')


def find_img(name):
    for dd in IMG_DIRS:
        p = os.path.join(dd, name)
        if os.path.exists(p):
            return p
    raise SystemExit(f'IMAGE MANQUANTE : {name}')


def img(rect, fname, mode='fill', align=(0.5, 0.5), affiche=False):
    p = find_img(fname)
    if affiche:                          # affiche de film : adaptée au format du cadre, sans rien couper (méthode D)
        _r = E(rect) if isinstance(rect, str) else rect
        _x0, _y0, _x1, _y1 = d.inner_bounds(_r)
        fname = adapt.adapte(p, (_x1 - _x0) / (_y1 - _y0), WARN)
        p = find_img(fname)
    w, h = Image.open(p).size
    USED.add(p)
    ext = 'png' if fname.lower().endswith('.png') else 'jpg'
    rid = rect if isinstance(rect, str) else rect.get('Self')
    d.place_image(rid, LINKDIR + urllib.parse.quote(fname), w, h, mode, ext, align)
    return w, h


def E(i):
    return d.el(i) if isinstance(i, str) else i


def take(i, dup=False):
    """élément du gabarit (ou sa copie) ramené sur la page de l'affiche"""
    el = d.duplicate(i) if dup else E(i)
    if el.getparent().tag == 'Spread' and el.getparent().get('Self') != 'u2a1b':
        el.getparent().remove(el)
        d.spreads[SP1].getroot().find('Spread').append(el)
    KEEP.add(el.get('Self'))
    return el


def story_of(f):
    return E(f).get('ParentStory')


def text_size(sid, pt, lead=None, align=None):
    for c in d.story(sid).getroot().iter('CharacterStyleRange'):
        c.set('PointSize', str(pt))
        if lead:
            p = c.find('Properties')
            if p is not None and p.find('Leading') is not None:
                p.find('Leading').text = str(lead)
    if align:
        for p in d.story(sid).getroot().iter('ParagraphStyleRange'):
            p.set('LeftIndent', '0'); p.set('Justification', align)


def vcenter(el):
    tfp = E(el).find('TextFramePreference')
    if tfp is not None:
        tfp.set('VerticalJustification', 'CenterAlign')


def heading(x0, y0, x1, y1, txt, pt, fill=None):
    h = take('ud0e9', dup=True)
    d.set_bounds(h, x0, y0, x1, y1)
    if fill:
        h.set('FillColor', fill)
    text_size(story_of(h), pt, align='CenterAlign')
    vcenter(h)
    d.set_text(story_of(h), {0: txt.lower()})
    return h


def _premiere(item):
    best = (99, 99 * 60)
    for j, hs in item[1].items():
        for h in hs:
            h = h if isinstance(h, str) else h['h']
            m = re.match(r'(\d+)h(\d*)', h)
            t = int(m.group(1)) * 60 + int(m.group(2) or 0) if m else 0
            best = min(best, (int(j), t))
    return best


# =====================================================================
# 1. en-tête : projecteurs, logo, fauteuil, affiches, bandeau des dates
# =====================================================================
HEAD_B = 48.0          # bas de la photo projecteurs
POST_B = 100.0         # bas de la bande noire des affiches
DATE_B = 111.0         # bas du bandeau des dates

bg = take('uc86a')
d.set_bounds(bg, -BL, -BL, W_PAGE + BL, DATE_B - 1)
beam = take('uc914')
d.set_bounds(beam, -BL, -BL, W_PAGE + BL, HEAD_B)
img(beam, PHOTO_PROJ, 'fill', (0.5, 0.35))

logo = take('ud3fb')
d.set_bounds(logo, 14.0, 7.0, 125.0, 36.0)
img(logo, CIN['logo'], 'fit', (0.0, 0.5))
slog = take('ud404')
d.set_bounds(slog, 15.0, 37.5, 170.0, 42.5)
d.set_text('ud407', {0: CIN.get('slogan', 'Cinéma indépendant, coopératif et proche de vous')})
text_size('ud407', 11)
FAUTEUIL = CIN.get('fauteuil_affiche') or CIN.get('fauteuil')
if FAUTEUIL:
    fa = take('ud3f3')
    d.set_bounds(fa, W_PAGE + BL - 60.0, HEAD_B - 40.0, W_PAGE + BL, HEAD_B)
    img(fa, FAUTEUIL, 'fill', (0.6, 1.0))

# 6 affiches de couverture, légèrement inclinées comme sur le programme
COVER = ['uc37d', 'uc380', 'uc89e', 'uc8b5', 'uc8c1', 'uc8cd']
aff = MOIS['couverture']['affiches'][:6]
n_aff = len(aff)
POST_H = POST_B - HEAD_B - 8.0
slot_w = (X1 - X0) / max(1, n_aff)
for k, fname in enumerate(aff):
    r = take(COVER[k])
    _cad = next((tuple(f_['cadrage_affiche']) for f_ in MOIS['films'].values()
                 if f_.get('affiche') == fname and f_.get('cadrage_affiche')), (0.5, 0.0))
    img(r, fname, 'fill', _cad, affiche=True)
    x0, y0, x1, y1 = d.bbox(r)
    s = POST_H / (y1 - y0)
    r.set('ItemTransform', fmt(mul([s, 0, 0, s, 0, 0], M(r.get('ItemTransform')))))
    r.set('StrokeWeight', '1.2')
    nx0, ny0, nx1, ny1 = d.bbox(r)
    cx = X0 + slot_w * (k + 0.5)
    d.move(r, cx - (nx0 + nx1) / 2, (HEAD_B + 4.0 + (k % 2) * 1.2) - ny0)

db = take('ud3da')
d.set_bounds(db, -BL, POST_B, W_PAGE + BL, DATE_B)
vcenter(db)
per = MOIS['periode']
d.set_text('ud3dd', {0: 'PROGRAMME du ', 1: per['du'] + ' ', 2: 'au ', 3: per['au_num'], 4: per.get('au_exposant', ''),
                     5: ' ' + per['au_mois'], 6: ' ' + str(per['annee'])})
for cr in d.story('ud3dd').getroot().iter('CharacterStyleRange'):
    cr.set('PointSize', '21'); cr.set('Tracking', '0')
for pr in d.story('ud3dd').getroot().iter('ParagraphStyleRange'):
    pr.set('LeftIndent', '0'); pr.set('Justification', 'CenterAlign')

# =====================================================================
# 2. colonne droite : grilles des week-ends
# =====================================================================
BODY_T = DATE_B + 6.0
BODY_B = float(os.environ.get('AFF_BODY_B', CIN.get('affiche_bas_grilles', 325.0)))   # réglable par cinéma
RX0, RX1 = X1 - 155.0, X1                # grilles un peu moins larges (retour Adrien)
SEMAINE = bool(MOIS.get('semaines'))          # 7e Art : 1 grille par SEMAINE, 6 à 8 films chacune


def legende_mois():
    """légende de l'affiche : items de « legende_grille » utilisés dans AU MOINS une semaine du mois"""
    L = CIN.get('legende_grille')
    if not L or isinstance(L, str) or not isinstance(L[0][0], dict):
        return L
    u = set()
    for w in MOIS.get('semaines') or MOIS.get('weekends', []):
        for e in w['films']:
            k, se, o = (e['film'], e.get('seances', {}), e) if isinstance(e, dict) else (e[0], e[1], e[2] if len(e) > 2 else {})
            if MOIS['films'][k].get('court'):
                u.add('i')
            if o.get('coeur'):
                u.add('coeur')
            for lst in se.values():
                for t in lst:
                    if isinstance(t, dict):
                        u |= set(t.get('s', ''))
    out = []
    for ligne in L:
        its = [it for it in ligne if it.get('code') in u or it.get('toujours')]
        if its:
            runs = []
            for jj, it in enumerate(its):
                if jj:
                    runs.append(['   ·   ', ''])
                runs += [list(r) for r in it['runs']]
            out.append(runs)
    return out


LEG_LINES = len(legende_mois() or [])
WE = MOIS.get('semaines') or MOIS['weekends']
H_FILM_PT = float(CIN.get('h_ligne_grille', 22.0))


def _norm(e):                                  # [clé, séances, options] ou {"film", "seances", ...}
    if isinstance(e, dict):
        return [e['film'], e.get('seances', {}), {k: v for k, v in e.items() if k not in ('film', 'seances')}]
    return [e[0], e[1], e[2] if len(e) > 2 else {}]


for _w in WE:
    _w['films'] = [_norm(e) for e in _w['films']]


def hf(we):
    if CIN.get('affiche_h_ligne'):              # Stella : hauteur de ligne propre à l'affiche (identique pour toutes les semaines)
        return float(CIN['affiche_h_ligne'])
    return float(we.get('h_ligne', H_FILM_PT))


CORPS = CIN.get('affiche_corps_grille')        # Stella (retour 06/10/2026) : corps fixes du texte des grilles sur l'affiche


def corps_grille(sid):
    """Impose des corps absolus (pt, après mise à l'échelle) : titres, durée, horaires, jours, dates, cases fusionnées."""
    if not CORPS:
        return
    for cell in d.story(sid).getroot().iter('Cell'):
        col, row = (int(v) for v in cell.get('Name').split(':'))
        if row == 0:
            sizes = [CORPS['dates']] if col == 0 else [CORPS['jours']]
        elif col == 0:                            # titre (même taille sur ses 2 lignes) / durée en petit
            for c in cell.iter('CharacterStyleRange'):
                ps = CORPS['duree'] if 'light' in c.get('AppliedCharacterStyle', '') else CORPS['titre']
                c.set('PointSize', str(ps))
                pr = c.find('Properties')
                ld = pr.find('Leading') if pr is not None else None
                if ld is not None and ld.get('type') == 'unit':
                    ld.text = str(round(ps * 1.08, 2))
            continue
        elif cell.get('ColumnSpan') and int(cell.get('ColumnSpan')) > 1:
            sizes = [CORPS['fusion']]
        else:
            sizes = [CORPS['horaires']]
        for k, c in enumerate(cell.iter('CharacterStyleRange')):
            ps = sizes[min(k, len(sizes) - 1)]
            c.set('PointSize', str(ps))
            pr = c.find('Properties')
            ld = pr.find('Leading') if pr is not None else None
            if ld is not None and ld.get('type') == 'unit':
                ld.text = str(round(ps * 1.08, 2))


TITRES_SEMAINE = CIN.get('affiche_titres_semaine', not bool(MOIS.get('semaines')))   # retour client 06/10/2026
HEAD_H, HEAD_GAP, WE_GAP = (7.0, 1.0, 4.0) if TITRES_SEMAINE else (0.0, 0.0, 4.0)
COLONNES = SEMAINE and CIN.get('affiche_disposition') == 'colonnes'    # retour client 06/10/2026
if COLONNES:
    # comme Argentonnay : colonne gauche = événements (vedette en haut), colonne droite = toutes les grilles
    PRO = MOIS.get('prochainement', [])[:3]
    GW = float(CIN.get('affiche_largeur_grilles', 170.0))
    RX0, RX1 = X1 - GW, X1
    LEG_H = (1.2 + LEG_LINES * 11 * 25.4 / 72) if CIN.get('legende_grille') else 0.0
    GRID_B = BODY_B - LEG_H - 1.5
    COLS_G = [(RX0, RX1, WE)]
    _base = sum((grid.H_DAYS + len(w['films']) * hf(w)) * 25.4 / 72 for w in WE)
    _fix = len(WE) * (HEAD_H + HEAD_GAP) + (len(WE) - 1) * WE_GAP
    K = min(1.6, (GRID_B - BODY_T - _fix) / _base)
    n_rows = sum(len(w['films']) for w in WE)
elif SEMAINE:
    # bas du corps : rangée de 3 bandeaux « évènements » sur toute la largeur, puis tarifs
    PRO = MOIS.get('prochainement', [])[:3]
    EV_W, EV_H, EV_GAP = 89.7, 31.5, 4.0        # même format que les bandeaux du programme
    VED_H, EV_H2, VED_ZOOM = 36.0, 26.0, 1.7    # événement vedette (ex. Ciné-Kids) pleine largeur, autres dessous
    _ved = any(e.get('vedette_affiche') for e in PRO)
    PRO_T = (BODY_B - (9.6 + (VED_H + 3.0 + EV_H2 if _ved else EV_H) + 2.2)) if PRO else BODY_B
    LEG_H = (0.2 + LEG_LINES * 11 * 25.4 / 72) if CIN.get('legende_grille') else 0.0
    GRID_B = PRO_T - 4.0 - LEG_H
    MID = (X0 + X1) / 2
    COLS_G = [(X0, MID - 3.0, WE[:2]), (MID + 3.0, X1, WE[2:4])]
    _ks = []
    for _x0, _x1, _ws in COLS_G:
        if not _ws:
            continue
        _base = sum((grid.H_DAYS + len(w['films']) * hf(w)) * 25.4 / 72 for w in _ws)
        _fix = len(_ws) * (HEAD_H + HEAD_GAP) + (len(_ws) - 1) * WE_GAP
        _ks.append((GRID_B - BODY_T - _fix) / _base)
    K = min(1.6, min(_ks))
    n_rows = sum(len(w['films']) for w in WE)
else:
    RX0, RX1 = X1 - 155.0, X1                # grilles un peu moins larges (retour Adrien)
    n_rows = sum(len(w['films']) for w in WE)
    base_h = sum((grid.H_DAYS + len(w['films']) * hf(w)) * 25.4 / 72 for w in WE)
    fixed = len(WE) * (HEAD_H + HEAD_GAP) + (len(WE) - 1) * WE_GAP
    K = min(1.6, (BODY_B - BODY_T - fixed) / base_h)
print(f'Grilles : échelle {K:.2f} ({n_rows} lignes de films)')


def scale_story(sid, k, lead=None):
    st = d.story(sid).getroot()
    for e in st.iter():
        for a in ('PointSize', 'LeftIndent', 'SingleRowHeight', 'MinimumHeight', 'SingleColumnWidth',
                  'TextTopInset', 'TextBottomInset', 'TextLeftInset', 'TextRightInset',
                  'TopInset', 'BottomInset', 'LeftInset', 'RightInset'):
            v = e.get(a)
            if v is not None:
                try:
                    e.set(a, str(float(v) * k))
                except ValueError:
                    pass
        if e.tag == 'Leading' and e.text and e.text.replace('.', '', 1).isdigit():
            e.text = str(float(e.text) * k)
    if lead:                                   # interlignage explicite (celui du style ne suit pas l'échelle)
        for c in st.iter('CharacterStyleRange'):
            ps = c.get('PointSize')
            if ps is None:
                continue
            pr = c.find('Properties')
            if pr is None:
                pr = etree.Element('Properties'); c.insert(0, pr)
            ld = pr.find('Leading')
            if ld is None:
                ld = etree.SubElement(pr, 'Leading'); ld.set('type', 'unit')
            ld.text = str(round(float(ps) * lead, 2))


def round_bottom(x0, x1, ybot, k, h_row=None):
    h_row = h_row or H_FILM_PT
    g = take('ud2ed', dup=True)
    g.set('ItemTransform', fmt(mul([k, 0, 0, k, 0, 0], M(g.get('ItemTransform')))))
    u = [c for c in g if c.tag == 'Rectangle' and c.get('StrokeTint') == '70'][0]
    ux0, _, _, uy1 = d.bbox(u)
    d.move(g, x0 - ux0, ybot - uy1)
    dw = (x1 - x0) - 90.0 * k
    mid = x0 + 45.0 * k
    for c in g:
        if c.tag != 'Rectangle':
            continue
        cx0, cy0, cx1, cy1 = d.bbox(c)
        if (cx1 - cx0) > 20:
            m = d.chain(c); mi = inv(m)
            for node in c.find('Properties/PathGeometry/GeometryPathType/PathPointArray'):
                for kk in ('Anchor', 'LeftDirection', 'RightDirection'):
                    X, Y = ap(m, *M(node.get(kk)))
                    if (X + OX) / PT > mid:
                        X += dw * PT
                    nx, ny = ap(mi, X, Y)
                    node.set(kk, f'{nx} {ny}')
        elif (cx0 + cx1) / 2 > mid:
            d.move(c, dw, 0)
    u = [c for c in g if c.tag == 'Rectangle' and c.get('StrokeTint') == '70'][0]
    m = d.chain(u); mi = inv(m)
    pts = list(u.find('Properties/PathGeometry/GeometryPathType/PathPointArray'))
    for node in (pts[0], pts[-1]):
        for kk in ('Anchor', 'LeftDirection', 'RightDirection'):
            X, Y = ap(m, *M(node.get(kk)))
            nx, ny = ap(mi, X, (ybot - h_row * k * 25.4 / 72) * PT - OY)
            node.set(kk, f'{nx} {ny}')


def gw_of(we):
    films = list(we['films']) if CIN.get('ordre_grille') == 'saisie' else sorted(we['films'], key=_premiere)
    return {'titre': we['titre'], 'days': we['jours'], 'fermes': we.get('fermes', []),
            'films': [(MOIS['films'][k_].get('grille', MOIS['films'][k_]['titre']), MOIS['films'][k_]['duree'],
                       {int(i): v for i, v in seances.items()},
                       {**({'court': True} if MOIS['films'][k_].get('court') else {}), **o})
                      for k_, seances, o in films]}


def label_dates(we):                 # « semaine du 14 au 20 octobre » → « DU 14 AU 20 OCTOBRE »
    t = we.get('titre_volet', we['titre'])
    return re.sub(r'^(semaine|week-end)\s+', '', t, flags=re.I).upper()


def one_grid(we, gx0_, gx1_, y):
    gw = gw_of(we)
    if TITRES_SEMAINE:
        heading(gx0_, y, gx1_, y + HEAD_H, we['titre'], 13)
        y += HEAD_H + HEAD_GAP
    else:
        gw['label_horaires'] = label_dates(we)   # les dates remplacent « HORAIRES » dans la grille
    g = take('ucf09', dup=True)
    if CORPS:
        grid.TITRE_PT = CORPS['titre'] / K        # corps final du titre ramené aux unités avant mise à l'échelle
    h = grid.build_one(d, g.get('ParentStory'), gw, (gx1_ - gx0_) * PT / K, h_film=hf(we), split=MOIS['films'],
                        day_w=float(CIN.get('affiche_largeur_jour', 22.0)))   # cases horaires élargies (retour client 06/10)
    scale_story(g.get('ParentStory'), K, lead=1.08)
    corps_grille(g.get('ParentStory'))
    h *= K
    gx0, gy0, _, _ = d.bbox(g)
    d.set_bounds(g, gx0, gy0, gx0 + (gx1_ - gx0_) + 0.5, gy0 + h + 7)
    d.move(g, gx0_ - gx0, y - gy0)
    round_bottom(gx0_, gx1_, y + h, K, hf(we))
    # picto « malentendants » en bas à droite de la case titre (comme le programme)
    _dw = float(CIN.get('affiche_largeur_jour', 22.0))
    _tw = ((gx1_ - gx0_) * PT / K - 7 * _dw) * K / PT
    _films = list(we['films']) if CIN.get('ordre_grille') == 'saisie' else sorted(we['films'], key=_premiere)
    for _ri, _e in enumerate(_films):
        _o = _e[2] if isinstance(_e, (list, tuple)) and len(_e) > 2 else {}
        if _o.get('malentendants'):
            _ph = 3.0 * K * 1.4
            _yb = y + (grid.H_DAYS + (_ri + 1) * hf(we)) * K / PT - 0.8 * K
            _xr = gx0_ + _tw - 1.0 * K
            _r = take('ubdf0', dup=True)
            _p = _r.getparent(); _p.remove(_r); _p.append(_r)          # premier plan (au-dessus de la grille)
            d.set_bounds(_r, _xr - _ph, _yb - _ph, _xr, _yb)
            _r.set('FillColor', 'Swatch/None'); _r.set('StrokeWeight', '0')
            img(_r.get('Self'), CIN.get('picto_malentendants', '7EA picto malentendants.png'), 'fit')
    return y + h


if SEMAINE:
    _ends = []
    for _x0, _x1, _ws in COLS_G:
        y = BODY_T
        for we in _ws:
            y = one_grid(we, _x0, _x1, y) + WE_GAP
        _ends.append(y - WE_GAP)
    GRID_END = max(_ends)
else:
    y = BODY_T
    for we in WE:
        y = one_grid(we, RX0, RX1, y) + WE_GAP
    GRID_END = y - WE_GAP

LEGENDE = legende_mois()
if SEMAINE and LEGENDE:                          # légende unique sous les grilles, lignes centrées
    if isinstance(LEGENDE, str):
        LEGENDE = [[[LEGENDE, '']]]
    lg = take('ubedb', dup=True)
    lg.set('FillColor', 'Swatch/None')
    _lgx = (RX0, RX1) if COLONNES else (X0, X1)
    d.set_bounds(lg, _lgx[0], GRID_END + 1.5, _lgx[1], GRID_END + 1.5 + LEG_H)
    st = d.story(story_of(lg)).getroot()
    psr = st.find('Story/ParagraphStyleRange')
    for extra in st.find('Story').findall('ParagraphStyleRange')[1:]:
        extra.getparent().remove(extra)
    psr.set('Justification', 'CenterAlign'); psr.set('LeftIndent', '0')
    tpl = copy.deepcopy(psr.find('CharacterStyleRange'))
    for c_ in psr.findall('CharacterStyleRange'):
        psr.remove(c_)
    for x in list(tpl):
        if x.tag in ('Content', 'Br'):
            tpl.remove(x)
    tpl.set('PointSize', '9'); tpl.set('FillColor', 'Color/Black'); tpl.set('FontStyle', '67 Medium Condensed')
    tpl.set('HorizontalScale', '100'); tpl.set('Tracking', '0')
    pr = tpl.find('Properties')
    if pr is None:
        pr = etree.SubElement(tpl, 'Properties')
    af = pr.find('AppliedFont')
    if af is None:
        af = etree.SubElement(pr, 'AppliedFont'); af.set('type', 'string')
    af.text = 'Helvetica Neue (OTF)'
    ld = pr.find('Leading')
    if ld is None:
        ld = etree.SubElement(pr, 'Leading'); ld.set('type', 'unit')
    ld.text = '11'
    for li, ligne in enumerate(LEGENDE):
        for si, (txt, sty) in enumerate(ligne):
            c_ = copy.deepcopy(tpl)
            if 'r' in sty: c_.set('FillColor', grid.ROUGE or BLUE)
            if 'v' in sty: c_.set('FillColor', 'Color/Grille violet')
            if 'b' in sty: c_.set('FillColor', 'Color/Grille bleu')
            if 's' in sty: c_.set('Underline', 'true'); c_.set('UnderlineOffset', '1.6'); c_.set('UnderlineWeight', '0.7')
            if 'i' in sty: c_.set('Skew', '12')
            if sty: c_.set('FontStyle', '77 Bold Condensed')
            if 'z' in sty:                       # ♥ coup de cœur (Zapf Dingbats)
                grid.set_font(c_, 'Zapf Dingbats', 'Regular')
            last = si == len(ligne) - 1
            etree.SubElement(c_, 'Content').text = txt + ('\u2028' if last and li < len(LEGENDE) - 1 else '')
            psr.append(c_)
    tfp = lg.find('TextFramePreference')
    if tfp is not None:
        tfp.set('VerticalJustification', 'TopAlign')

# =====================================================================
# 3. colonne gauche : événement spécial + prochainement
# =====================================================================
SLOTS = [('uc035', 'ud126', 'ud145', 'ud1a6', 'uc139', (0, 2, 5, 9)),
         ('uc043', 'ud157', 'ud170', 'ud1a7', 'ud1ab', (0, 2, 6, 10)),
         ('uc054', 'ud1cc', 'ud200', 'ud1e5', 'ud1e9', (0, 2, 5, 9))]
LX0 = X0 + 2.2
LX1 = (RX0 - 4.0) if not SEMAINE else X1 - 2.2


def grow_date(grp, dst, top, h, zoom=1.35, w=31.0):
    g = E(grp)
    tf = [c for c in g if c.tag == 'TextFrame'][0]
    for ln in [c for c in g if c.tag == 'Polygon']:
        g.remove(ln)
    x0, y0, x1, y1 = d.bbox(tf)
    d.set_bounds(tf, x1 - w, top + 1.0, x1, top + h - 1.0)
    vcenter(tf)
    for c in d.story(dst).getroot().iter('CharacterStyleRange'):
        ps = float(c.get('PointSize', '12'))
        c.set('PointSize', str(round(ps * zoom, 1)))
        p = c.find('Properties')
        if p is not None and p.find('Leading') is not None:
            p.find('Leading').text = str(round(float(p.find('Leading').text) * zoom * 0.96, 1))


def place_slot(slot, x0, top, h, ev, x1=None, zoom=1.0):
    im_, tf, ln, grp, dst, idx = slot
    for i in (im_, tf, ln, grp):
        take(i)
    if zoom > 1 and ev.get('visuel_affiche'):       # bloc vedette déjà composé (ex. outils/bloc_cinekids.py)
        d.set_bounds(E(im_), x0, top, x1, top + h)
        E(im_).set('FillColor', 'Swatch/None'); E(im_).set('StrokeWeight', '0')
        img(im_, ev['visuel_affiche'], 'fill', (0.5, 0.5))
        for i in (tf, ln, grp):
            d.delete(i)
        return
    ix0, iy0, ix1, iy1 = d.bbox(E(im_))
    w = (x1 - x0) if x1 else ix1 - ix0
    dx = x0 - ix0
    dy = top - iy0 + (h - (iy1 - iy0)) / 2
    for i in (tf, ln):
        d.move(E(i), dx, dy)
    d.move(E(grp), dx + (w - (ix1 - ix0)), dy)
    d.set_bounds(E(im_), x0, top, x0 + w, top + h)
    E(im_).set('FillColor', 'Swatch/None')
    img(im_, ev.get('image_affiche_vedette' if zoom > 1 else 'image_affiche') or ev['image'], 'fill', tuple(ev.get('cadrage', (0.5, 0.5))))
    d.set_text(story_of(tf), {0: ev['surtitre'], 2: ev['titre'], 4: ev['ligne'], 6: ev['ligne_grasse']})
    dt = ev['date']
    m = {idx[0]: dt['jour'] + ' ', idx[1]: dt['num'], idx[2]: dt['mois'], idx[3]: dt['heure']}
    if dst == 'ud1ab':
        m[3] = dt.get('exposant', '')
    d.set_text(dst, m)
    if zoom > 1:                                  # bandeau vedette : texte agrandi, filet supprimé
        tailles = {ev['surtitre']: (13, 'Color/Paper'), ev['titre']: (26, BLUE), ev['ligne']: (12.5, 'Color/Paper'),
                   ev['ligne_grasse']: (12.5, 'Color/Paper')}
        for c_ in d.story(story_of(tf)).getroot().iter('CharacterStyleRange'):
            txt_ = ''.join(x.text or '' for x in c_.iter('Content'))
            for k_, (pt_, col_) in tailles.items():
                if txt_ and txt_.strip() == k_.strip():
                    c_.set('PointSize', str(pt_))
                    if k_ == ev['titre']:
                        c_.set('FillColor', col_)
                    pr_ = c_.find('Properties')
                    if pr_ is None:
                        pr_ = etree.SubElement(c_, 'Properties')
                    ld_ = pr_.find('Leading')
                    if ld_ is None:
                        ld_ = etree.SubElement(pr_, 'Leading'); ld_.set('type', 'unit')
                    ld_.text = str(round(pt_ * 1.18, 1))
        d.set_bounds(E(tf), x0 + 6.0, top + 2.0, x0 + (x1 - x0) * 0.6, top + h - 2.0)
        vcenter(tf)
        E(ln).getparent().remove(E(ln))
        grow_date(grp, dst, top, h, zoom=1.35 * 1.25, w=60.0)
    else:
        grow_date(grp, dst, top, h, zoom=min(1.35, 1.35 * h / 31.5))   # bandeau plus bas → date réduite d'autant


SPE = MOIS.get('evenement_special')
PRO = MOIS.get('prochainement', [])[:3]
if COLONNES:
    SPE = None
    LX0c, LX1c = X0, RX0 - 4.0
    VED = [e for e in PRO if e.get('vedette_affiche')][:1]
    AUT = [e for e in PRO if e not in VED]
    ew_ = LX1c - LX0c - 4.4
    eh_ = round(ew_ / 2.85, 1)                    # même proportion que les bandeaux du programme
    box_h = (9.6 + len(AUT) * eh_ + (len(AUT) - 1) * 2.0 + 2.2) if AUT else 0
    box_t = BODY_B - box_h
    if AUT:
        box = take('ud24f')
        pp, pts = d.anchors(box)
        mi = inv(d.chain(box))
        corners = [(LX0c, BODY_B), (LX0c, box_t), (LX1c, box_t), (LX1c, BODY_B), (LX0c, BODY_B)]
        for node, (x, yy) in zip(pp, corners):
            nx, ny = ap(mi, x * PT - OX, yy * PT - OY)
            for kk in ('Anchor', 'LeftDirection', 'RightDirection'):
                node.set(kk, f'{nx} {ny}')
        hd = take('ud109')
        d.set_bounds(hd, LX0c, box_t + 1.4, LX1c - 6.0, box_t + 8.4)
        d.set_text('ud10c', {0: CIN.get('titre_prochainement', 'prochainement').lower()})
    si_ = 0
    if VED:
        vh_ = (box_t - 4.0 if AUT else BODY_B) - BODY_T
        print(f'Bloc vedette (colonne gauche) : {LX1c - LX0c:.1f} × {vh_:.1f} mm '
              f'→ outils/bloc_cinekids.py --largeur {LX1c - LX0c:.1f} --hauteur {vh_:.1f}')
        vis_ = VED[0].get('visuel_affiche_colonne')
        if vis_:
            r_ = take(SLOTS[si_][0]); si_ += 1
            d.set_bounds(r_, LX0c, BODY_T, LX1c, BODY_T + vh_)
            r_.set('FillColor', 'Swatch/None'); r_.set('StrokeWeight', '0')
            img(r_, vis_, 'fill', (0.5, 0.5))
        else:
            WARN.append('Vedette sans « visuel_affiche_colonne » : bandeau standard utilisé')
            place_slot(SLOTS[si_], LX0c, BODY_T, vh_, dict(VED[0], image_affiche=VED[0]['image']), LX1c); si_ += 1
    for k_, ev in enumerate(AUT):
        ev2 = dict(ev, image_affiche=ev['image'])          # bandeaux du programme (même proportion)
        place_slot(SLOTS[si_], LX0c + 2.2, box_t + 9.6 + k_ * (eh_ + 2.0), eh_, ev2, LX0c + 2.2 + ew_); si_ += 1
    PRO = []
    GRID_END = BODY_B
elif SEMAINE:
    SPE = None
    if PRO:
        box = take('ud24f')
        pp, pts = d.anchors(box)
        mi = inv(d.chain(box))
        corners = [(X0, BODY_B), (X0, PRO_T), (X1, PRO_T), (X1, BODY_B), (X0, BODY_B)]
        for node, (x, yy) in zip(pp, corners):
            nx, ny = ap(mi, x * PT - OX, yy * PT - OY)
            for kk in ('Anchor', 'LeftDirection', 'RightDirection'):
                node.set(kk, f'{nx} {ny}')
        hd = take('ud109')
        d.set_bounds(hd, X0, PRO_T + 1.4, X0 + 110.0, PRO_T + 8.4)
        d.set_text('ud10c', {0: CIN.get('titre_prochainement', 'prochainement').lower()})
        VED = [e for e in PRO if e.get('vedette_affiche')][:1]
        AUT = [e for e in PRO if e not in VED]
        si_ = 0
        y_ = PRO_T + 9.6
        if VED and VED[0].get('visuel_affiche'):       # visuel complet déjà composé (outils/visuel_cinekids.py)
            r_ = take(SLOTS[si_][0]); si_ += 1
            d.set_bounds(r_, X0 + 2.2, y_, X1 - 2.2, y_ + VED_H)
            r_.set('FillColor', 'Swatch/None'); r_.set('StrokeWeight', '0')
            img(r_, VED[0]['visuel_affiche'], 'fit', (0.5, 0.5))
        elif VED:
            place_slot(SLOTS[si_], X0 + 2.2, y_, VED_H, VED[0], X1 - 2.2, zoom=VED_ZOOM); si_ += 1
        if VED:
            y_ += VED_H + 3.0
        n_ = len(AUT)
        ew_ = EV_W if not VED else ((X1 - X0 - 4.4) - (n_ - 1) * 4.0) / max(1, n_)
        eh_ = EV_H if not VED else EV_H2
        gap_ = ((X1 - X0 - 4.4) - n_ * ew_) / max(1, n_ - 1) if n_ > 1 else 0
        x_ = X0 + 2.2 + ((X1 - X0 - 4.4) - n_ * ew_) / 2 if n_ == 1 else X0 + 2.2
        for k_, ev in enumerate(AUT):
            place_slot(SLOTS[si_], x_ + k_ * (ew_ + gap_), y_, eh_, ev, x_ + k_ * (ew_ + gap_) + ew_); si_ += 1
        print(f'Bandeaux « évènements » : vedette {VED_H} mm + {n_} × {ew_:.1f} × {eh_} mm' if VED else f'Bandeaux « évènements » : {n_} × {EV_W} × {EV_H} mm')
    PRO = []
    GRID_END = BODY_B
if SPE and len(PRO) == 3:
    src = SLOTS[2]
    nim, ntf, nln, ngrp = (d.duplicate(i) for i in src[:4])
    ndst = [c for c in ngrp if c.tag == 'TextFrame'][0].get('ParentStory')
    SLOTS.append((nim.get('Self'), ntf.get('Self'), nln.get('Self'), ngrp.get('Self'), ndst, src[5]))
free = list(range(len(SLOTS)))
PRO_SLOT_H, PRO_GAP = round((LX1 - LX0) / 2.85, 1), 2.0   # même proportion que les bandeaux du programme
pro_h = (9.6 + len(PRO) * PRO_SLOT_H + (len(PRO) - 1) * PRO_GAP + 2.2) if PRO else 0
col_b = GRID_END
if SPE:
    top = BODY_T
    bottom = (col_b - pro_h - 5.0) if PRO else col_b
    heading(LX0 - 2.2, top, LX1 + 2.2, top + 9.0, SPE['bandeau'], 13, fill='Color/Black')
    place_slot(SLOTS[free.pop(0)], LX0 - 2.2, top + 9.0, bottom - top - 9.0, SPE, LX1 + 2.2)
    fr = take('ubdf0', dup=True)
    for ch in list(fr):
        if ch.tag in ('Image', 'PDF', 'EPS'):
            fr.remove(ch)
    fr.set('ContentType', 'Unassigned'); fr.set('FillColor', 'Swatch/None')
    fr.set('StrokeColor', BLUE); fr.set('StrokeWeight', '3'); fr.set('StrokeAlignment', 'InsideAlignment')
    d.set_bounds(fr, LX0 - 2.2, top, LX1 + 2.2, bottom)
    if bottom - top < 45:
        WARN.append(f"Peu de place pour l'événement spécial ({bottom - top:.0f} mm)")
if PRO:
    ptop = col_b - pro_h
    box = take('ud24f')
    pp, pts = d.anchors(box)
    mi = inv(d.chain(box))
    corners = [(LX0 - 2.2, col_b), (LX0 - 2.2, ptop), (LX1 + 2.2, ptop), (LX1 + 2.2, col_b), (LX0 - 2.2, col_b)]
    for node, (x, yy) in zip(pp, corners):
        nx, ny = ap(mi, x * PT - OX, yy * PT - OY)
        for kk in ('Anchor', 'LeftDirection', 'RightDirection'):
            node.set(kk, f'{nx} {ny}')
    hd = take('ud109')
    d.set_bounds(hd, LX0 - 2.2, ptop + 1.4, LX1 - 6.0, ptop + 8.4)
    d.set_text('ud10c', {0: CIN.get('titre_prochainement', 'prochainement').lower()})
    for k_, ev in enumerate(PRO):
        place_slot(SLOTS[free.pop(0)], LX0, ptop + 9.6 + k_ * (PRO_SLOT_H + PRO_GAP), PRO_SLOT_H, ev, LX1)
    print(f'Bandeaux « prochainement » : {len(PRO)} × {PRO_SLOT_H} mm (mêmes images que le programme)')

# =====================================================================
# 4. tarifs, abonnements, bandeau réservations
# =====================================================================
TAR_T = GRID_END + 5.0
FOOT_T = float(os.environ.get('AFF_FOOT_T', 406.0))     # haut du pied de page projecteurs
BAN_H = 9.0
BAN_T = FOOT_T - 3.0 - BAN_H
d.set_bounds(take('ucdb9'), X0, TAR_T, X1, BAN_T + 3.3)
COLX = [(X0 + 3.0, 118.0), (130.0, X1 - 3.0)]
KT = float(os.environ.get('AFF_TARIFS', CIN.get('affiche_tarifs', 1.25)))     # tarifs agrandis
T583 = d.story('uc583').getroot().find('Story')
T59D = d.story('uc59d').getroot().find('Story')
P583 = T583.findall('ParagraphStyleRange')
P59D = T59D.findall('ParagraphStyleRange')
TPL_TITLE = copy.deepcopy(P583[0])
TPL_LINE = copy.deepcopy(P583[1]); TPL_LINE_CSR = [copy.deepcopy(c) for c in TPL_LINE.findall('CharacterStyleRange')[:5]]
TPL_SUB = copy.deepcopy(P583[2]); TPL_SUB_CSR = copy.deepcopy(TPL_SUB.findall('CharacterStyleRange')[0])
TPL_NOTE = copy.deepcopy(P583[7])
TPL_TXT = copy.deepcopy(P59D[1]); TPL_TXT_CSR = copy.deepcopy(TPL_TXT.findall('CharacterStyleRange')[0])
TPL_DETAIL_CSR = copy.deepcopy(P59D[3].findall('CharacterStyleRange')[2])
TPL_CENTRE = copy.deepcopy(P59D[6]); TPL_CENTRE_CSR = [copy.deepcopy(c) for c in TPL_CENTRE.findall('CharacterStyleRange')]
TPL_CENTRE2 = copy.deepcopy(P59D[7])


def _empty(p):
    p = copy.deepcopy(p)
    for c in p.findall('CharacterStyleRange'):
        p.remove(c)
    return p


def _set(c, text, br=True):
    for x in list(c):
        if x.tag in ('Content', 'Br'):
            c.remove(x)
    etree.SubElement(c, 'Content').text = text
    if br:
        etree.SubElement(c, 'Br')
    return c


def build_bloc(story, items):
    for p in story.findall('ParagraphStyleRange'):
        story.remove(p)
    for k, it in enumerate(items):
        last = k == len(items) - 1
        if 'titre' in it:
            p = copy.deepcopy(TPL_TITLE)
            _set(p.findall('CharacterStyleRange')[0], it['titre'], br=False)
        elif 'prix' in it:
            p = _empty(TPL_LINE)
            b, lab, tab, price, eur = [copy.deepcopy(c) for c in TPL_LINE_CSR]
            _set(b, '• ', False); _set(lab, it['ligne'] + (' ' if it.get('detail') else ''), False)
            p.append(b); p.append(lab)
            if it.get('detail'):
                p.append(_set(copy.deepcopy(TPL_DETAIL_CSR), it['detail'], False))
            p.append(_set(tab, '\t', False)); p.append(_set(price, it['prix'], False))
            p.append(_set(eur, '€', not last))
        elif 'sous' in it:
            p = _empty(TPL_SUB)
            p.append(_set(copy.deepcopy(TPL_SUB_CSR), '- ' + it['sous'], not last))
        elif 'texte' in it:
            p = _empty(TPL_TXT)
            p.append(_set(copy.deepcopy(TPL_TXT_CSR), it['texte'], not last))
        elif 'note' in it:
            p = copy.deepcopy(TPL_NOTE)
            _set(p.findall('CharacterStyleRange')[0], it['note'], not last)
        elif 'fort' in it:
            p = _empty(TPL_CENTRE)
            a, sp_, strong, b2 = [copy.deepcopy(c) for c in TPL_CENTRE_CSR[:4]]
            p.append(_set(a, '✶', False)); p.append(_set(sp_, ' ', False))
            p.append(_set(strong, it['fort'] + ' ', False)); p.append(_set(b2, '✶', not last))
        elif 'centre' in it:
            p = copy.deepcopy(TPL_CENTRE2)
            _set(p.findall('CharacterStyleRange')[0], it['centre'], not last)
        else:
            raise SystemExit(f'élément tarif inconnu : {it}')
        if 'titre' in it and not last:
            etree.SubElement(p.findall('CharacterStyleRange')[-1], 'Br')
        story.append(p)


build_bloc(T583, CIN['tarifs'])
build_bloc(T59D, CIN['abonnements'])
for _st in (T583, T59D):
    for _k, _p in enumerate(_st.findall('ParagraphStyleRange')):
        _p.set('SpaceBefore', '0')
        _p.set('SpaceAfter', '2.83' if _k == 0 else '0')


def set_tabs(sid, pos_pt):                    # prix calés à droite du cadre (points de conduite)
    for pos in d.story(sid).getroot().iter('Position'):
        if pos.getparent().tag == 'ListItem':
            pos.text = str(pos_pt)


for sid, (cx0, cx1) in (('uc583', COLX[0]), ('uc59d', COLX[1])):
    for cr in d.story(sid).getroot().iter('CharacterStyleRange'):
        if cr.get('PointSize') is None:
            cr.set('PointSize', '7.5')           # taille du style rendue explicite avant agrandissement
    scale_story(sid, KT, lead=1.18)
    set_tabs(sid, (cx1 - cx0) * PT - 2)
d.set_bounds(take('uc580'), COLX[0][0], TAR_T + 2.5, COLX[0][1], BAN_T - 0.5)
d.set_bounds(take('uc599'), COLX[1][0], TAR_T + 2.5, COLX[1][1], BAN_T - 0.5)
sep = take('ucdba')
_lx0, _ly0, _lx1, _ly1 = d.bbox(sep)
d.move(sep, (COLX[0][1] + COLX[1][0]) / 2 - _lx0, 0)
shift_points_y(d, sep, _ly0, TAR_T + 3.0)
shift_points_y(d, sep, _ly1, BAN_T - 2.0)
ban = take('ucdbc')
d.set_bounds(ban, X0, BAN_T, X1, BAN_T + BAN_H)
vcenter(ban)
_tfp = ban.find('TextFramePreference')                                # bandeau fin : ni marge interne,
_tfp.set('InsetSpacing', '0 0 0 0')                                   # ni espace avant (9 mm dans le gabarit)
for _x in _tfp.iter('InsetSpacing'):
    _x.text = '0'
for _p in d.story('ucdbe').getroot().iter('ParagraphStyleRange'):
    _p.set('SpaceBefore', '0'); _p.set('SpaceAfter', '0')
for _l in d.story('ucdbe').getroot().iter('Leading'):
    _l.text = '13'
d.set_text('ucdbe', {0: CIN['bandeau_bas'][0], 1: CIN['bandeau_bas'][1]})
for _c in d.story('ucdbe').getroot().iter('CharacterStyleRange'):
    _c.set('BaselineShift', '0')
text_size('ucdbe', float(CIN.get('affiche_bandeau_bas_corps', 11)), lead=float(CIN.get('affiche_bandeau_bas_corps', 11)) * 1.15, align='CenterAlign')

# =====================================================================
# 5. pied de page : projecteurs + adresse (bloc de la couverture)
# =====================================================================
fbg = take('uc86a', dup=True)               # fond noir sous la photo (sinon le fondu part dans le blanc)
d.set_bounds(fbg, -BL, FOOT_T, W_PAGE + BL, H_PAGE + BL)
foot = take('uc91b')
d.set_bounds(foot, -BL, FOOT_T, W_PAGE + BL, H_PAGE + BL)
for _fx in foot.iter('DirectionalFeatherSetting'):   # fondu de 30 mm du gabarit : trop pour 14 mm de haut
    _fx.set('Applied', 'false')
img(foot, PHOTO_PROJ, 'fill', (0.5, 0.75))
c = CIN['contact']                         # une ligne d'adresse + la mention, centrées
d.set_text('uc470', {0: c[0] + ' · ', 1: None, 2: c[1] + ' · ', 3: None, 4: c[2]})
d.set_text('ud420', {0: CIN.get('mention_gestion', '')})
for sid, pt in (('uc470', 11), ('ud420', 7.5)):
    text_size(sid, pt, align='CenterAlign')
    for cr in d.story(sid).getroot().iter('CharacterStyleRange'):
        cr.set('FillColor', 'Color/Paper')           # tout en blanc : lisible sur la photo sombre
d.set_bounds(take('uc46c'), 15.0, FOOT_T + 2.0, W_PAGE - 15.0, FOOT_T + 7.5)
d.set_bounds(take('ud41d'), 15.0, FOOT_T + 8.0, W_PAGE - 15.0, FOOT_T + 11.5)
vcenter('uc46c')

# =====================================================================
# 6. nettoyage : tout le reste du gabarit disparaît, page 2 supprimée
# =====================================================================
for sp in (SP1, SP2):
    root = d.spreads[sp].getroot().find('Spread')
    for ch in list(root):
        if ch.tag in ITEMS and ch.get('Self') not in KEEP:
            d.delete(ch.get('Self'))
d.save()
dm = d.dm.getroot()
for e in list(dm.iter('{*}Spread')):
    if e.get('src') == SP2:
        e.getparent().remove(e)
d.dm.write(f'{ROOT}/designmap.xml', xml_declaration=True, encoding='UTF-8', standalone=True)
os.remove(f'{ROOT}/{SP2}')
pp = f'{ROOT}/Resources/Preferences.xml'
s = open(pp, encoding='utf-8').read()
s = re.sub(r'(<DocumentPreference[^>]*?)PageHeight="[^"]*"', rf'\1PageHeight="{H_PAGE * PT}"', s)
s = re.sub(r'(<DocumentPreference[^>]*?)PageWidth="[^"]*"', rf'\1PageWidth="{W_PAGE * PT}"', s)
open(pp, 'w', encoding='utf-8').write(s)
for mpth in glob.glob(f'{ROOT}/MasterSpreads/*.xml'):
    s = open(mpth, encoding='utf-8').read()
    s = s.replace('GeometricBounds="0 0 595.275590551 841.889763778"', f'GeometricBounds="0 0 {H_PAGE * PT} {W_PAGE * PT}"')
    open(mpth, 'w', encoding='utf-8').write(s)

# couleur du cinéma + polices (comme programme.py)
hexc = CIN['couleur'].lstrip('#')
rgb = ' '.join(str(int(hexc[i:i + 2], 16)) for i in (0, 2, 4))
gp = f'{ROOT}/Resources/Graphic.xml'
gx = open(gp, encoding='utf-8').read()
for k, old in enumerate(['C=0 M=100 J=100 N=0', 'C=0 M=88 J=75 N=0', 'R=187 V=24 B=27', 'R=165 V=22 B=26',
                         'C=15 M=100 J=100 N=0', 'C=75 M=22 J=71 N=0', 'C=75 M=22 J=71 N=0 copie',
                         'C=75 M=22 J=71 N=0 copie 2']):
    m = re.search(r'(<Color Self="Color/' + re.escape(old) + r'"[^>]*/>)', gx)
    el = m.group(1)
    el2 = re.sub(r'Space="[^"]*"', 'Space="RGB"', el)
    el2 = re.sub(r'ColorValue="[^"]*"', f'ColorValue="{rgb}"', el2)
    el2 = re.sub(r' Name="[^"]*"', f' Name="{CIN["nom_couleur"]}{"" if k == 0 else " " + str(k + 1)}"', el2)
    gx = gx.replace(el, el2)
# déclinaisons (comme le programme) : sur l'affiche, seule l'alternance des lignes de grille (« R=211 V=211 B=211 »)
for _old, _hx in CIN.get('declinaisons', {}).items():
    if not _old.startswith('R=211'):
        continue
    m = re.search(r'(<Color Self="Color/' + re.escape(_old) + r'"[^>]*/>)', gx)
    if not m:
        continue
    _hx = _hx.lstrip('#'); _rgb = ' '.join(str(int(_hx[i:i + 2], 16)) for i in (0, 2, 4))
    el = m.group(1)
    el2 = re.sub(r'Space="[^"]*"', 'Space="RGB"', el)
    el2 = re.sub(r'ColorValue="[^"]*"', f'ColorValue="{_rgb}"', el2)
    el2 = re.sub(r' Name="[^"]*"', f' Name="{CIN["nom_couleur"]} - {_old.split(" ")[0]} #{_hx.upper()}"', el2)
    gx = gx.replace(el, el2)
_base = re.search(r'(<Color Self="Color/C=0 M=100 J=100 N=0"[^>]*/>)', gx).group(1)
for _nm, _hx in CIN.get('couleurs_grille', {}).items():
    _hx = _hx.lstrip('#'); _rgb = ' '.join(str(int(_hx[i:i + 2], 16)) for i in (0, 2, 4))
    _el = re.sub(r'Self="[^"]*"', f'Self="Color/Grille {_nm}"', _base)
    _el = re.sub(r' Name="[^"]*"', f' Name="Grille {_nm}"', _el)
    _el = re.sub(r'ColorValue="[^"]*"', f'ColorValue="{_rgb}"', _el)
    gx = gx.replace(_base, _base + '\n\t' + _el)
open(gp, 'w', encoding='utf-8').write(gx)
for p in glob.glob(f'{ROOT}/Stories/*.xml') + [f'{ROOT}/Resources/Styles.xml']:
    s = open(p, encoding='utf-8').read()
    s2 = s
    for old in ('37 Thin Condensed', '47 Light Condensed Oblique', '57 Condensed'):
        s2 = s2.replace(f'FontStyle="{old}"', 'FontStyle="67 Medium Condensed"')
    if s2 != s:
        open(p, 'w', encoding='utf-8').write(s2)

# =====================================================================
# 7. paquet de sortie
# =====================================================================
name = MOIS.get('nom_affiche') or MOIS['nom_fichier'].replace('PROGRAMME', 'AFFICHE A3')
pk = os.path.join(A.out, name)
os.makedirs(os.path.join(pk, 'Links'), exist_ok=True)
with zipfile.ZipFile(os.path.join(pk, name + '.idml'), 'w') as z:
    z.write(f'{ROOT}/mimetype', 'mimetype', compress_type=zipfile.ZIP_STORED)
    for root, _, files in os.walk(ROOT):
        for f in sorted(files):
            p = os.path.join(root, f); a = os.path.relpath(p, ROOT)
            if a != 'mimetype':
                z.write(p, a, compress_type=zipfile.ZIP_DEFLATED)
for p in USED:
    shutil.copy(p, os.path.join(pk, 'Links', os.path.basename(p)))
print('OK', pk, '|', name)
for w in WARN:
    print('ATTENTION :', w)
