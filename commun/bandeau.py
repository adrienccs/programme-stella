"""
Bandeau d'événement UNIQUE du réseau (décision d'Adrien, 08/10/2026).

Photo plein cadre (assombrie à gauche) · surtitre en capitales espacées + filet · titre en gras · ligne d'info ·
ligne en gras (tarif) · à droite la date (jour, gros numéro, mois) et l'heure.

Règles :
- les TAILLES DE TEXTE sont fixes (référence : Fauteuil Rouge validé le 07/10/2026, bandeau de 46,3 mm de large 89,7 mm) ;
  elles ne dépendent PAS de la hauteur du bandeau ;
- seule la HAUTEUR varie (nombre d'événements du programme) : le bloc texte et la date sont centrés verticalement,
  la photo est recadrée (prep_images.py bandeau … --haut-mm <h>) ;
- le surtitre tient toujours sur une ligne (même taille pour tous les surtitres du programme) ;
- tous les titres d'un même programme ont la même taille (la plus grande qui fait tenir le plus long sur une ligne,
  sans dépasser la taille de référence) — utiliser « titre_court » si un titre est trop long ;
- hauteur minimale H_MIN (30 mm pour 89,7 mm de large) : en dessous, ATTENTION (retirer un événement ou
  raccourcir) — les textes ne sont JAMAIS réduits en douce.
- Sur l'affiche A3, le bandeau est le même, à l'échelle de sa largeur (largeur / 89,7 mm).

Utilisation dans un moteur (le moteur fournit son contexte) :
    from commun import bandeau
    CTX = bandeau.Contexte(d=d, E=E, img=img, story_of=story_of, etree=etree, alertes=WARN)
    bandeau.poser(CTX, slot, x0, y_haut, h, ev, tous=EVTS, largeur=89.7)
"""
import math

LARGEUR_REF = 89.7        # mm : largeur d'un volet
KH = 46.3 / 31.5          # facteur des textes (Fauteuil Rouge validé : bandeau de 46,3 mm, gabarit dessiné pour 31,5 mm)
K_TITRE = 1.3             # titre : jusqu'à KH × 1,3
K_LIGNES = 0.9            # surtitre et lignes : KH × 0,9
ZOOM_DATE = 1.35          # bloc date (jour / numéro / mois / heure)
LARG_DATE = 31.0          # mm, colonne de la date
H_MIN = 30.0              # mm, hauteur minimale pour LARGEUR_REF
_BASE = {'CharacterStyle/nom film': '8', 'CharacterStyle/réalisé par': '7.5'}   # tailles des styles du gabarit


class Contexte:
    def __init__(self, d, E, img, story_of, etree, alertes=None, sans_heure=None):
        self.d, self.E, self.img, self.story_of, self.etree = d, E, img, story_of, etree
        self.alertes = alertes if alertes is not None else []
        self.sans_heure = sans_heure          # fonction(story date) appelée quand la date n'a pas d'heure


def _titre(ev):
    return ev.get('titre_court', ev['titre'])


def _date(ctx, grp, dst, top, h, k):
    d, E = ctx.d, ctx.E
    g = E(grp)
    tf = [c for c in g if c.tag == 'TextFrame'][0]
    for ln in [c for c in g if c.tag == 'Polygon']:
        g.remove(ln)
    x0, y0, x1, y1 = d.bbox(tf)
    w = LARG_DATE * k
    d.set_bounds(tf, x1 - w, top + 1.0, x1, top + h - 1.0)
    tfp = tf.find('TextFramePreference')
    if tfp is not None:
        tfp.set('VerticalJustification', 'CenterAlign')
    z = ZOOM_DATE * k
    for c in d.story(dst).getroot().iter('CharacterStyleRange'):
        ps = float(c.get('PointSize', '12'))
        c.set('PointSize', str(round(ps * z, 1)))
        p = c.find('Properties')
        if p is not None and p.find('Leading') is not None:
            p.find('Leading').text = str(round(float(p.find('Leading').text) * z * 0.96, 1))


def _textes(ctx, tf, ln, grp, ev, top, h, k, tous):
    d, E, etree = ctx.d, ctx.E, ctx.etree
    kh = KH * k
    tit = _titre(ev)
    gx0, _, _, _ = d.bbox([c for c in E(grp) if c.tag == 'TextFrame'][0])
    tx0, ty0, tx1, ty1 = d.bbox(E(tf))
    wmm = (gx0 - 1.0) - tx0 - 1.0
    std = [e for e in (tous or []) if not (e.get('visuel') or e.get('visuel_programme'))]
    lmax = max([len(_titre(e)) for e in std] + [len(tit)])
    lsur = max([len(e.get('surtitre', '')) for e in std] + [len(ev.get('surtitre', ''))])
    runs = []
    for c in d.story(ctx.story_of(tf)).getroot().iter('CharacterStyleRange'):
        ps = c.get('PointSize') or _BASE.get(c.get('AppliedCharacterStyle'))
        txt = ''.join(x.text or '' for x in c.iter('Content')).strip()
        if not ps or not txt:
            continue
        role, k_ = 'sur', kh * K_LIGNES
        if txt == ev.get('surtitre', '').strip():     # surtitre : toujours sur UNE ligne, même taille pour tous
            k_ = min(kh * K_LIGNES, (wmm / (lsur * 0.76 * 25.4 / 72)) / float(ps))
        elif txt == tit.strip():
            role = 'tit'
            k_ = min(kh * K_TITRE, (wmm / (lmax * 0.74 * 25.4 / 72)) / float(ps))   # même taille pour tous les titres
        elif txt in (ev.get('ligne', '').strip(), ev.get('ligne_grasse', '').strip()):
            role = 'lig'
        pt = round(float(ps) * k_, 2)
        first_lig = role == 'lig' and not any(r[0] == 'lig' for r in runs)
        lead = pt * 1.12 + (5.0 * k if role == 'tit' else 0) + (3.0 * k if first_lig else 0)
        c.set('PointSize', str(pt))
        p = c.find('Properties')
        if p is None:
            p = etree.SubElement(c, 'Properties')
        ld = p.find('Leading')
        if ld is None:
            ld = etree.SubElement(p, 'Leading'); ld.set('type', 'unit')
        ld.text = str(round(lead, 2))
        n = max(1, math.ceil(len(txt) * pt * 0.5 * 25.4 / 72 / wmm)) if role == 'lig' else 1
        runs.append((role, pt, lead, n))
    for p in d.story(ctx.story_of(tf)).getroot().iter('ParagraphStyleRange'):
        p.set('SpaceBefore', '0'); p.set('SpaceAfter', '0')
    hb = sum(r[2] + (r[3] - 1) * r[1] * 1.12 for r in runs) * 25.4 / 72
    if hb > h - 2.0:
        ctx.alertes.append(f"Bandeau « {tit} » : texte trop haut ({hb:.0f} mm pour {h:.0f} mm) → raccourcir la ligne "
                           f"ou retirer un événement (les textes ne sont pas réduits)")
    ytop = top + max(1.5, (h - hb) / 2)
    d.set_bounds(E(tf), tx0, ytop, gx0 - 1.0, top + h - 1.0)
    x = E(tf).find('TextFramePreference')
    if x is not None:
        x.set('VerticalJustification', 'TopAlign')
        x.set('FirstBaselineOffset', 'LeadingOffset')
        x.set('InsetSpacing', '0 0 0 0')
        for _x in list(x.iter('InsetSpacing')):
            _x.getparent().remove(_x)
    sur_lead = runs[0][2] if runs else 10
    lx0, ly0, lx1, ly1 = d.bbox(E(ln))
    d.move(E(ln), 0, (ytop + sur_lead * 25.4 / 72 + 1.3 * k) - (ly0 + ly1) / 2)


def h_min(largeur=LARGEUR_REF):
    return H_MIN * largeur / LARGEUR_REF


def poser(ctx, slot, x0, top, h, ev, tous=None, largeur=None, image_cle='image'):
    """pose un bandeau. slot = (image, cadre texte, filet, groupe date, story date, index des champs date) ;
    top/x0 en mm DANS la planche (décalage de planche déjà ajouté) ; largeur None = celle du gabarit."""
    d, E = ctx.d, ctx.E
    im_, tf, ln, grp, dst, idx = slot
    ix0, iy0, ix1, iy1 = d.bbox(E(im_))
    w = largeur or (ix1 - ix0)
    k = w / LARGEUR_REF
    if h < h_min(w) - 0.05:
        ctx.alertes.append(f"Bandeau « {_titre(ev)} » : {h:.1f} mm de haut < minimum {h_min(w):.0f} mm → "
                           f"trop d'événements pour la place (en retirer un)")
    dx = x0 - ix0
    dy = top - iy0 + (h - (iy1 - iy0)) / 2
    for i in (tf, ln):
        d.move(E(i), dx, dy)
    d.move(E(grp), dx + (w - (ix1 - ix0)), dy)
    d.set_bounds(E(im_), x0, top, x0 + w, top + h)
    E(im_).set('FillColor', 'Swatch/None')
    ctx.img(im_, ev.get(image_cle) or ev['image'], 'fill', tuple(ev.get('cadrage', (0.5, 0.5))))
    d.set_text(ctx.story_of(tf), {0: ev['surtitre'], 2: _titre(ev), 4: ev.get('ligne', ''), 6: ev.get('ligne_grasse', '')})
    dt = ev['date']
    m = {idx[0]: dt['jour'] + ' ', idx[1]: dt['num'], idx[2]: dt['mois'], idx[3]: dt['heure']}
    if dst == 'ud1ab':
        m[3] = dt.get('exposant', '')
    d.set_text(dst, m)
    if not (dt.get('heure') or '').strip() and ctx.sans_heure:
        ctx.sans_heure(dst)
    _date(ctx, grp, dst, top, h, k)
    _textes(ctx, tf, ln, grp, ev, top, h, k, tous)
