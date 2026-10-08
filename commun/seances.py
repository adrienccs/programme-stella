"""
Code UNIQUE des séances du réseau (décision d'Adrien, 08/10/2026) — module commun à tous les cinémas.

Styles d'une séance dans mois.json : {"h": "20h30", "s": "<lettres>"} ; lettres combinables :
    r rouge = VOSTFR · b bleu = Dolby Atmos · v violet = événement · o orange = prix spécial (4,50 €, Ciné à 1 €…)
    g vert = court-métrage · s souligné = goûter
Drapeaux d'un film : "court": true (toutes ses séances en vert), "coeur": true (♥), "derniere": true (⌛),
"pictos": ["ad", "bim", "12" | "16" | "18"], "vostfr": true (toutes ses séances en rouge).

La légende ne montre QUE les codes réellement présents (dans la semaine / le programme passé en argument).
"""
import copy, json, os

ICI = os.path.dirname(os.path.abspath(__file__))
CODES = json.load(open(os.path.join(ICI, 'codes.json'), encoding='utf-8'))
STYLES = CODES['styles']
PICTOS = CODES['pictos']
COULEURS_STYLE = [k for k, v in STYLES.items() if v.get('couleur')]          # r b v o g
PRIORITE = CODES['priorite_couleurs']
COEUR = 'Color/Grille rouge'                   # couleur du ♥ coup de cœur (grilles et légende)


def couleurs_grille():
    """nuances à créer dans le document : {"rouge": "#D41818", ...} → swatches « Color/Grille rouge »…"""
    return dict(CODES['couleurs'])


def swatch(lettre):
    return 'Color/Grille ' + STYLES[lettre]['couleur']


def lettres(st, court=False, vostfr=False):
    """style normalisé d'une séance (drapeaux du film inclus)"""
    st = st or ''
    out = ''.join(c for c in st if c in STYLES)
    if vostfr and 'r' not in out:
        out += 'r'
    if court and 'g' not in out:
        out += 'g'
    return out


def styler(x, st, court=False, vostfr=False, souligne=(1.5, 0.8)):
    """applique le code d'une séance à un CharacterStyleRange (horaire de grille).
    Plusieurs couleurs : priorité de codes.json « priorite_couleurs » (VOSTFR > Atmos > événement > court > prix spécial)."""
    st = lettres(st, court, vostfr)
    for c in reversed(CODES['priorite_couleurs']):
        if c in st:
            x.set('FillColor', swatch(c))
    if 's' in st:
        x.set('Underline', 'true'); x.set('UnderlineOffset', str(souligne[0])); x.set('UnderlineWeight', str(souligne[1]))
    return st


def _seance(t):
    return ('' if isinstance(t, str) else (t.get('s') or ''))


def codes_utilises(*objets, films=None):
    """ensemble des codes présents dans des morceaux de mois.json (semaines, lignes de grille, films…) :
    lettres de style + 'coeur', 'sablier', 'ad', 'bim', 'age'. `films` = dictionnaire MOIS['films'] pour les drapeaux."""
    u = set()

    def film(f):
        if not isinstance(f, dict):
            return
        if f.get('court'):
            u.add('g')
        if f.get('vostfr'):
            u.add('r')
        if f.get('coeur'):
            u.add('coeur')
        if f.get('derniere'):
            u.add('sablier')
        if f.get('malentendants'):
            u.add('bim')
        for p in f.get('pictos', []) or []:
            p = CODES['anciens_pictos'].get(str(p), str(p))
            u.add(PICTOS.get(p, {}).get('style') or PICTOS.get(p, {}).get('groupe', p))

    def walk(o):
        if isinstance(o, dict):
            if 'h' in o and isinstance(o.get('h'), str):
                u.update(c for c in _seance(o) if c in STYLES)
            film(o)
            if films is not None:
                for k in ('film', 'cle', 'id'):
                    if isinstance(o.get(k), str) and o[k] in films:
                        film(films[o[k]])
            for v in o.values():
                walk(v)
        elif isinstance(o, (list, tuple)):
            if films is not None and o and isinstance(o[0], str) and o[0] in films:
                film(films[o[0]])
            for v in o:
                walk(v)

    for ob in objets:
        walk(ob)
    return {c for c in u if c in STYLES or c in PICTOS or c == 'age'}


ORDRE_PICTOS = list(PICTOS)                    # de gauche à droite à côté du titre


def picto_fichier(p):
    return PICTOS[p]['fichier']


def picto_hauteur(p):
    return PICTOS[p].get('hauteur', CODES['picto_hauteur'])


def pictos_titre(film=None, opts=None, seances_film=None):
    """pictos à poser à droite du titre d'une ligne de grille : pictos déclarés (film puis ligne), ⌛ si dernière
    semaine, ♥ si coup de cœur, + automatiques (Atmos si une séance est bleue, étoile si une séance est violette)"""
    film, opts = film or {}, opts or {}
    out = []
    for src in (film, opts):
        for p in src.get('pictos', []) or []:
            out.append(CODES['anciens_pictos'].get(str(p), str(p)))
        if src.get('malentendants'):
            out.append('bim')
        if src.get('derniere'):
            out.append('sablier')
        if src.get('coeur'):
            out.append('coeur')
    lettres_ = set()
    for lst in (seances_film or {}).values():
        for t in lst:
            lettres_ |= set(_seance(t))
    for p, v in PICTOS.items():
        if v.get('auto') and v['auto'] in lettres_:
            out.append(p)
    return [p for p in ORDRE_PICTOS if p in out]


def items_legende(codes):
    """items de légende dans l'ordre du réseau, pour les codes présents seulement.
    Chaque item : {"code", "runs": [[texte, style]]} — style : lettre de couleur / 's' (souligné) / 'z' (♥) / 'p:<picto>'"""
    out = []
    for c in CODES['ordre_legende']:
        if c not in codes:
            continue
        if c in STYLES:
            s = STYLES[c]
            it = {'code': c, 'runs': [[s['nom'], c], [' : ' + s['texte'], '']], 'court': s['legende']}
            pl = [p for p, v in PICTOS.items() if v.get('style') == c]
            if pl:
                it['picto'] = pl[0]                  # légende : logo + couleur (ex. Atmos + « Bleu »)
            out.append(it)
        elif c == 'coeur':
            out.append({'code': c, 'picto': 'coeur', 'runs': [['♥', 'z'], [' : ' + PICTOS['coeur']['texte'], '']], 'court': PICTOS['coeur']['legende']})
        else:
            p = '12' if c == 'age' else c
            out.append({'code': c, 'picto': p, 'runs': [['', 'p:' + p], [PICTOS[p]['texte'], '']], 'court': PICTOS[p]['legende']})
    return out


def lignes_legende(codes, car_par_ligne=95, sep='   ·   '):
    """légende en lignes de runs [[texte, style], ...] (format « legende_grille » des moteurs), coupée au nombre
    de caractères donné ; seuls les codes présents. Les pictos image (sablier, AD…) sont rendus par leur texte."""
    lignes, cur, n = [], [], 0
    for it in items_legende(codes):
        runs = [list(r) for r in it['runs'] if not r[1].startswith('p:')]
        if it.get('picto') and it['picto'] != 'coeur':
            runs = [['', 'p:' + it['picto']]] + runs
        long_ = sum(len(t) for t, _ in runs) + 3
        if cur and n + len(sep) + long_ > car_par_ligne:
            lignes.append(cur); cur, n = [], 0
        if cur:
            cur.append([sep, '']); n += len(sep)
        cur += runs; n += long_
    if cur:
        lignes.append(cur)
    return lignes


def style_run(c, sty, swatch_cinema, set_font=None):
    """applique le style d'un run de légende à un CharacterStyleRange (gras pour tout run stylé)"""
    if not sty:
        return
    for l in COULEURS_STYLE:
        if l in sty:
            c.set('FillColor', swatch(l))
    if 's' in sty:
        c.set('Underline', 'true'); c.set('UnderlineOffset', '1.2'); c.set('UnderlineWeight', '0.5')
    if 'z' in sty:                         # ♥ coup de cœur : toujours rouge, comme dans les grilles
        c.set('FillColor', COEUR)
        if set_font:
            set_font(c, 'Zapf Dingbats', 'Regular')
    c.set('FontStyle', '77 Bold Condensed')


def convertir_style(cinema, st):
    """ancien style (avant le 08/10/2026) → code du réseau"""
    m = CODES['anciens_codes'].get(cinema, {})
    out = ''
    for ch in st or '':
        n = m.get(ch, ch)
        if n and n not in out:
            out += n
    return out


def appliquer(cin):
    """fiche cinéma → couleurs de grille et légende du réseau (les anciennes clés locales sont ignorées)"""
    cin = copy.deepcopy(cin)
    cin['couleurs_grille'] = couleurs_grille()
    cin.pop('legende_grille', None)
    cin.pop('legende_pictos', None)
    return cin


def ajouter_nuances(gx, base='Color/C=0 M=100 J=100 N=0'):
    """Graphic.xml (texte) → avec les nuances « Grille rouge/bleu/… » du réseau (copies RVB de la nuance `base`)"""
    import re
    if 'Self="Color/Grille rouge"' in gx:
        return gx
    b = re.search(r'(<Color Self="' + re.escape(base) + r'"[^>]*/>)', gx).group(1)
    for nm, hx in couleurs_grille().items():
        hx = hx.lstrip('#'); rgb = ' '.join(str(int(hx[i:i + 2], 16)) for i in (0, 2, 4))
        el = re.sub(r'Self="[^"]*"', f'Self="Color/Grille {nm}"', b)
        el = re.sub(r' Name="[^"]*"', f' Name="Grille {nm}"', el)
        el = re.sub(r'Space="[^"]*"', 'Space="RGB"', el)
        el = re.sub(r'ColorValue="[^"]*"', f'ColorValue="{rgb}"', el)
        gx = gx.replace(b, b + '\n\t' + el)
    return gx
