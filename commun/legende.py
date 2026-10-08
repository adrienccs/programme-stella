"""
Légende et pictos du réseau, DESSINÉS (module commun à tous les moteurs du gabarit 3 volets / affiche A3).

- légende : bloc en 3 colonnes, libellés courts (modèle du Fauteuil Rouge validé le 07/10/2026) ; chaque entrée = logo du picto
  ou mot de couleur (« Rouge »), puis son texte ; SEULEMENT les codes présents (seances.codes_utilises) ;
- pictos de titre : à droite du titre dans la case titre de la grille (ordre et fichiers de codes.json).

Le moteur fournit un objet Outils (cadres du gabarit à dupliquer, placement dans la planche).
"""
import copy
from . import seances

PAS_LIGNE = 3.4          # mm entre deux lignes de légende


class Outils:
    """d : document ; place(el) : met l'élément dans la bonne planche ; img(id, fichier, mode, align) ;
    taille_image(fichier) -> (l, h) en pixels ; texte_id / image_id : cadres du gabarit à dupliquer."""

    def __init__(self, d, story_of, img, place, taille_image, etree, set_font=None,
                 texte_id='ubedb', image_id='ubdf0'):
        self.d, self.story_of, self.img, self.place = d, story_of, img, place
        self.taille_image, self.etree, self.set_font = taille_image, etree, set_font
        self.texte_id, self.image_id = texte_id, image_id

    def image(self, x0, y0, x1, y1, fichier, mode='fit', align=(0.5, 0.5)):
        r = self.d.duplicate(self.image_id)
        self.place(r)
        self.d.set_bounds(r, x0, y0, x1, y1)
        r.set('FillColor', 'Swatch/None'); r.set('StrokeWeight', '0')
        self.img(r.get('Self'), fichier, mode, align)
        return r

    def texte(self, x0, y0, x1, y1, runs, size=6.0, lead=6.6, just='LeftAlign'):
        """runs = [(texte, style)] ; style = lettre de code du réseau (couleur, gras) ou ''"""
        d, etree = self.d, self.etree
        lg = d.duplicate(self.texte_id)
        self.place(lg)
        lg.set('FillColor', 'Swatch/None')
        d.set_bounds(lg, x0, y0, x1, y1)
        st = d.story(self.story_of(lg)).getroot()
        psr = st.find('Story/ParagraphStyleRange')
        for extra in st.find('Story').findall('ParagraphStyleRange')[1:]:
            extra.getparent().remove(extra)
        psr.set('Justification', just); psr.set('LeftIndent', '0')
        tpl = copy.deepcopy(psr.find('CharacterStyleRange'))
        for c in psr.findall('CharacterStyleRange'):
            psr.remove(c)
        for x in list(tpl):
            if x.tag in ('Content', 'Br'):
                tpl.remove(x)
        tpl.set('PointSize', str(size)); tpl.set('FillColor', 'Color/Black'); tpl.set('FontStyle', '67 Medium Condensed')
        tpl.set('HorizontalScale', '100'); tpl.set('Tracking', '0')
        for k in ('Underline', 'Skew'):
            tpl.attrib.pop(k, None)
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
        ld.text = str(lead)
        for txt, sty in runs:
            c = copy.deepcopy(tpl)
            seances.style_run(c, sty, None, self.set_font)
            etree.SubElement(c, 'Content').text = txt
            psr.append(c)
        tfp = lg.find('TextFramePreference')
        if tfp is not None:
            tfp.set('VerticalJustification', 'CenterAlign')
            tfp.set('InsetSpacing', '0 0 0 0')
            for _x in list(tfp.iter('InsetSpacing')):
                _x.getparent().remove(_x)
        return lg


def items(codes):
    return seances.items_legende(codes)


def hauteur(codes, k=1.0, colonnes=3):
    """hauteur (mm) du bloc légende pour ces codes ; 0 si aucun code"""
    n = len(items(codes))
    return 0.0 if not n else (((n + colonnes - 1) // colonnes) * PAS_LIGNE + 1.0) * k


def poser(o, x0, x1, y, codes, k=1.0, colonnes=3):
    """dessine la légende sous une grille (haut du bloc à y, en mm de planche) ; renvoie sa hauteur"""
    its = items(codes)
    if not its:
        return 0.0
    cw = (x1 - x0) / colonnes
    for n, it in enumerate(its):
        col, row = n % colonnes, n // colonnes
        lx = x0 + 1.0 * k + col * cw
        ly = y + 0.6 * k + row * PAS_LIGNE * k
        mot, texte = it['runs'][0], it['court']           # libellé court du réseau
        if it.get('picto'):
            f = seances.picto_fichier(it['picto'])
            iw, ih = o.taille_image(f)
            ph = 2.5 * k
            pw = min(7.0 * k, ph * iw / ih)
            o.image(lx, ly, lx + pw, ly + ph, f, 'fit', (0.0, 0.5))
            tx = lx + pw + 1.4 * k                    # texte juste après le logo
            # logo + texte dans la couleur du code (ex. Atmos en bleu), sinon texte simple
            runs = [(texte, it['code'] if it['code'] in seances.STYLES else '')]
        else:
            ww = (len(mot[0]) * 1.12 + 0.6) * k       # mot de couleur (gras condensé 6,5 pt)
            o.texte(lx, ly - 0.3 * k, lx + ww, ly + 3.0 * k, [(mot[0], mot[1])], 6.5 * k, 7.5 * k)
            tx = lx + ww + 1.0 * k
            runs = [(texte, '')]
        o.texte(tx, ly - 0.3 * k, x0 + (col + 1) * cw - 0.5 * k, ly + 3.0 * k, runs, 6.0 * k, 6.6 * k)
    return hauteur(codes, k, colonnes)


def poser_pictos_titre(o, x_droite, y_bas, pictos, k=1.0):
    """pictos alignés à droite (x_droite) sur la ligne de base y_bas (mm de planche), ordre du réseau"""
    xr = x_droite
    for p in reversed(pictos):
        f = seances.picto_fichier(p)
        iw, ih = o.taille_image(f)
        ph = seances.picto_hauteur(p) * k
        pw = ph * iw / ih
        o.image(xr - pw, y_bas - ph, xr, y_bas, f, 'fit')
        xr -= pw + 0.7 * k
    return x_droite - xr
