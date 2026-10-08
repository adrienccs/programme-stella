#!/usr/bin/env python3
"""
Moteur « Programme cinéma 3 volets » — Copy Color Service.

Construit l'IDML d'un programme mensuel à partir :
  - du gabarit InDesign (gabarit/GABARIT_3_VOLETS.idml, maquette Fauteuil Rouge),
  - d'une fiche cinéma  (cinemas/<cinema>.json : couleur, logo, tarifs, adresse...),
  - d'une fiche mois    (mois/<cinema>-AAAA-MM.json : films, horaires, événements, images).

Usage :
  python3 programme.py --kit KIT --cinema cinemas/7emeart.json --mois mois/7emeart-2026-10/mois.json \
                       --images DOSSIER_IMAGES --out DOSSIER_SORTIE

Mise en page : 4 volets = 4 semaines (intérieur gauche, milieu, droite, puis extérieur gauche),
chacun avec ses fiches film (1 à 4, choisies par « fiches »), une image de remplissage éventuelle,
et sa grille horaire en bas (jusqu'à 9 films, styles de séances, cases fusionnées, jours fermés).
Extérieur milieu : « prochainement » (0 à 2 bandeaux) + remerciements + tarifs/abonnements.
Couverture : logo, dates, 6 affiches, encart événement spécial (optionnel).
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
ap_.add_argument('--images', required=True, help='dossier contenant toutes les images citées')
ap_.add_argument('--out', required=True)
A = ap_.parse_args()

CIN = json.load(open(A.cinema, encoding='utf-8'))
sys.path.insert(0, os.path.abspath(A.kit))
from commun import seances, bandeau          # code des séances + bandeau du réseau (programme-commun, 08/10/2026)
CIN = seances.appliquer(CIN)
MOIS = json.load(open(A.mois, encoding='utf-8'))
IMG_DIRS = [A.images, os.path.join(A.kit, 'assets', 'cinemas', CIN['id']), os.path.join(A.kit, 'assets', 'communs')]

ROOT = os.path.join(A.out, '_idml')
shutil.rmtree(ROOT, ignore_errors=True)
with zipfile.ZipFile(os.path.join(A.kit, 'assets', 'gabarit', 'GABARIT_3_VOLETS.idml')) as z:
    z.extractall(ROOT)
d = Doc(ROOT)
SP1, SP2 = 'Spreads/Spread_u2a1b.xml', 'Spreads/Spread_uc313.xml'
P2 = 279.5          # décalage vertical de la page 2 (coordonnées mm internes)
BLUE = 'Color/C=0 M=100 J=100 N=0'   # nuance « accent » du gabarit, recolorée avec la couleur du cinéma
LINKDIR = CIN.get('dossier_liens_mac') or ''   # URI file:/... du dossier Links côté Mac
if not LINKDIR.startswith('file:/'):            # sans chemin file:/ valide, InDesign ignore les liens (cadres vides)
    LINKDIR = 'file:/Volumes/Clients/Links/'
    print('ATTENTION : dossier_liens_mac absent ou invalide → liens écrits vers', LINKDIR, '(le script les reliera)')
if not LINKDIR.endswith('/'):
    LINKDIR += '/'
USED = set()
WARN = []

d._image_template = copy.deepcopy(d.el('u8423').find('Image'))
grid.capture(d)
grid.ROUGE = 'Color/Grille rouge' if 'rouge' in CIN.get('couleurs_grille', {}) else None
grid.TITRE_UNE_LIGNE = bool(CIN.get('titres_grille_entiers'))   # Stella 08/10/2026 : titres jamais en « gros + petit »
TEMPLATE_SYN = copy.deepcopy(d.story('ubb36').getroot().find('Story'))


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
    d.place_image(rect, LINKDIR + urllib.parse.quote(fname), w, h, mode, ext, align)
    return w, h


def E(i):
    return d.el(i) if isinstance(i, str) else i


def to_spread(el, sp):
    el = E(el)
    el.getparent().remove(el)
    d.spreads[sp].getroot().find('Spread').append(el)
    return el


def story_of(f):
    return E(f).get('ParentStory')


# =====================================================================
# 0. nettoyage du gabarit
# =====================================================================
for t in d.spreads.values():
    for r in t.xpath('//Rectangle[.//Link[contains(@LinkResourceURI,"pictos%20films")]]'):
        r.getparent().remove(r)
for i in ['u83a2', 'u83d4', 'u83ed', 'u8406', 'u83bb', 'u8423', 'u8532', 'u8564', 'u857d', 'ub09e', 'u854b', 'u85b3',
          'ub0de', 'ub110', 'ub129', 'ub142', 'ub0f7', 'ub0d9', 'u89c7', 'u89f9', 'u8a12', 'u8a2b', 'u89e0', 'u8a44',
          'ubd3b', 'ubd6d', 'ubd86', 'ubd9f', 'ubd54', 'ubd34', 'ubdf5', 'ube27', 'ube40', 'ube59', 'ube0e',
          'ubb1a', 'ubb4c', 'ubb65', 'ubb7e', 'ubb33', 'ubb16', 'ubbe4', 'ubc16', 'ubc2f', 'ubc48', 'ubbfd', 'ubbde',
          'ubc8e', 'ubcc1', 'ubcda', 'ubcf3', 'ubca8', 'ubc89', 'ubf62', 'ubf94', 'ubfad', 'ubfc6', 'ubf7b', 'ubfea',
          'uc065', 'ud215', 'ud22f', 'ud231',
          'ucf71', 'ucfd4', 'uce0b', 'uc44e', 'uce0c', 'ud2ce', 'uce14', 'ud2f3', 'uc35f', 'uc312',
          'ucdaf']:   # ucdaf = cadre magenta de repère (calque GABARIT) sur la couverture
    d.delete(i)

# =====================================================================
# 1. fiches film
# =====================================================================
FICHE_SRC = ('ubea8', 'ubedb', 'ubef4', 'ubf0d', 'ubec2', 'ubea5')   # titre, durée, pays, pictos, résumé, affiche
COLS = [(5.8, 95.8, SP1, 0), (103.4, 195.8, SP1, 0), (202.3, 292.3, SP1, 0), (4.6, 94.6, SP2, P2)]
TOP = 15.5          # haut de la 1re fiche
H_FILM_PT = float(CIN.get('h_ligne_grille', 22.0))    # hauteur ligne de grille


def hf(we):                          # hauteur de ligne d'une semaine (« h_ligne » pour resserrer une grille chargée)
    return float(we.get('h_ligne', H_FILM_PT))
LEGENDE = True                                 # légende du réseau (programme-commun) : seuls les codes présents
LEG_LEAD_MM = 6.5 * 25.4 / 72                  # interligne de la légende (6,5 pt)


def codes_semaine(we):
    """codes réellement utilisés dans une semaine (séances, courts, coups de cœur, pictos)"""
    return seances.codes_utilises(we['films'], films=MOIS['films'])


def legende_semaine(we):
    """légende du réseau limitée aux codes présents dans la semaine (décision d'Adrien du 08/10/2026)"""
    return seances.lignes_legende(codes_semaine(we))


GRID_BOTTOM = 206.0


def fill_synopsis(fid, f):
    st = d.story(story_of(fid)).getroot().find('Story')
    keep = [c for c in st if c.tag in ('StoryPreference', 'InCopyExportOption')]
    for c in list(st):
        st.remove(c)
    for c in keep:
        st.append(c)
    for c in TEMPLATE_SYN:
        if c.tag == 'ParagraphStyleRange':
            st.append(copy.deepcopy(c))
    sid = story_of(fid)
    d.set_text(sid, {0: f['resume'], 2: f'Réalisé par {f["realisateur"]}. Sortie : {f["sortie"]}', 6: f'Genre : {f["genre"]}'})
    if f.get('avec'):
        d.set_text(sid, {4: 'Avec ' + f['avec']})
    else:
        d.set_text(sid, {4: None, 5: None})


def make_fiche(key, x0, y0, sp, pitch, X1):
    f = MOIS['films'][key]
    s = tuple(d.duplicate(i) for i in FICHE_SRC)
    if sp != SP1:
        s = tuple(to_spread(i, sp) for i in s)
    off = P2 if sp == SP2 else 0
    px0, py0, _, _ = d.bbox(s[5])
    for i in s:
        d.move(i, x0 - px0, (y0 + off) - py0)
    t, du, co, pi, sy, po = s
    d.set_text(story_of(t), {0: f['titre']})
    if len(f['titre']) >= 37:                    # titre long : chasse réduite pour tenir sur une ligne
        for c in d.story(story_of(t)).getroot().iter('CharacterStyleRange'):
            c.set('HorizontalScale', '76' if len(f['titre']) > 38 else '82')
    d.set_text(story_of(du), {0: f['duree']})
    d.set_text(story_of(co), {0: f['pays']})
    fill_synopsis(sy, f)
    ph = min(PH, pitch - 3.0)               # même taille d'affiche dans tous les volets
    bx0, by0, _, _ = d.bbox(po)
    d.set_bounds(po, bx0, by0, bx0 + ph * 0.75, by0 + ph)
    img(po.get('Self'), f['affiche'], 'fill', tuple(f.get('cadrage_affiche', (0.5, 0.0))), affiche=True)   # « cadrage_affiche » : [x, y] (1.0 = bas)
    cx0, cy0, cx1, cy1 = d.bbox(co)
    qx0, qy0, qx1, qy1 = d.bbox(pi)
    d.set_bounds(co, cx0, cy0, cx0 + 31, cy1)
    d.set_bounds(pi, cx0 + 31, qy0, qx1, qy1)
    sx0, sy0, sx1, sy1 = d.bbox(sy)
    d.set_bounds(sy, sx0, sy0, X1 - 0.2, by0 + min(36.0, pitch - 3.0) + 0.5)   # texte : toute la place du créneau
    for el in (t, pi):          # titre et barre grise jusqu'au bord du volet
        a0, b0, a1, b1 = d.bbox(el)
        d.set_bounds(el, a0, b0, X1, b1)
    return s


def big_heading(h, pt):
    for c in d.story(story_of(h)).getroot().iter('CharacterStyleRange'):
        c.set('PointSize', str(pt))
    for p in d.story(story_of(h)).getroot().iter('ParagraphStyleRange'):
        p.set('LeftIndent', '0'); p.set('Justification', 'CenterAlign')
    tfp = h.find('TextFramePreference')
    if tfp is not None:
        tfp.set('VerticalJustification', 'CenterAlign')


WEEKENDS = MOIS.get('semaines') or MOIS['weekends']
if len(WEEKENDS) > 4:
    raise SystemExit('4 semaines maximum (4 volets)')


def _norm(e):                       # [clé, séances, options?] ou {"film", "seances", ...options}
    if isinstance(e, dict):
        o = {k: v for k, v in e.items() if k not in ('film', 'seances')}
        return [e['film'], e.get('seances', {}), o]
    return [e[0], e[1], e[2] if len(e) > 2 else {}]


for _we in WEEKENDS:
    _we['films'] = [_norm(e) for e in _we['films']]
# bas des grilles : la légende (2 ou 3 lignes selon la semaine la plus chargée) doit tenir au-dessus du massicot
LEG_N = max((len(legende_semaine(w) or []) for w in WEEKENDS), default=0)
GRID_BOTTOM = (202.0 - max(0, LEG_N - 2) * 1.5) if LEGENDE else 206.0   # 3 lignes : grilles remontées de 1,5 mm

def _premiere(item):              # ordre de diffusion = 1re séance du week-end
    s = item[1]
    best = (99, 99 * 60)
    for j, hs in s.items():
        for h in hs:
            h = h if isinstance(h, str) else h['h']
            m = re.match(r'(\d+)h(\d*)', h)
            t = int(m.group(1)) * 60 + int(m.group(2) or 0) if m else 0
            best = min(best, (int(j), t))
    return best


def film_image(we):                 # film de l'image de remplissage : clé « film », sinon déduit du nom de fichier
    ir = we.get('image_remplissage')
    if not ir:
        return None
    if ir.get('film'):
        return ir['film']
    nom = ir['image'].lower()
    for k in (we.get('fiches') or [f[0] for f in we['films']]):
        aff = MOIS['films'][k].get('affiche', '').lower().rsplit('.', 1)[0]
        if aff and nom.startswith(aff):
            return k
    return None


def ordre_fiches(we):               # fiches : ordre de diffusion, sauf ordre imposé (« ordre_fiches » / « fiches »)
    if we.get('fiches'):            # 7e Art : seulement certains films ont une fiche, triées par 1re séance
        def prem(k):                # 1re séance du film dans la semaine, toutes lignes confondues
            return min(_premiere(f) for f in we['films'] if f[0] == k)
        keys = list(dict.fromkeys(we['fiches']))
        if we.get('ordre_fiches'):
            keys.sort(key=lambda k: we['ordre_fiches'].index(k))
        else:
            keys.sort(key=prem)
        fi = film_image(we)          # le film illustré par l'image de remplissage passe juste avant elle
        if fi in keys:
            keys.remove(fi); keys.append(fi)
        return [[k, {}, {}] for k in keys]
    if we.get('ordre_fiches'):
        out = sorted(we['films'], key=lambda f: we['ordre_fiches'].index(f[0]))
    else:
        out = sorted(we['films'], key=_premiere)
    fi = film_image(we)
    if fi and not we.get('ordre_fiches'):
        out = [f for f in out if f[0] != fi] + [f for f in out if f[0] == fi]
    return out


heads_src = ['ud0c7', 'ud0e9']
# hauteur d'affiche UNIQUE pour tout le programme (la plus petite place disponible commande)
_ph = []
for _we in WEEKENDS:
    _gtop = GRID_BOTTOM - (grid.H_DAYS + len(_we['films']) * hf(_we)) * 25.4 / 72
    _ph.append(min(36.0, min(39.0, (_gtop - 3 - TOP) / len(ordre_fiches(_we))) - 3.0))
PH = min(_ph)
for vi, we in enumerate(WEEKENDS):
    x0, x1, sp, off = COLS[vi]
    n = len(we['films'])                        # lignes de grille
    nf = len(ordre_fiches(we))                  # fiches résumé
    if not 1 <= nf <= 4 or n > 10:          # Stella : jusqu’à 10 films dans une semaine (h_ligne 18)
        raise SystemExit(f"Volet {vi+1} : {nf} fiches (1 à 4) et {n} lignes de grille (10 max)")
    # heading
    h = E(heads_src[vi]) if vi < 2 else d.duplicate('ud0e9')
    if sp != SP1:
        to_spread(h, sp)
    d.set_bounds(h, x0, 4.5 + off, x1, 13.0 + off)
    big_heading(h, 12.5)
    d.set_text(story_of(h), {0: we.get('titre_volet', we['titre']).lower()})
    # grid
    grid_h = (grid.H_DAYS + n * hf(we)) * 25.4 / 72
    gtop = GRID_BOTTOM - grid_h
    pitch = min(39.0, (gtop - 3 - TOP) / nf)
    if pitch < 30:
        WARN.append(f"Volet {vi+1} : fiches serrées ({pitch:.1f} mm) — réduire le nombre de fiches")
    top_f = TOP
    _spe = MOIS.get('evenement_special')
    if _spe and _spe['volet'] - 1 == vi and _spe.get('position', 'bas') == 'haut':
        # événement AVANT les résumés (logique « soirée + résumé du film »)
        ev_h = (gtop - 2.5) - TOP - (nf * pitch - 2.5) - 2.0
        if ev_h < 30:
            WARN.append(f"Volet {vi+1} : seulement {ev_h:.0f} mm pour l'événement en haut")
        we['_ev'] = (TOP, TOP + ev_h)
        top_f = TOP + ev_h + 2.0
    for k, (key, *_r) in enumerate(ordre_fiches(we)):
        make_fiche(key, x0, top_f + k * pitch, sp, pitch, x1)
    we['_fiches_bottom'] = top_f + nf * pitch - 3.0 + 0.5
    we['_gtop'] = gtop

# contrôle : chaque film avec un résumé doit avoir sa fiche au moins une fois dans le mois
_avec_fiche = {f[0] for we in WEEKENDS for f in ordre_fiches(we)}
for _k, _f in MOIS['films'].items():
    if _f.get('resume') and not _f.get('court') and _k not in _avec_fiche \
            and any(f[0] == _k for we in WEEKENDS for f in we['films']):
        WARN.append(f"« {_f['titre']} » n'a de fiche résumé dans aucune semaine")
# contrôle : une avant-première a TOUJOURS sa fiche dans la semaine de l'avant-première
for _vi, _we in enumerate(WEEKENDS):
    _fi = {f[0] for f in ordre_fiches(_we)}
    for _k, _s, _o in _we['films']:
        _ap = 'avant-premi' in (str(_o.get('etiquette', '')) + str((_o.get('fusion') or {}).get('texte', ''))).lower()
        if _ap and _k not in _fi:
            WARN.append(f"Volet {_vi+1} : avant-première « {MOIS['films'][_k]['titre']} » sans fiche résumé")

# grilles
for vi, we in enumerate(WEEKENDS):
    x0, x1, sp, off = COLS[vi]
    g = d.duplicate('ucf09')
    to_spread(g, sp)
    films_grille = list(we['films']) if CIN.get('ordre_grille') == 'saisie' else sorted(we['films'], key=_premiere)
    gw = {'titre': we['titre'], 'days': we['jours'], 'fermes': we.get('fermes', []),
          'films': [(MOIS['films'][k].get('grille', MOIS['films'][k]['titre']), MOIS['films'][k]['duree'],
                     {int(i): v for i, v in seances.items()},
                     {**({'court': True} if MOIS['films'][k].get('court') else {}), **o})
                    for k, seances, o in films_grille]}
    h = grid.build_one(d, g.get('ParentStory'), gw, (x1 - x0) * PT, h_film=hf(we),
                       split=MOIS['films'])
    gx0, gy0, _, _ = d.bbox(g)
    d.set_bounds(g, gx0, gy0, gx0 + (x1 - x0) + 0.5, gy0 + h + 7)
    d.move(g, x0 - gx0, (GRID_BOTTOM + off - h) - gy0)
    # picto « malentendants » (boucle magnétique, picto officiel du Fauteuil Rouge) en bas à droite de la case titre
    _gt = GRID_BOTTOM + off - h
    _tw = ((x1 - x0) * PT - 7 * 22.0) / PT
    for _ri, (_k, _s, _o) in enumerate(films_grille):
        if _o.get('malentendants'):
            _ph = 3.0
            _yb = _gt + (grid.H_DAYS + (_ri + 1) * hf(we)) / PT - 0.8
            _xr = x0 + _tw - 1.0
            _r = d.duplicate('ubdf0')
            to_spread(_r, sp)
            d.set_bounds(_r, _xr - _ph, _yb - _ph, _xr, _yb)
            _r.set('FillColor', 'Swatch/None'); _r.set('StrokeWeight', '0')
            img(_r.get('Self'), CIN.get('picto_malentendants', '7EA picto malentendants.png'), 'fit')
d.delete('ucf09')

if LEGENDE:                                       # légende sous chaque grille, lignes coupées à la main
    # LEGENDE = [[[texte, style], ...] par ligne] ; style : r rouge, s souligné, i italique, v violet, b bleu
    if isinstance(LEGENDE, str):
        LEGENDE = [[[LEGENDE, '']]]
    for vi, we in enumerate(WEEKENDS):
        x0, x1, sp, off = COLS[vi]
        lg = d.duplicate('ubedb')
        to_spread(lg, sp)
        lg.set('FillColor', 'Swatch/None')
        LEG_W = legende_semaine(we)
        d.set_bounds(lg, x0, GRID_BOTTOM + off + 0.5, x1, GRID_BOTTOM + off + 0.5 + LEG_N * LEG_LEAD_MM + 0.1)
        st = d.story(story_of(lg)).getroot()
        psr = st.find('Story/ParagraphStyleRange')
        for extra in st.find('Story').findall('ParagraphStyleRange')[1:]:
            extra.getparent().remove(extra)
        psr.set('Justification', 'CenterAlign'); psr.set('LeftIndent', '0')
        tpl = copy.deepcopy(psr.find('CharacterStyleRange'))
        for c in psr.findall('CharacterStyleRange'):
            psr.remove(c)
        for x in list(tpl):
            if x.tag in ('Content', 'Br'):
                tpl.remove(x)
        tpl.set('PointSize', '6'); tpl.set('FillColor', 'Color/Black'); tpl.set('FontStyle', '67 Medium Condensed')
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
        ld.text = '6.5'
        for li, ligne in enumerate(LEG_W):
            for si, (txt, sty) in enumerate(ligne):
                c = copy.deepcopy(tpl)
                if sty.startswith('p:'):          # picto image : pas dessiné dans ce moteur → texte seul
                    WARN.append(f"picto « {sty[2:]} » utilisé : pas encore dessiné dans les grilles de ce cinéma")
                    continue
                seances.style_run(c, sty, BLUE, grid.set_font)
                last = si == len(ligne) - 1
                etree.SubElement(c, 'Content').text = txt + ('\u2028' if last and li < len(LEG_W) - 1 else '')
                psr.append(c)
        tfp = lg.find('TextFramePreference')
        if tfp is not None:
            tfp.set('VerticalJustification', 'TopAlign')


# bas arrondi des grilles
def round_bottom(x0, x1, ybot, sp, h_row=None):
    h_row = h_row or H_FILM_PT
    g = d.duplicate('ud2ed')
    to_spread(g, sp)
    u = [c for c in g if c.tag == 'Rectangle' and c.get('StrokeTint') == '70'][0]
    ux0, _, _, uy1 = d.bbox(u)
    d.move(g, x0 - ux0, ybot - uy1)
    dw = (x1 - x0) - 90.0
    if abs(dw) > 0.01:
        mid = x0 + 45.0
        for c in g:
            if c.tag != 'Rectangle':
                continue
            cx0, cy0, cx1, cy1 = d.bbox(c)
            if (cx1 - cx0) > 20:
                m = d.chain(c); mi = inv(m)
                for node in c.find('Properties/PathGeometry/GeometryPathType/PathPointArray'):
                    for k in ('Anchor', 'LeftDirection', 'RightDirection'):
                        X, Y = ap(m, *M(node.get(k)))
                        if (X + OX) / PT > mid:
                            X += dw * PT
                        nx, ny = ap(mi, X, Y)
                        node.set(k, f'{nx} {ny}')
            elif (cx0 + cx1) / 2 > mid:
                d.move(c, dw, 0)
    u = [c for c in g if c.tag == 'Rectangle' and c.get('StrokeTint') == '70'][0]
    m = d.chain(u); mi = inv(m)
    pts = list(u.find('Properties/PathGeometry/GeometryPathType/PathPointArray'))
    for node in (pts[0], pts[-1]):
        for k in ('Anchor', 'LeftDirection', 'RightDirection'):
            X, Y = ap(m, *M(node.get(k)))
            nx, ny = ap(mi, X, (ybot - h_row * 25.4 / 72) * PT - OY)
            node.set(k, f'{nx} {ny}')
    # coins arrondis : les coins carrés des cellules de la dernière ligne (fond rose/gris) dépassaient de la courbe
    # → 2 caches pleins blancs qui épousent l'arrondi, sous le filet (repris du Fauteuil Rouge, retour Adrien 08/10/2026)
    pts = list(u.find('Properties/PathGeometry/GeometryPathType/PathPointArray'))
    L, yb = M(pts[1].get('Anchor'))[0], M(pts[2].get('Anchor'))[1]
    R = M(pts[4].get('Anchor'))[0]
    rx = M(pts[2].get('Anchor'))[0] - L
    ry = yb - M(pts[1].get('Anchor'))[1]
    e = 1.2
    coins = [
        [((L - e, yb - ry),) * 3, ((L, yb - ry),) * 3, ((L + rx, yb), (L, yb), (L + rx, yb)),
         ((L + rx, yb + e),) * 3, ((L - e, yb + e),) * 3],
        [((R - rx, yb),) * 3, ((R, yb - ry), (R, yb), (R, yb - ry)), ((R + e, yb - ry),) * 3,
         ((R + e, yb + e),) * 3, ((R - rx, yb + e),) * 3],
    ]
    for coin in coins:
        c = copy.deepcopy(u)
        c.set('Self', d.newid())
        c.set('FillColor', 'Color/Paper')
        c.set('StrokeColor', 'Swatch/None'); c.set('StrokeWeight', '0')
        for _a in ('StrokeTint',):
            if c.get(_a) is not None:
                del c.attrib[_a]
        gp = c.find('Properties/PathGeometry/GeometryPathType')
        gp.set('PathOpen', 'false')
        arr = gp.find('PathPointArray')
        for n in list(arr):
            arr.remove(n)
        for (a, l, r_) in coin:
            n = etree.SubElement(arr, 'PathPointType')
            n.set('Anchor', f'{a[0]} {a[1]}'); n.set('LeftDirection', f'{l[0]} {l[1]}')
            n.set('RightDirection', f'{r_[0]} {r_[1]}')
        u.addprevious(c)


for vi, we in enumerate(WEEKENDS):
    x0, x1, sp, off = COLS[vi]
    round_bottom(x0, x1, GRID_BOTTOM + off, sp, hf(we))
d.delete('ud2ed')

# =====================================================================
# 2. bandeaux événements (gabarit « avant-première »)
# =====================================================================
SLOTS = [('uc035', 'ud126', 'ud145', 'ud1a6', 'uc139', (0, 2, 5, 9)),
         ('uc043', 'ud157', 'ud170', 'ud1a7', 'ud1ab', (0, 2, 6, 10)),
         ('uc054', 'ud1cc', 'ud200', 'ud1e5', 'ud1e9', (0, 2, 5, 9))]


def grow_date(grp, dst, top, h):
    g = E(grp)
    tf = [c for c in g if c.tag == 'TextFrame'][0]
    for ln in [c for c in g if c.tag == 'Polygon']:
        g.remove(ln)
    x0, y0, x1, y1 = d.bbox(tf)
    d.set_bounds(tf, x1 - 31.0, top + 1.0, x1, top + h - 1.0)
    tfp = tf.find('TextFramePreference')
    if tfp is not None:
        tfp.set('VerticalJustification', 'CenterAlign')
    for c in d.story(dst).getroot().iter('CharacterStyleRange'):
        ps = float(c.get('PointSize', '12'))
        c.set('PointSize', str(round(ps * 1.35, 1)))
        p = c.find('Properties')
        if p is not None and p.find('Leading') is not None:
            p.find('Leading').text = str(round(float(p.find('Leading').text) * 1.3, 1))


BCTX = bandeau.Contexte(d=d, E=E, img=img, story_of=story_of, etree=etree, alertes=WARN)
TOUS_EVTS = [e for e in [MOIS.get('evenement_special')] + list(MOIS.get('prochainement', []) or []) if e]

def place_slot(slot, x0, top, h, ev, sp):
    im_, tf, ln, grp, dst, idx = slot
    if sp != SP1:
        for i in (im_, tf, ln, grp):
            to_spread(i, sp)
    off = P2 if sp == SP2 else 0
    ix0, iy0, ix1, iy1 = d.bbox(E(im_))
    w = ix1 - ix0
    if ev.get('visuel_programme'):                 # bandeau déjà composé (ex. outils/bloc_cinekids.py --largeur 89.7)
        d.set_bounds(E(im_), x0, top + off, x0 + w, top + off + h)
        E(im_).set('FillColor', 'Swatch/None')
        img(im_, ev['visuel_programme'], 'fill', (0.5, 0.5))
        for i in (tf, ln, grp):
            d.delete(i)
        return
    bandeau.poser(BCTX, slot, x0, top + off, h, ev, tous=TOUS_EVTS)   # bandeau du réseau (programme-commun)


used_slots = []
PRO = MOIS.get('prochainement', [])
if len(PRO) > 3:
    raise SystemExit('3 bandeaux « prochainement » maximum')
if (1 if MOIS.get('evenement_special') else 0) + len(PRO) > 3:
    src = SLOTS[2]
    nim, ntf, nln, ngrp = (d.duplicate(i) for i in src[:4])
    ndst = [c for c in ngrp if c.tag == 'TextFrame'][0].get('ParentStory')
    SLOTS.append((nim.get('Self'), ntf.get('Self'), nln.get('Self'), ngrp.get('Self'), ndst, src[5]))
# 2a. événement spécial dans son volet (ex. soirée anniversaire)
SPE = MOIS.get('evenement_special')
fill_rects = []
if SPE:
    vi = SPE['volet'] - 1
    x0, x1, sp, off = COLS[vi]
    we = WEEKENDS[vi]
    top, bottom = we.get('_ev') or (we['_fiches_bottom'] + 1.5, we['_gtop'] - 2.5)
    if bottom - top < 30:
        WARN.append(f"Peu de place pour l'événement spécial dans le volet {vi+1} ({bottom-top:.0f} mm)")
    sh = d.duplicate('ud0e9')
    if sp != SP1:
        to_spread(sh, sp)
    d.set_bounds(sh, x0, top + off, x1, top + 7.5 + off)
    sh.set('FillColor', 'Color/Black')
    d.set_text(story_of(sh), {0: SPE['bandeau'].lower()})
    big_heading(sh, 11.5)
    place_slot(SLOTS[0], x0, top + 8.0, bottom - top - 8.0, SPE, sp)
    used_slots.append(0)
    fr = d.duplicate('ubdf0')
    for ch in list(fr):
        if ch.tag in ('Image', 'PDF', 'EPS'):
            fr.remove(ch)
    fr.set('ContentType', 'Unassigned'); fr.set('FillColor', 'Swatch/None')
    fr.set('StrokeColor', BLUE); fr.set('StrokeWeight', '2.5'); fr.set('StrokeAlignment', 'InsideAlignment')
    to_spread(fr, sp)
    d.set_bounds(fr, x0, top + off, x1, bottom + off)
    for c in d.story(story_of('ud126')).getroot().iter('CharacterStyleRange'):
        if any((x.text or '') == SPE['titre'] for x in c.iter('Content')):
            c.set('PointSize', '11.5')
            p = c.find('Properties')
            if p is not None and p.find('Leading') is not None:
                p.find('Leading').text = '12'
    we['_filled'] = True

# 2b. images de remplissage des volets
for vi, we in enumerate(WEEKENDS):
    if we.get('_filled') or not we.get('image_remplissage'):
        continue
    x0, x1, sp, off = COLS[vi]
    top = we['_fiches_bottom'] + 1.5
    bottom = we['_gtop'] - 2.5
    if bottom - top < 15:
        continue
    r = d.duplicate('ubdf0')
    to_spread(r, sp)
    d.set_bounds(r, x0, top + off, x1, bottom + off)
    r.set('FillColor', 'Swatch/None')
    ir = we['image_remplissage']
    img(r.get('Self'), ir['image'], 'fill', tuple(ir.get('cadrage', (0.5, 0.5))))
d.delete('ubdf0')

# 2c. prochainement (extérieur milieu)
to_spread('ud24f', SP2); to_spread('ud109', SP2)
free = [i for i in [1, 2, 0] + list(range(3, len(SLOTS))) if i not in used_slots]
PRO_TOP, PRO_BOTTOM, PRO_GAP = 15.0, float(os.environ.get('PRO_BOTTOM', 113.5)), 2.0
REM_SCALE = float(CIN.get('remerciements_echelle', 0.72))   # logos remerciements (0,72 = réduits, retour client Commynes)      # zone des bandeaux (mm, page 2)
n_pro = max(1, len(PRO))
slot_h = min(48.5, (PRO_BOTTOM - PRO_TOP - (n_pro - 1) * PRO_GAP) / n_pro)
if PRO:
    d.set_bounds(E('ud109'), 99.6, 7.0 + P2, 189.6, 13.0 + P2)
    d.set_text('ud10c', {0: CIN.get('titre_prochainement', 'prochainement').lower()})
    box = E('ud24f')
    pp, pts = d.anchors(box)
    mi = inv(d.chain(box))
    yb = PRO_TOP + len(PRO) * slot_h + (len(PRO) - 1) * PRO_GAP + 0.6
    corners = [(99.8, yb), (99.8, 5.4), (194.0, 5.4), (194.0, yb), (99.8, yb)]
    for node, (x, y) in zip(pp, corners):
        nx, ny = ap(mi, x * PT - OX, (y + P2) * PT - OY)
        for k in ('Anchor', 'LeftDirection', 'RightDirection'):
            node.set(k, f'{nx} {ny}')
    for k, ev in enumerate(PRO):
        si = free.pop(0)
        place_slot(SLOTS[si], 102.0, PRO_TOP + k * (slot_h + PRO_GAP), slot_h, ev, SP2)
        used_slots.append(si)
    print(f'Bandeaux « prochainement » : {len(PRO)} × {slot_h:.1f} mm de haut '
          f'(préparer les images avec prep_images.py bandeau --haut-mm {slot_h:.1f})')
else:
    d.delete('ud24f'); d.delete('ud109')
for si in range(len(SLOTS)):
    if si not in used_slots:
        for i in SLOTS[si][:4]:
            d.delete(i)

# =====================================================================
# 3. extérieur milieu : remerciements, tarifs, abonnements, bandeau
# =====================================================================
REM_TOP = PRO_BOTTOM + P2 + 2.0          # cadre remerciements, juste sous les bandeaux
for _k, _logo in enumerate(CIN.get('partenaires_en_plus', [])):     # logos ajoutés (ex. ville de Cerizay)
    _src = E('uc342')
    _r = d.duplicate('uc342')
    _sx0, _sy0, _sx1, _sy1 = d.bbox(_src)
    _w, _h = Image.open(find_img(_logo)).size
    _hh = (_sy1 - _sy0) + 1.6
    _x = _sx1 + 1.6 + _k * 8.0
    d.set_bounds(_r, _x, _sy0 - 0.8, _x + _hh * _w / _h, _sy1 + 0.8)
    img(_r.get('Self'), _logo, 'fit', (0.5, 0.5))
# logos du gabarit à remplacer (fiche cinéma « remplacer_logos » : {lien d'origine: nouveau fichier}) — retour client
# 07/10/2026 : « Poitou-Charentes Cinéma » → logo Région Nouvelle-Aquitaine. Même hauteur, largeur selon le logo.
for _old, _new in CIN.get('remplacer_logos', {}).items():
    _q = urllib.parse.quote(_old)
    for _r in [r_ for t_ in d.spreads.values()
               for r_ in t_.xpath(f'//Rectangle[.//Link[contains(@LinkResourceURI,"{_q}")]]')]:
        _x0, _y0, _x1, _y1 = d.bbox(_r)
        _w, _h = Image.open(find_img(_new)).size
        for ch in list(_r):
            if ch.tag in ('Image', 'PDF', 'EPS'):
                _r.remove(ch)
        d.set_bounds(_r, _x0, _y0, _x0 + (_y1 - _y0) * _w / _h, _y1)
        img(_r.get('Self'), _new, 'fit', (0.5, 0.5))
_g = E('uc331')
_g.set('ItemTransform', fmt(mul([REM_SCALE, 0, 0, REM_SCALE, 0, 0], M(_g.get('ItemTransform')))))
_rx0, _ry0, _rx1, _ry1 = d.bbox(E('uc346'))
d.set_bounds(E('uc346'), _rx0, _ry0 - 0.6, _rx1 + 6.0, _ry1 + 0.6)
gx0, gy0, gx1, gy1 = d.bbox(E('uc331'))
d.move(E('uc331'), (99.6 + 194.2) / 2 - (gx0 + gx1) / 2, (REM_TOP + 1.0) - gy0)
if CIN.get('remerciements_pleine_largeur'):     # logos répartis sur toute la largeur du cadre (retour client 06/10/2026)
    _logos = sorted([c for c in _g if c.tag == 'Rectangle'], key=lambda c: d.bbox(c)[0])
    _bb = [d.bbox(c) for c in _logos]
    _L, _R = 99.6 + 3.0, 194.2 - 3.0
    _gap = ((_R - _L) - sum(b[2] - b[0] for b in _bb)) / max(1, len(_logos) - 1)
    _x = _L
    for c, b in zip(_logos, _bb):
        d.move(c, _x - b[0], 0)
        _x += (b[2] - b[0]) + _gap
    _tx0, _ty0, _tx1, _ty1 = d.bbox(E('uc346'))           # « Remerciements » calé à gauche
    d.move(E('uc346'), _L - _tx0, 0)
gx0, gy0, gx1, gy1 = d.bbox(E('uc331'))
gh = gy1 - gy0
d.set_bounds(E('uce0f'), 99.6, REM_TOP, 194.2, REM_TOP + gh + 2.0)
TAR_TOP = REM_TOP + gh + 2.0 + 1.5       # cadre tarifs
BAN_TOP = 473.0                          # bandeau bas (rapproché du pied de page)
d.set_bounds(E('ucdb9'), 99.7, TAR_TOP, 194.3, BAN_TOP + 3.3)
d.set_bounds(E('uc580'), 101.2, TAR_TOP + 2.3, 145.2, BAN_TOP - 0.5)
d.set_bounds(E('uc599'), 148.6, TAR_TOP + 2.3, 192.6, BAN_TOP - 0.5)
_lx0, _ly0, _lx1, _ly1 = d.bbox(E('ucdba'))
shift_points_y(d, E('ucdba'), _ly0, TAR_TOP + 2.8)
shift_points_y(d, E('ucdba'), _ly1, BAN_TOP - 2.0)
d.set_bounds(E('ucdbc'), 99.7, BAN_TOP, 194.3, BAN_TOP + 11.0)
_cx0, _cy0, _cx1, _cy1 = d.bbox(E('uc467'))
d.move(E('uc467'), 0, 485.6 - _cy0)

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
            cs = p.findall('CharacterStyleRange')
            _set(cs[0], it['titre'], br=False)
            story.append(p)
            continue
        elif 'prix' in it:
            p = _empty(TPL_LINE)
            b, lab, tab, price, eur = [copy.deepcopy(c) for c in TPL_LINE_CSR]
            _set(b, '• ', False); _set(lab, it['ligne'] + (' ' if it.get('detail') else ''), False)
            p.append(b); p.append(lab)
            if it.get('detail'):
                p.append(_set(copy.deepcopy(TPL_DETAIL_CSR), it['detail'], False))
            p.append(_set(tab, '\t', False)); p.append(_set(price, it['prix'], False))
            p.append(_set(eur, '€', not last))
            story.append(p)
            continue
        elif 'sous' in it:
            p = _empty(TPL_SUB)
            p.append(_set(copy.deepcopy(TPL_SUB_CSR), '- ' + it['sous'], not last))
            story.append(p)
            continue
        elif 'texte' in it:
            p = _empty(TPL_TXT)
            p.append(_set(copy.deepcopy(TPL_TXT_CSR), it['texte'], not last))
            story.append(p)
            continue
        elif 'note' in it:
            p = copy.deepcopy(TPL_NOTE)
            _set(p.findall('CharacterStyleRange')[0], it['note'], not last)
            story.append(p)
            continue
        elif 'fort' in it:
            p = _empty(TPL_CENTRE)
            a, sp_, strong, b2 = [copy.deepcopy(c) for c in TPL_CENTRE_CSR[:4]]
            p.append(_set(a, '✶', False)); p.append(_set(sp_, ' ', False))
            p.append(_set(strong, it['fort'] + ' ', False)); p.append(_set(b2, '✶', not last))
            story.append(p)
            continue
        elif 'centre' in it:
            p = copy.deepcopy(TPL_CENTRE2)
            _set(p.findall('CharacterStyleRange')[0], it['centre'], not last)
            story.append(p)
            continue
        else:
            raise SystemExit(f'élément tarif inconnu : {it}')
        if not last:
            etree.SubElement(p.findall('CharacterStyleRange')[-1], 'Br')
        story.append(p)


build_bloc(T583, CIN['tarifs'])
build_bloc(T59D, CIN['abonnements'])
for _st in (T583, T59D):                      # suppression des espaces blancs (retour client)
    for _k, _p in enumerate(_st.findall('ParagraphStyleRange')):
        _p.set('SpaceBefore', '0')
        _p.set('SpaceAfter', '2.83' if _k == 0 else '0')
d.set_text('ucdbe', {0: CIN['bandeau_bas'][0], 1: CIN['bandeau_bas'][1]})
_ban = E('ucdbc')                                   # bandeau bas : texte centré verticalement, agrandi (retour 06/10/2026)
_tfp = _ban.find('TextFramePreference')
if _tfp is not None:
    _tfp.set('VerticalJustification', 'CenterAlign')
    _top = 3.3 * PT                                  # le haut du bandeau passe sous le cadre des tarifs : on centre sur la partie visible
    _tfp.set('InsetSpacing', f'{_top} 0 0 0')
    for _x in list(_tfp.iter('InsetSpacing')):          # la valeur « Properties » (4 mm partout) l'emporterait
        _x.getparent().remove(_x)
    _pr = _tfp.find('Properties')
    if _pr is None:
        _pr = etree.SubElement(_tfp, 'Properties')
    _is = etree.SubElement(_pr, 'InsetSpacing'); _is.set('type', 'list')
    for _v in (_top, 0, 0, 0):                          # haut, gauche, bas, droite
        _li = etree.SubElement(_is, 'ListItem'); _li.set('type', 'unit'); _li.text = str(_v)
for _p in d.story('ucdbe').getroot().iter('ParagraphStyleRange'):
    _p.set('SpaceBefore', '0'); _p.set('SpaceAfter', '0'); _p.set('Justification', 'CenterAlign'); _p.set('LeftIndent', '0')
_bpt = float(CIN.get('bandeau_bas_corps', 12.5))
for _c in d.story('ucdbe').getroot().iter('CharacterStyleRange'):
    _c.set('PointSize', str(_bpt)); _c.set('BaselineShift', '0')     # le gabarit décalait le texte de -4 pt
    _pr = _c.find('Properties')
    if _pr is None:
        _pr = etree.SubElement(_c, 'Properties')
    _ld = _pr.find('Leading')
    if _ld is None:
        _ld = etree.SubElement(_pr, 'Leading'); _ld.set('type', 'unit')
    _ld.text = str(round(_bpt * 1.15, 1))


# =====================================================================
# 4. couverture
# =====================================================================
d.set_bounds(E('ud3fb'), 205.0, 283.0 + 0.0, 268.0, 303.5)       # logo plus grand
img('ud3fb', CIN['logo'], 'fit', (0.0, 0.5))
d.move(E('ud3f3'), 0, -12.0)                                      # fauteuil remonté
if CIN.get('fauteuil'):
    img('ud3f3', CIN['fauteuil'], 'fill', (0.5, 0.5))
d.set_bounds(E('ud404'), 205.4, 305.0, 266.0, 307.6)               # slogan
d.set_bounds(E('ud3da'), 197.0, 309.3, 302.9, 319.8)               # bandeau des dates plus haut
_tfp = E('ud3da').find('TextFramePreference')
if _tfp is not None:
    _tfp.set('VerticalJustification', 'CenterAlign')
per = MOIS['periode']
d.set_text('ud3dd', {0: '  PROGRAMME du ', 1: per['du'] + ' ', 2: 'au ', 3: per['au_num'], 4: per.get('au_exposant', ''),
                     5: ' ' + per['au_mois'], 6: ' ' + str(per['annee'])})
for cr in d.story('ud3dd').getroot().iter('CharacterStyleRange'):
    cr.set('PointSize', '12'); cr.set('Tracking', '0')
for pr in d.story('ud3dd').getroot().iter('ParagraphStyleRange'):
    pr.set('LeftIndent', str(6.0 * PT))
d.set_text('ud3dd', {0: 'PROGRAMME du '})
d.set_text('ud407', {0: CIN.get('slogan', 'Cinéma indépendant, coopératif et proche de vous')})
d.set_text('ud420', {0: CIN.get('mention_gestion', '')})
c = CIN['contact']
d.set_text('uc470', {0: c[0], 2: c[1], 4: c[2]})
_ax0, _ay0, _ax1, _ay1 = d.bbox(E('uc919'))          # filet vertical = hauteur du bloc adresse
_sx0, _sy0, _sx1, _sy1 = d.bbox(E('ud3d3'))
_rx0, _, _rx1, _ = d.bbox(E('uc697'))
d.move(E('ud3d3'), ((_ax1 + _rx1) / 2) - (_sx0 + _sx1) / 2, ((_ay0 + _ay1) / 2) - (_sy0 + _sy1) / 2)

# fonds perdus 3 mm du volet couverture (bord droit = 297 + 3)
BLEED_R = 300.6
def to_bleed_right(rid):
    r = E(rid)
    x0, y0, x1, y1 = d.bbox(r)
    if x1 < BLEED_R:
        d.set_bounds(r, x0, y0, BLEED_R, y1)
    im = r.find('Image')
    if im is None:
        return
    m = mul(M(im.get('ItemTransform')), d.chain(r))
    gb = im.find('Properties/GraphicBounds')
    pts = [ap(m, float(gb.get(a)), float(gb.get(b))) for a, b in (('Left', 'Top'), ('Right', 'Bottom'))]
    xs = sorted((p[0] + OX) / PT for p in pts); ys = sorted((p[1] + OY) / PT for p in pts)
    if xs[1] >= BLEED_R:
        return
    s = (BLEED_R + 0.4 - xs[0]) / (xs[1] - xs[0])          # agrandit l'image depuis son bord gauche/haut
    ai = ap(inv(d.chain(r)), xs[0] * PT - OX, ys[0] * PT - OY)
    t = [s, 0, 0, s, ai[0] * (1 - s), ai[1] * (1 - s)]
    im.set('ItemTransform', fmt(mul(M(im.get('ItemTransform')), t)))
for _rid in ('uc86a', 'uc914', 'uc91b', 'ud3f3'):
    to_bleed_right(_rid)

COVER_RECTS = [('uc37d', 0.90, 324.0, None), ('uc380', 0.90, 332.5, None),
               ('uc89e', 0.80, 389.0, 213.0), ('uc8b5', 0.80, 394.5, 236.0),
               ('uc8c1', 0.80, 399.5, 259.0), ('uc8cd', 0.80, 403.5, 281.0)]
aff = MOIS['couverture']['affiches']
for k, (rid, s, top, xc) in enumerate(COVER_RECTS):
    if k >= len(aff):
        d.delete(rid)
        continue
    _cad = next((tuple(f_['cadrage_affiche']) for f_ in MOIS['films'].values()
                 if f_.get('affiche') == aff[k] and f_.get('cadrage_affiche')), (0.5, 0.0))
    img(rid, aff[k], 'fill', _cad, affiche=True)
    r = E(rid)
    x0, y0, x1, y1 = d.bbox(r)
    cx = (x0 + x1) / 2 if xc is None else xc
    r.set('ItemTransform', fmt(mul([s, 0, 0, s, 0, 0], M(r.get('ItemTransform')))))
    nx0, ny0, nx1, ny1 = d.bbox(r)
    d.move(r, cx - (nx0 + nx1) / 2, top - ny0)

# réseaux sociaux de la couverture : le fichier commun montre Facebook, Instagram, X, TikTok (dans cet ordre).
# « reseaux_visibles » = part gauche du fichier à garder (7e Art : Facebook seul → [0, 0.13]), recentrée.
_rv = CIN.get('reseaux_visibles')
if _rv:
    for _r in [r_ for t_ in d.spreads.values()
               for r_ in t_.xpath('//Rectangle[.//Link[contains(@LinkResourceURI,"SEAUX.ai")]]')]:
        _x0, _y0, _x1, _y1 = d.bbox(_r); _w = _x1 - _x0; _cx = (_x0 + _x1) / 2
        d.set_bounds(_r, _x0 + _w * _rv[0], _y0, _x0 + _w * _rv[1], _y1)
        _n0, _, _n1, _ = d.bbox(_r)
        d.move(_r, _cx - (_n0 + _n1) / 2, 0)

CO = MOIS.get('couverture', {}).get('encart')
if CO:
    cv = d.duplicate('ud0e9')
    to_spread(cv, SP2)
    d.set_bounds(cv, 204.0, 437.5, 290.0, 459.5)
    cv.set('ItemLayer', 'u437')
    cv.set('StrokeColor', 'Color/Paper'); cv.set('StrokeWeight', '1')
    tfp = cv.find('TextFramePreference')
    if tfp is not None:
        tfp.set('VerticalJustification', 'CenterAlign')
    psr = d.story(cv.get('ParentStory')).getroot().find('Story/ParagraphStyleRange')
    psr.set('LeftIndent', '0'); psr.set('Justification', 'CenterAlign')
    tpl = psr.find('CharacterStyleRange'); psr.remove(tpl)

    def run(text, font, style, size, lead, track='0', caps='Normal', br=True):
        r = copy.deepcopy(tpl)
        for ch in list(r):
            if ch.tag in ('Content', 'Br'):
                r.remove(ch)
        r.set('FontStyle', style); r.set('PointSize', str(size)); r.set('Tracking', track)
        r.set('Capitalization', caps); r.set('HorizontalScale', '100')
        p = r.find('Properties'); p.find('AppliedFont').text = font
        ld = p.find('Leading')
        if ld is None:
            ld = etree.SubElement(p, 'Leading'); ld.set('type', 'unit')
        ld.text = str(lead)
        etree.SubElement(r, 'Content').text = text
        if br:
            etree.SubElement(r, 'Br')
        psr.append(r)
    run(CO['surtitre'], 'Futura LT', 'Book', 8.5, 11, '80', 'AllCaps')
    run(CO['titre'], 'Futura', 'Bold', 17, 19, '0', 'AllCaps')
    run(CO['ligne'], 'Futura LT Medium', 'Regular', 8.5, 10, '0', 'Normal', br=False)

for vi in range(len(WEEKENDS), 2):
    d.delete(heads_src[vi])
for i in FICHE_SRC:
    d.delete(i)

# =====================================================================
# 5. couleur du cinéma + polices manquantes sur le Mac
# =====================================================================
d.save()
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
# déclinaisons de la couleur du cinéma (repris de la Belle épine) : les gris neutres du gabarit listés dans la fiche
# cinéma « declinaisons » (ex. bandeau durée/pays des fiches « C=32 M=25 J=27 N=7 ») prennent une teinte claire
for _old, _hx in CIN.get('declinaisons', {}).items():
    m = re.search(r'(<Color Self="Color/' + re.escape(_old) + r'"[^>]*/>)', gx)
    if not m:
        WARN.append(f'déclinaison : nuance « {_old} » absente du gabarit'); continue
    _hx = _hx.lstrip('#'); _rgb = ' '.join(str(int(_hx[i:i + 2], 16)) for i in (0, 2, 4))
    el = m.group(1)
    el2 = re.sub(r'Space="[^"]*"', 'Space="RGB"', el)
    el2 = re.sub(r'ColorValue="[^"]*"', f'ColorValue="{_rgb}"', el2)
    el2 = re.sub(r' Name="[^"]*"', f' Name="{CIN["nom_couleur"]} - {_old.split(" ")[0]} #{_hx.upper()}"', el2)
    gx = gx.replace(el, el2)
_base = re.search(r'(<Color Self="Color/C=0 M=100 J=100 N=0"[^>]*/>)', gx).group(1)
for _nm, _hx in CIN.get('couleurs_grille', {'violet': '#6A1B9A', 'bleu': '#1565C0'}).items():
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
# 6. paquet de sortie
# =====================================================================
name = MOIS['nom_fichier']
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
if len(WEEKENDS) < 4:
    WARN.append(f"Seulement {len(WEEKENDS)} week-end(s) : le(s) volet(s) suivant(s) restent vides, à meubler à la main")
if len(PRO) < 2:
    WARN.append("Moins de 2 bandeaux « prochainement » : espace libre sous le bloc (extérieur milieu)")
print('OK', pk)
for w in WARN:
    print('ATTENTION :', w)
