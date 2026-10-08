"""Rebuild the screening grid (story ucf0d) as one table with one section per week-end."""
import copy
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from commun import seances as RES
from lxml import etree

# Stella : séances « r » (4,50 €) en ROUGE même si la couleur du cinéma est orange
# (nuance « Grille rouge » de couleurs_grille ; sinon couleur du cinéma comme au 7e Art)
ROUGE = None

# Stella (retour client 08/10/2026) : titres des grilles jamais coupés en « gros + petit ».
#   - titre entier sur UNE ligne, resserré au besoin (chasse ≥ TITRE_CHASSE_MIN) ;
#   - sinon 2 lignes : la 2e partie du titre garde la MÊME taille et le même style, puis « · durée » en petit.
# TITRE_PT = corps du titre en unités de la grille AVANT mise à l'échelle (affiche : corps fixe / K).
TITRE_UNE_LIGNE = False
TITRE_PT = 8.0
TITRE_CHASSE_MIN = 0.80
_FONT_TITRE = None


def coupe_equilibree(titre, suite):
    """coupe un titre en 2 lignes de largeurs les plus proches (la 2e porte aussi « · durée » en petit, ≈ 0,8×)"""
    mots = titre.split(' ')
    best = None
    for i in range(1, len(mots)):
        a, b = ' '.join(mots[:i]), ' '.join(mots[i:])
        if b.split(' ')[0].lower() in ('de', 'du', 'des', 'et', 'le', 'la', 'les', 'à', 'au', 'aux', "l'", 'l’') and i < len(mots) - 1 \
                and len(mots[i - 1]) > 2:
            pen = 0.0
        else:
            pen = 0.0
        la = largeur_titre(a, TITRE_PT)
        lb = largeur_titre(b, TITRE_PT) + largeur_titre(suite, TITRE_PT) * 0.75
        m = max(la, lb) + pen
        if best is None or m < best[2]:
            best = (a, b, m)
    return best


def largeur_titre(txt, pt):
    """largeur (pt) d'un titre de grille : Helvetica Neue 67 Medium Condensed, en capitales"""
    global _FONT_TITRE
    if _FONT_TITRE is None:
        import os
        from PIL import ImageFont
        _FONT_TITRE = ImageFont.truetype(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets',
                                         'polices', '3f2d5574-helvetica-neue-55', 'HelveticaNeue-MediumCond.otf'), 1000)
    return _FONT_TITRE.getlength(txt.upper()) * pt / 1000

DAYS = ['Mer', 'Jeu', 'Ven', 'Sam', 'Dim', 'Lun', 'Mar']
H_SECTION = 14.173228346456694
H_DAYS = 19.84251968503937
H_SPACER = 5.669291338582678
H_FILM = 29.5


def set_font(csr, family, style):
    csr.set('FontStyle', style)
    pr = csr.find('Properties')
    if pr is None:
        pr = etree.SubElement(csr, 'Properties')
    af = pr.find('AppliedFont')
    if af is None:
        af = etree.SubElement(pr, 'AppliedFont'); af.set('type', 'string')
    af.text = family


def _cells(table):
    return {c.get('Name'): c for c in table.findall('Cell')}


def build(d, weekends):
    t0 = d.story('ucf0d').getroot().find('.//Table')
    t1 = d.story('ucf75').getroot().find('.//Table')
    t2 = d.story('ucfd7').getroot().find('.//Table')
    c0, c1, c2 = _cells(t0), _cells(t1), _cells(t2)
    tpl_day = [copy.deepcopy(c0[f'{i}:0']) for i in range(8)]       # black day header
    tpl_spacer = copy.deepcopy(c0['0:1'])                            # white spacer (span 8)
    tpl_section = copy.deepcopy(c1['0:0'])                           # red section bar (span 8)
    tpl_name = copy.deepcopy(c2['0:4'])                              # film name + duration
    tpl_time = copy.deepcopy(c2['1:4'])                              # time cell
    row_tpl = copy.deepcopy(t2.findall('Row')[4])
    cols = [copy.deepcopy(c) for c in t0.findall('Column')]

    tid = t0.get('Self')
    for ch in list(t0):
        t0.remove(ch)

    rows, cells = [], []

    def add_row(h):
        r = copy.deepcopy(row_tpl)
        n = len(rows)
        r.set('Self', f'{tid}Row{n}'); r.set('Name', str(n))
        r.set('SingleRowHeight', str(h)); r.set('MinimumHeight', str(h))
        rows.append(r)
        return n

    def add_cell(tpl, col, row):
        c = copy.deepcopy(tpl)
        c.set('Name', f'{col}:{row}')
        c.set('Self', f'{tid}i{len(cells)}')
        cells.append(c)
        return c

    def set_runs(cell, texts):
        cs = [x for x in cell.iter('Content')]
        for x, t in zip(cs, texts):
            x.text = t

    for w_i, we in enumerate(weekends):
        if w_i:
            r = add_row(H_SPACER); add_cell(tpl_spacer, 0, r)
        r = add_row(H_SECTION)
        c = add_cell(tpl_section, 0, r)
        set_runs(c, [we['label'].upper()])
        r = add_row(H_DAYS)
        add_cell(tpl_day[0], 0, r)
        for i in range(7):
            c = add_cell(tpl_day[i + 1], i + 1, r)
            n = len(list(c.iter('Content')))
            set_runs(c, [DAYS[i], ' ', we['days'][i]] if n == 3 else [DAYS[i] + ' ', we['days'][i]])
        for name, dur, times in we['films']:
            r = add_row(H_FILM)
            c = add_cell(tpl_name, 0, r)
            set_runs(c, [name + ' ', dur])
            for i in range(7):
                c = add_cell(tpl_time, i + 1, r)
                csr = [x for x in c.iter('CharacterStyleRange')][0]
                for x in list(csr):
                    if x.tag in ('Content', 'Br'):
                        csr.remove(x)
                for k, tt in enumerate(times.get(i, [])):
                    if k:
                        etree.SubElement(csr, 'Br')
                    etree.SubElement(csr, 'Content').text = tt
    for r in rows:
        t0.append(r)
    for c in cols:
        t0.append(c)
    for c in cells:
        t0.append(c)
    t0.set('BodyRowCount', str(len(rows)))
    t0.set('HeaderRowCount', '0'); t0.set('FooterRowCount', '0')
    total = sum(float(r.get('SingleRowHeight')) for r in rows)
    return total * 25.4 / 72


TPL = {}
SPLIT = {
    'La Bataille de Gaulle partie 1': ('La Bataille de Gaulle', 'partie 1'),
    'La Bataille de Gaulle partie 2': ('La Bataille de Gaulle', 'partie 2'),
    'Tad l’explorateur et la lampe magique': ('Tad l’explorateur', 'et la lampe magique'),
    'La Pat’ Patrouille : mission Dino': ('La Pat’ Patrouille', 'mission Dino'),
}


def capture(d):
    t0 = d.story('ucf0d').getroot().find('.//Table')
    t2 = d.story('ucfd7').getroot().find('.//Table')
    c0, c2 = _cells(t0), _cells(t2)
    TPL['day'] = [copy.deepcopy(c0[f'{i}:0']) for i in range(8)]
    TPL['name'] = copy.deepcopy(c2['0:4'])
    TPL['time'] = copy.deepcopy(c2['1:4'])
    TPL['row'] = copy.deepcopy(t2.findall('Row')[4])
    TPL['cols'] = [copy.deepcopy(c) for c in t0.findall('Column')]


def auto_split(name):
    """titre de grille sur 2 lignes : (ligne1, ligne2)"""
    if isinstance(name, (list, tuple)):
        return name[0], name[1]
    if len(name) <= 22:
        return name, ''
    for sep in (' partie ', ' : ', ' – ', ' - ', ' et ', ' de ', ' du '):
        i = name.lower().find(sep, 8)
        if 8 <= i <= 26:
            head, tail = name[:i], name[i:].strip(' :–-')
            return head, tail
    i = name.rfind(' ', 0, 22)
    return name[:i], name[i + 1:]


def build_one(d, story_id, we, total_w_pt, h_film=18.0, split=None, day_w=22.0):
    t0 = d.story(story_id).getroot().find('.//Table')
    tid = t0.get('Self')
    for ch in list(t0):
        t0.remove(ch)
    rows, cells = [], []

    def add_row(h):
        r = copy.deepcopy(TPL['row']); n = len(rows)
        r.set('Self', f'{tid}Row{n}'); r.set('Name', str(n))
        r.set('SingleRowHeight', str(h)); r.set('MinimumHeight', str(h))
        rows.append(r); return n

    def add_cell(tpl, col, row):
        c = copy.deepcopy(tpl); c.set('Name', f'{col}:{row}'); c.set('Self', f'{tid}i{len(cells)}')
        cells.append(c); return c

    def set_runs(cell, texts):
        for x, t in zip(list(cell.iter('Content')), texts):
            x.text = t

    BLUE = 'Color/C=0 M=100 J=100 N=0'
    r = add_row(H_DAYS)
    c = add_cell(TPL['day'][0], 0, r)
    c.set('FillColor', BLUE)
    csr0 = list(c.iter('CharacterStyleRange'))[0]
    csr0.set('FillColor', 'Color/Paper'); csr0.set('PointSize', '9'); csr0.set('FontStyle', 'Bold')
    p0 = csr0.find('Properties')
    if p0 is not None and p0.find('AppliedFont') is not None:
        p0.find('AppliedFont').text = 'Futura'
    etree.SubElement(csr0, 'Content').text = we.get('label_horaires', 'HORAIRES')
    for i in range(7):
        c = add_cell(TPL['day'][i + 1], i + 1, r)
        c.set('FillColor', BLUE)
        n = len(list(c.iter('Content')))
        set_runs(c, [DAYS[i], ' ', we['days'][i]] if n == 3 else [DAYS[i] + ' ', we['days'][i]])
        for x in c.iter('CharacterStyleRange'):
            x.set('PointSize', '7.5')
            p = x.find('Properties')
            if p is not None and p.find('Leading') is not None:
                p.find('Leading').text = '8.5'
    GRIS = ('Color/Black', '45')
    fermes = set(we.get('fermes', []))
    for fi, film in enumerate(we['films']):
        name, dur, times = film[:3]
        opts = film[3] if len(film) > 3 else {}
        r = add_row(h_film)
        # alternance de lignes : blanc / gris clair (demande client oct. 2026)
        row_fill = ('Color/Paper', '100') if fi % 2 == 0 else ('Color/R=211 V=211 B=211', '45')
        c = add_cell(TPL['name'], 0, r)
        c.set('FillColor', row_fill[0]); c.set('FillTint', row_fill[1])
        main, sub = auto_split(name)
        suite = dur + (' · ' + opts['etiquette'] if opts.get('etiquette') else '')
        chasse = None
        if TITRE_UNE_LIGNE:
            dispo = (total_w_pt - 7 * day_w) - 5.67 - 2.83 - 1.0
            entier = ' '.join(name) if isinstance(name, (list, tuple)) else name
            r1 = dispo / largeur_titre(entier, TITRE_PT)
            if r1 >= TITRE_CHASSE_MIN:                       # titre entier sur une ligne
                main, sub, chasse = entier, '', min(1.0, r1)
            else:                                            # 2 lignes, 2e partie à la même taille
                main, sub, lmax = coupe_equilibree(entier, ' · ' + suite)
                chasse = min(1.0, dispo / lmax)
        if TITRE_UNE_LIGNE and sub:
            set_runs(c, [main, '\u2028' + ' · ' + suite])
            _t = list(c.iter('CharacterStyleRange'))[0]
            _t2 = copy.deepcopy(_t)
            for x in list(_t2):
                if x.tag in ('Content', 'Br'):
                    _t2.remove(x)
            etree.SubElement(_t2, 'Content').text = '\u2028' + sub
            _t.addnext(_t2)
            _b = list(c.iter('Content'))[-1]
            _b.text = ' · ' + suite
        else:
            bas = (sub + ' · ' if sub else '') + suite
            set_runs(c, [main, '\u2028' + bas])
        for k in ('LeftInset', 'TextLeftInset'):
            c.set(k, '5.67')
        for k in ('RightInset', 'TextRightInset'):
            c.set(k, '2.83')
        for psr in c.iter('ParagraphStyleRange'):
            psr.set('LeftIndent', '0')
        for k, x in enumerate(c.iter('CharacterStyleRange')):
            _titre = 'light' not in x.get('AppliedCharacterStyle', '')
            x.set('PointSize', '8' if _titre else '7')
            if chasse is not None and _titre and chasse < 1.0:
                x.set('HorizontalScale', str(round(chasse * 100, 1)))   # titre resserré pour tenir sur sa ligne
        if opts.get('coeur'):                            # coup de cœur : ♥ (Zapf Dingbats) couleur du cinéma après le titre
            _c0 = list(c.iter('CharacterStyleRange'))[0]
            _h = copy.deepcopy(_c0)
            for x in list(_h):
                if x.tag in ('Content', 'Br'):
                    _h.remove(x)
            set_font(_h, 'Zapf Dingbats', 'Regular')
            _h.set('FillColor', RES.COEUR); _h.set('PointSize', '7'); _h.set('Skew', '0')
            etree.SubElement(_h, 'Content').text = '\u00a0\u2665'
            _c0.addnext(_h)
        fus = opts.get('fusion')
        gris = set(opts.get('gris', [])) | fermes
        i = 0
        while i < 7:
            if fus and i == fus['de']:
                span = fus['a'] - fus['de'] + 1
                c = add_cell(TPL['time'], i + 1, r)
                c.set('ColumnSpan', str(span))
                c.set('FillColor', BLUE); c.set('FillTint', '100')
                csr = [x for x in c.iter('CharacterStyleRange')][0]
                for x in list(csr):
                    if x.tag in ('Content', 'Br'):
                        csr.remove(x)
                csr.set('PointSize', '7'); csr.set('FontStyle', '77 Bold Condensed')
                csr.set('FillColor', 'Color/Paper'); csr.set('Capitalization', 'AllCaps')
                etree.SubElement(csr, 'Content').text = fus['texte']
                i += span
                continue
            c = add_cell(TPL['time'], i + 1, r)
            csr0 = [x for x in c.iter('CharacterStyleRange')][0]
            psr = csr0.getparent()
            psr.remove(csr0)
            for x in list(csr0):
                if x.tag in ('Content', 'Br'):
                    csr0.remove(x)
            csr0.set('PointSize', '7.5')
            csr0.set('FontStyle', '77 Bold Condensed')
            if i in gris and not times.get(i):
                c.set('FillColor', GRIS[0]); c.set('FillTint', GRIS[1])
            else:
                c.set('FillColor', row_fill[0]); c.set('FillTint', row_fill[1])
            seances = times.get(i, [])
            if not seances:
                psr.append(copy.deepcopy(csr0))
            for k, tt in enumerate(seances):
                h, st = (tt, '') if isinstance(tt, str) else (tt['h'], tt.get('s', ''))
                x = copy.deepcopy(csr0)
                RES.styler(x, st, court=opts.get('court'), vostfr=opts.get('vostfr'))   # code du réseau (programme-commun)
                etree.SubElement(x, 'Content').text = h
                if k < len(seances) - 1:
                    etree.SubElement(x, 'Br')
                psr.append(x)
            i += 1
    cols = [copy.deepcopy(c) for c in TPL['cols']]
    for cc in cols[1:]:
        cc.set('SingleColumnWidth', str(day_w))
    cols[0].set('SingleColumnWidth', str(total_w_pt - 7 * day_w))
    for i, c in enumerate(cols):
        c.set('Self', f'{tid}Column{i}')
    # last row: no outer strokes (the rounded U-shape draws them)
    last = str(len(rows) - 1)
    for cc in cells:
        col, row = cc.get('Name').split(':')
        if row == last:
            cc.set('BottomEdgeStrokeWeight', '0')
            if col == '0':
                cc.set('LeftEdgeStrokeWeight', '0')
            if int(col) + int(cc.get('ColumnSpan', '1')) - 1 == 7:
                cc.set('RightEdgeStrokeWeight', '0')
    for x in rows + cols + cells:
        t0.append(x)
    t0.set('BodyRowCount', str(len(rows))); t0.set('ColumnCount', '8')
    t0.set('HeaderRowCount', '0'); t0.set('FooterRowCount', '0')
    return sum(float(r.get('SingleRowHeight')) for r in rows) * 25.4 / 72
