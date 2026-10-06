"""Approximate IDML preview renderer (for proofing only): frames, fills, images, text with real fonts, tables.
Reports overset text frames.  usage: render.py <idml_dir> <out_prefix>"""
import math, sys, os, re, glob, subprocess, unicodedata, urllib.parse, functools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lxml import etree
from PIL import Image, ImageDraw, ImageFont
from idmllib import M, mul, ap, inv, OX, OY, PT, ITEMS

ROOT = sys.argv[1]
OUT = sys.argv[2]
S = 6.0  # px per mm
FONTDIR = os.environ.get('RENDER_FONTS', '/home/claude/cine/fonts')
LINKDIRS = [x for x in os.environ.get('RENDER_LINKS', '/home/claude/cine/newlinks:/home/claude/cine/Links').split(':') if x]
OVERSET = []

# ---------------- colours ----------------
G = etree.parse(f'{ROOT}/Resources/Graphic.xml')
COL = {}
for c in G.iter('Color'):
    v = [float(x) for x in c.get('ColorValue').split()]
    if c.get('Space') == 'CMYK':
        C, Mg, Y, K = [x / 100 for x in v]
        rgb = tuple(int(255 * (1 - min(1, x * 0.92 + K))) for x in (C, Mg, Y))
    else:
        rgb = tuple(int(x) for x in v[:3])
    COL[c.get('Self')] = rgb
COL['Color/Paper'] = (255, 255, 255)
COL['Color/Black'] = (35, 31, 32)


def color(name, tint=None):
    if not name or name in ('Swatch/None', 'n'):
        return None
    rgb = COL.get(name)
    if rgb is None:
        return (128, 128, 128)
    if tint not in (None, '-1', '100'):
        t = float(tint) / 100
        rgb = tuple(int(255 - (255 - x) * t) for x in rgb)
    return rgb


# ---------------- fonts ----------------
FONTFILES = {}
for f in glob.glob(f'{FONTDIR}/**/*', recursive=True):
    if f.lower().endswith(('.ttf', '.otf', '.ttc')):
        try:
            n = 1 if not f.endswith('.ttc') else 6
            for i in range(n):
                ps = subprocess.run(['fc-scan', '--format', '%{postscriptname}', f, '--index', str(i)] if False else ['fc-scan', '--format', '%{postscriptname}|', f], capture_output=True, text=True).stdout
                for k, p in enumerate([x for x in ps.split('|') if x]):
                    FONTFILES.setdefault(p, (f, k))
                break
        except Exception:
            pass

FAMMAP = {
    ('Futura LT', 'Light'): 'FuturaLT-Light', ('Futura LT', 'Book'): 'FuturaLT-Book',
    ('Futura LT', 'Bold'): 'FuturaLT-Bold', ('Futura LT', 'Regular'): 'FuturaLT',
    ('Futura LT', 'Medium'): 'FuturaLT', ('Futura LT', 'Heavy'): 'FuturaLT-Heavy',
    ('Futura LT', 'Light Oblique'): 'FuturaLT-LightOblique', ('Futura LT', 'Book Oblique'): 'FuturaLT-BookOblique',
    ('Futura LT Medium', 'Regular'): 'FuturaLT', ('Futura LT Medium', 'Bold'): 'FuturaLT-Bold',
    ('Futura', 'Bold'): 'Futura-Bold', ('Futura', 'Medium'): 'Futura-Medium', ('Futura', 'Regular'): 'Futura-Medium',
    ('Futura', 'Condensed Medium'): 'Futura-CondensedMedium', ('Futura', 'Condensed ExtraBold'): 'Futura-CondensedExtraBold',
    ('Futura', 'Book'): 'Futura-Book', ('Futura', 'Light'): 'FuturaLT-Light',
    ('Helvetica Neue', '67 Medium Condensed'): 'HelveticaNeue-MediumCond',
    ('Helvetica Neue', '57 Condensed'): 'HelveticaNeue-Condensed',
    ('Helvetica Neue', '47 Light Condensed'): 'HelveticaNeue-LightCond',
    ('Helvetica Neue', '77 Bold Condensed'): 'HelveticaNeue-CondensedBold',
    ('Helvetica Neue', '37 Thin Condensed'): 'HelveticaNeue-ThinCond',
    ('Helvetica Neue', 'Condensed Bold'): 'HelveticaNeue-CondensedBold',
    ('Helvetica Neue', 'Light'): 'HelveticaNeue-Light', ('Helvetica Neue', 'Regular'): 'HelveticaNeue-Roman',
    ('Helvetica Neue', 'Bold'): 'HelveticaNeue-Bold', ('Helvetica Neue', 'Medium'): 'HelveticaNeue-Medium',
    ('Minion Pro', 'Regular'): 'MinionPro-Regular', ('Roboto', 'Regular'): 'Roboto-Regular',
}
MISSING = set()


@functools.lru_cache(None)
def font(fam, style, px):
    fam = re.sub(r' \((OTF|TT|T1)\)$', '', fam)
    key = FAMMAP.get((fam, style))
    if key is None:
        key = FAMMAP.get((fam, 'Regular'))
        MISSING.add((fam, style))
    f = FONTFILES.get(key) if key else None
    if f is None:
        MISSING.add((fam, style))
        f = FONTFILES.get('FuturaLT-Book')
    return ImageFont.truetype(f[0], max(1, int(round(px))), index=f[1])


# ---------------- styles ----------------
ST = etree.parse(f'{ROOT}/Resources/Styles.xml')
PSTY = {e.get('Self'): e for e in ST.iter('ParagraphStyle')}
CSTY = {e.get('Self'): e for e in ST.iter('CharacterStyle')}
CHAR_KEYS = ('PointSize', 'FontStyle', 'HorizontalScale', 'Tracking', 'Capitalization', 'FillColor', 'FillTint', 'Position',
             'Underline', 'Skew')
PARA_KEYS = ('Justification', 'LeftIndent', 'RightIndent', 'FirstLineIndent', 'SpaceBefore', 'SpaceAfter')


def apply(d, e):
    for k in CHAR_KEYS + PARA_KEYS:
        if e.get(k) is not None:
            d[k] = e.get(k)
    p = e.find('Properties')
    if p is not None:
        for k in ('AppliedFont', 'Leading'):
            x = p.find(k)
            if x is not None and x.text is not None:
                d[k] = x.text


def chain(sty, table, name):
    out = []
    while name and name in table:
        e = table[name]
        out.insert(0, e)
        b = e.find('Properties/BasedOn')
        nb = b.text if b is not None else None
        if nb and not nb.startswith(('ParagraphStyle/', 'CharacterStyle/')):
            nb = ('ParagraphStyle/' if table is PSTY else 'CharacterStyle/') + nb
        if nb == name:
            break
        name = nb
    return out


def resolve(psr, csr):
    d = {}
    apply(d, PSTY['ParagraphStyle/$ID/[No paragraph style]'])
    for e in chain(None, PSTY, psr.get('AppliedParagraphStyle')):
        apply(d, e)
    apply(d, psr)
    for e in chain(None, CSTY, csr.get('AppliedCharacterStyle')):
        apply(d, e)
    apply(d, csr)
    return d


# ---------------- text engine ----------------
def story_paragraphs(container):
    """returns list of paragraphs; paragraph = (pattrs, [ (text, cattrs) ...]) ; tables returned as ('TABLE', el)"""
    paras = []
    cur = None

    def newp(psr):
        nonlocal cur
        cur = [resolve(psr, etree.Element('x')), []]
        paras.append(cur)

    for psr in container.iter('ParagraphStyleRange'):
        if psr.getparent().tag == 'Cell' and container.tag != 'Cell':
            continue
        # skip ranges that belong to nested cells
        anc = psr.getparent()
        skip = False
        while anc is not None and anc is not container:
            if anc.tag == 'Cell':
                skip = True
                break
            anc = anc.getparent()
        if skip:
            continue
        if cur is None or cur[0].get('_closed'):
            newp(psr)
        else:
            cur[0].update({k: v for k, v in resolve(psr, etree.Element('x')).items() if k in PARA_KEYS})
        for csr in psr.findall('CharacterStyleRange'):
            a = resolve(psr, csr)
            for ch in csr:
                if ch.tag == 'Content':
                    cur[1].append((ch.text or '', a))
                elif ch.tag == 'Br':
                    cur[0]['_closed'] = True
                    newp(psr)
                elif ch.tag == 'Table':
                    paras.append(['TABLE', ch])
                    newp(psr)
    return [p for p in paras if p[0] == 'TABLE' or p[1]]


def run_font(a):
    pt = float(a.get('PointSize', 12))
    px = pt * S / PT
    return font(a.get('AppliedFont', 'Minion Pro'), a.get('FontStyle', 'Regular'), px * 4), px


def measure(txt, a):
    f, px = run_font(a)
    hs = float(a.get('HorizontalScale', 100)) / 100
    tr = float(a.get('Tracking', 0)) / 1000 * px
    if a.get('Capitalization') == 'AllCaps':
        txt = txt.upper()
    return f.getlength(txt) / 4 * hs + tr * len(txt)


def layout_para(runs, width):
    """greedy line breaking -> list of lines (list of (text, attrs)), widths"""
    tokens = []
    for txt, a in runs:
        for piece in re.split(r'(\s+| )', txt):
            if piece:
                tokens.append((piece, a))
    lines, line, w = [], [], 0
    for tok, a in tokens:
        if tok == ' ':
            lines.append((line, w)); line, w = [], 0
            continue
        tw = measure(tok.replace('\t', '    '), a)
        if line and not tok.isspace() and w + tw > width:
            # trim trailing space
            lines.append((line, w)); line, w = [], 0
        if not line and tok.isspace():
            continue
        line.append((tok.replace('\t', '    '), a)); w += tw
    if line:
        lines.append((line, w))
    return lines or [([], 0)]


def leading(a):
    pt = float(a.get('PointSize', 12))
    L = a.get('Leading', 'Auto')
    v = pt * 1.2 if L in ('Auto', None) else float(L)
    return v * S / PT


def draw_text(draw, img, container, box, vjust='TopAlign', label=''):
    x0, y0, x1, y1 = box
    W = x1 - x0
    paras = story_paragraphs(container)
    blocks = []  # (kind, data, height)
    for p in paras:
        if p[0] == 'TABLE':
            blocks.append(('table', p[1], table_height(p[1])))
            continue
        pa, runs = p
        li = float(pa.get('LeftIndent', 0)) * S / PT
        ri = float(pa.get('RightIndent', 0)) * S / PT
        lines = layout_para(runs, W - li - ri)
        h = 0
        ls = []
        for ln, lw in lines:
            lead = max([leading(a) for _, a in ln] or [leading(runs[0][1])])
            ls.append((ln, lw, lead))
            h += lead
        sb = float(pa.get('SpaceBefore', 0)) * S / PT
        sa = float(pa.get('SpaceAfter', 0)) * S / PT
        blocks.append(('p', (pa, ls, li, ri, sb, sa), h + sb + sa))
    total = sum(b[2] for b in blocks)
    y = y0
    if vjust == 'CenterAlign':
        y = y0 + max(0, (y1 - y0 - total) / 2)
    elif vjust == 'BottomAlign':
        y = y0 + max(0, y1 - y0 - total)
    over = False
    for kind, data, h in blocks:
        if kind == 'table':
            draw_table(draw, img, data, x0, y)
            y += h
            continue
        pa, ls, li, ri, sb, sa = data
        y += sb
        for ln, lw, lead in ls:
            if y + lead > y1 + 1.5:
                over = True
            j = pa.get('Justification', 'LeftAlign')
            xx = x0 + li
            if j == 'CenterAlign':
                xx = x0 + li + (W - li - ri - lw) / 2
            elif j == 'RightAlign':
                xx = x1 - ri - lw
            base = y + lead * 0.78
            for ti, (tok, a) in enumerate(ln):
                if tok.strip(' ') == '' and '    ' in tok and ti:
                    rest = sum(measure(t2, a2) for t2, a2 in ln[ti + 1:])
                    xx = max(xx, x1 - ri - rest)
                    continue
                f, px = run_font(a)
                t = tok.upper() if a.get('Capitalization') == 'AllCaps' else tok
                c = color(a.get('FillColor', 'Color/Black'), a.get('FillTint')) or (0, 0, 0)
                hs = float(a.get('HorizontalScale', 100)) / 100
                tr = float(a.get('Tracking', 0)) / 1000 * px
                if not t.isspace():
                    fs = font(a.get('AppliedFont', 'Minion Pro'), a.get('FontStyle', 'Regular'), px)
                    sk = float(a.get('Skew', 0) or 0)
                    if sk:                                   # faux italique (Skew InDesign) : texte cisaillé
                        tw = int(measure(tok, a)) + int(px) + 4
                        th = int(px * 1.6) + 4
                        lay = Image.new('RGBA', (tw, th), (0, 0, 0, 0))
                        ld = ImageDraw.Draw(lay)
                        cx = 2
                        for chh in t:
                            ld.text((cx, th - int(px * 0.35)), chh, font=fs, fill=c, anchor='ls')
                            cx += fs.getlength(chh) * hs + tr
                        k = math.tan(math.radians(sk))
                        lay = lay.transform(lay.size, Image.AFFINE, (1, k, -k * th, 0, 1, 0), Image.BICUBIC)
                        img.paste(lay, (int(xx) - 2, int(base - th + px * 0.35)), lay)
                    elif abs(hs - 1) < 0.02 and abs(tr) < 0.05:
                        draw.text((xx, base), t, font=fs, fill=c, anchor='ls')
                    else:
                        cx = xx
                        for chh in t:
                            draw.text((cx, base), chh, font=fs, fill=c, anchor='ls')
                            cx += fs.getlength(chh) * hs + tr
                    if str(a.get('Underline', '')).lower() == 'true':   # soulignement
                        uy = base + max(1, px * 0.12)
                        draw.line([(xx, uy), (xx + measure(tok, a), uy)], fill=c, width=max(1, int(px * 0.08)))
                xx += measure(tok, a)
            y += lead
        y += sa
    if over:
        OVERSET.append(label if label == 'cell' else f'{label}:+{(y - y1) / S:.1f}mm')
        draw.rectangle([x1 - 6, y1 - 6, x1, y1], fill=(255, 0, 0))
    return total


def table_height(t):
    return sum(float(r.get('SingleRowHeight')) for r in t.findall('Row')) * S / PT


def draw_table(draw, img, t, x, y):
    cw = [float(c.get('SingleColumnWidth')) * S / PT for c in t.findall('Column')]
    rh = [float(r.get('SingleRowHeight')) * S / PT for r in t.findall('Row')]
    cx = [x + sum(cw[:i]) for i in range(len(cw) + 1)]
    ry = [y + sum(rh[:i]) for i in range(len(rh) + 1)]
    for c in t.findall('Cell'):
        ci, ri = map(int, c.get('Name').split(':'))
        cs = int(c.get('ColumnSpan', 1)); rs = int(c.get('RowSpan', 1))
        bx = (cx[ci], ry[ri], cx[ci + cs], ry[ri + rs])
        fc = color(c.get('FillColor'), c.get('FillTint'))
        if fc:
            draw.rectangle(bx, fill=fc)
        draw.rectangle(bx, outline=(170, 170, 170))
        ins = 0.6 * S
        draw_text(draw, img, c, (bx[0] + ins, bx[1] + 0.3 * S, bx[2] - ins * 0.3, bx[3]), c.get('VerticalJustification', 'TopAlign'), label='cell')


# ---------------- graphics ----------------
@functools.lru_cache(None)
def load_link(uri):
    name = urllib.parse.unquote(uri.split('/')[-1])
    cands = []
    for dd in LINKDIRS:
        for f in os.listdir(dd):
            if unicodedata.normalize('NFC', f) == unicodedata.normalize('NFC', name):
                cands.append(os.path.join(dd, f))
    if not cands:
        print('missing link', name)
        return None
    p = cands[0]
    try:
        if p.lower().endswith(('.ai', '.pdf')):
            out = f'/tmp/_r_{abs(hash(p))}'
            subprocess.run(['pdftoppm', '-r', '150', '-png', '-singlefile', '-f', '1', '-l', '1', p, out], check=True)
            return Image.open(out + '.png').convert('RGBA')
        im = Image.open(p)
        im.load()
        return im.convert('RGBA')
    except Exception as e:
        print('cannot open', p, e)
        return None


def to_px(m, x, y, org):
    X, Y = ap(m, x, y)
    return ((X + OX) / PT * S - org[0], (Y + OY) / PT * S - org[1])


class R:
    def __init__(self, org, size):
        self.org = org
        self.img = Image.new('RGB', size, 'white')
        self.draw = ImageDraw.Draw(self.img)

    def item(self, el, parent_m):
        m = mul(M(el.get('ItemTransform', '1 0 0 1 0 0')), parent_m)
        if el.tag == 'Group':
            for ch in el:
                if ch.tag in ITEMS:
                    self.item(ch, m)
            return
        if el.get('Visible') == 'false':
            return
        pp = el.find('Properties/PathGeometry/GeometryPathType/PathPointArray')
        pts = [to_px(m, *M(p.get('Anchor')), self.org) for p in pp] if pp is not None else []
        fill = color(el.get('FillColor'), el.get('FillTint'))
        if fill and len(pts) > 2:
            if el.tag == 'Oval':
                xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
                self.draw.ellipse([min(xs), min(ys), max(xs), max(ys)], fill=fill)
            else:
                self.draw.polygon(pts, fill=fill)
        # graphic content
        for g in el:
            if g.tag in ('Image', 'PDF', 'EPS', 'ImportedPage'):
                self.graphic(g, m, pts)
        if el.tag == 'TextFrame':
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            tfp = el.find('TextFramePreference')
            vj = tfp.get('VerticalJustification', 'TopAlign') if tfp is not None else 'TopAlign'
            st = etree.parse(f"{ROOT}/Stories/Story_{el.get('ParentStory')}.xml").getroot().find('Story')
            ins = [0.0, 0.0, 0.0, 0.0]                      # marges intérieures (haut, gauche, bas, droite) en pt
            if tfp is not None:
                li = tfp.find('Properties/InsetSpacing')
                if li is not None and li.get('type') == 'list':
                    ins = [float(x.text) for x in li][:4]
                elif li is not None and li.text:
                    ins = [float(li.text)] * 4
                elif tfp.get('InsetSpacing'):
                    ins = [float(v) for v in tfp.get('InsetSpacing').split()][:4]
            k_ = S / PT
            draw_text(self.draw, self.img, st, (min(xs) + ins[1] * k_, min(ys) + ins[0] * k_,
                                                max(xs) - ins[3] * k_, max(ys) - ins[2] * k_), vj, label=el.get('Self'))
        sc = color(el.get('StrokeColor'), el.get('StrokeTint'))
        sw = float(el.get('StrokeWeight', 0) or 0)
        if sc and sw > 0 and len(pts) > 1:
            closed = el.find('Properties/PathGeometry/GeometryPathType').get('PathOpen') == 'false'
            self.draw.line(pts + ([pts[0]] if closed else []), fill=sc, width=max(1, int(sw * S / PT)))

    def graphic(self, g, m_rect, clip_pts):
        lk = g.find('Link')
        if lk is None:
            return
        src = load_link(lk.get('LinkResourceURI'))
        if src is None:
            return
        gm = mul(M(g.get('ItemTransform', '1 0 0 1 0 0')), m_rect)
        gb = g.find('Properties/GraphicBounds')
        L, T, Rr, B = [float(gb.get(k)) for k in ('Left', 'Top', 'Right', 'Bottom')]
        p0 = to_px(gm, L, T, self.org); p1 = to_px(gm, Rr, B, self.org)
        x0, x1 = sorted([p0[0], p1[0]]); y0, y1 = sorted([p0[1], p1[1]])
        w, h = int(x1 - x0), int(y1 - y0)
        if w < 1 or h < 1 or w > 20000 or h > 20000:
            return
        im = src.resize((w, h))
        if g.tag == 'PDF':
            # crop of pdf page: GraphicBounds are the page box
            pass
        mask = Image.new('L', self.img.size, 0)
        ImageDraw.Draw(mask).polygon(clip_pts, fill=255)
        layer = Image.new('RGBA', self.img.size, (0, 0, 0, 0))
        layer.paste(im, (int(x0), int(y0)))
        a = layer.split()[3]
        from PIL import ImageChops
        a = ImageChops.multiply(a, mask)
        self.img.paste(layer.convert('RGB'), (0, 0), a)


def page_origin(spread):
    sm = M(spread.get('ItemTransform'))
    pg = spread.find('Page')
    pm = mul(M(pg.get('ItemTransform')), sm)
    X, Y = ap(pm, 0, 0)
    gb = [float(v) for v in pg.get('GeometricBounds').split()]
    return (X + OX) / PT, (Y + OY) / PT, pg.get('AppliedMaster'), (gb[3] - gb[1]) / PT, (gb[2] - gb[0]) / PT


DM = etree.parse(f'{ROOT}/designmap.xml')
masters = {}
for ms in DM.getroot().iter('{*}MasterSpread'):
    t = etree.parse(f"{ROOT}/{ms.get('src')}").getroot().find('MasterSpread')
    masters[t.get('Self')] = t
for n, sp in enumerate(DM.getroot().iter('{*}Spread')):
    s = etree.parse(f"{ROOT}/{sp.get('src')}").getroot().find('Spread')
    ox, oy, master, PW, PH = page_origin(s)
    bleed = 3
    org = ((ox - bleed) * S, (oy - bleed) * S)
    r = R(org, (int((PW + 2 * bleed) * S), int((PH + 2 * bleed) * S)))
    if master in masters:
        ms = masters[master]
        for ch in ms:
            if ch.tag in ITEMS:
                r.item(ch, M(ms.get('ItemTransform')))
    for ch in s:
        if ch.tag in ITEMS:
            r.item(ch, M(s.get('ItemTransform')))
    # trim marks
    d = r.draw
    tb = [bleed * S, bleed * S, (PW + bleed) * S, (PH + bleed) * S]
    d.rectangle(tb, outline=(0, 200, 255))
    for xx in ((99, 198) if PW > PH else ()):
        d.line([((xx + bleed) * S, 0), ((xx + bleed) * S, 8)], fill=(0, 200, 255))
    r.img.save(f'{OUT}-{n + 1}.png')
    print('page', n + 1, 'origin', round(ox, 1), round(oy, 1))
print('OVERSET:', [o for o in OVERSET if o != 'cell'], 'cells overset:', OVERSET.count('cell'))
print('MISSING FONTS:', MISSING)
