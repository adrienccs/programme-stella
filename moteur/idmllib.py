"""Small helpers to edit an unpacked IDML (geometry in page-millimetres, as printed by scan.py)."""
import copy, os, re, urllib.parse
from lxml import etree

PT = 72 / 25.4          # mm -> pt
OX, OY = 420.944881889, 297.6377952755
ITEMS = ('Group', 'Rectangle', 'TextFrame', 'Polygon', 'GraphicLine', 'Oval')


def M(s):
    return [float(v) for v in s.split()]


def mul(m, n):
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return [a*A + b*C, a*B + b*D, c*A + d*C, c*B + d*D, e*A + f*C + E, e*B + f*D + F]


def inv(m):
    a, b, c, d, e, f = m
    det = a*d - b*c
    ia, ib, ic, id_ = d/det, -b/det, -c/det, a/det
    return [ia, ib, ic, id_, -(e*ia + f*ic), -(e*ib + f*id_)]


def ap(m, x, y):
    a, b, c, d, e, f = m
    return (x*a + y*c + e, x*b + y*d + f)


def fmt(m):
    return ' '.join(repr(round(v, 10)) for v in m)


class Doc:
    def __init__(self, root):
        self.root = root
        self.dm = etree.parse(f'{root}/designmap.xml')
        self.spreads = {}
        for sp in self.dm.getroot().iter('{*}Spread'):
            p = sp.get('src')
            self.spreads[p] = etree.parse(f'{root}/{p}')
        self.stories = {}
        self.counter = 0
        self.deleted_stories = []

    # ---------- lookup ----------
    def el(self, sid):
        for t in self.spreads.values():
            r = t.xpath(f'//*[@Self="{sid}"]')
            if r:
                return r[0]
        raise KeyError(sid)

    def story(self, sid):
        if sid not in self.stories:
            self.stories[sid] = etree.parse(f'{self.root}/Stories/Story_{sid}.xml')
        return self.stories[sid]

    def newid(self, p='cmy'):
        self.counter += 1
        return f'{p}{self.counter:04d}'

    # ---------- geometry ----------
    def chain(self, el):
        """full transform el-inner -> spread"""
        m = M(el.get('ItemTransform', '1 0 0 1 0 0'))
        p = el.getparent()
        while p is not None and p.tag != 'Spread':
            if p.get('ItemTransform'):
                m = mul(m, M(p.get('ItemTransform')))
            p = p.getparent()
        if p is not None:
            m = mul(m, M(p.get('ItemTransform')))
        return m

    def parent_chain(self, el):
        p = el.getparent()
        if p.tag == 'Spread':
            return M(p.get('ItemTransform'))
        return self.chain(p)

    def anchors(self, el):
        pp = el.find('Properties/PathGeometry/GeometryPathType/PathPointArray')
        return pp, [M(x.get('Anchor')) for x in pp]

    def bbox(self, el):
        """bbox in page mm"""
        if el.tag == 'Group':
            bbs = [self.bbox(c) for c in el if c.tag in ITEMS]
            return (min(b[0] for b in bbs), min(b[1] for b in bbs), max(b[2] for b in bbs), max(b[3] for b in bbs))
        m = self.chain(el)
        _, pts = self.anchors(el)
        P = [ap(m, x, y) for x, y in pts]
        xs = [(p[0] + OX) / PT for p in P]
        ys = [(p[1] + OY) / PT for p in P]
        return (min(xs), min(ys), max(xs), max(ys))

    def move(self, el, dx_mm, dy_mm):
        pc = self.parent_chain(el)
        lin = inv([pc[0], pc[1], pc[2], pc[3], 0, 0])
        dx, dy = ap(lin, dx_mm * PT, dy_mm * PT)
        m = M(el.get('ItemTransform', '1 0 0 1 0 0'))
        m[4] += dx
        m[5] += dy
        el.set('ItemTransform', fmt(m))

    def set_bounds(self, el, x0, y0, x1, y1):
        """axis-aligned rectangle-ish frame -> new bbox in page mm (keeps transform, edits anchors)"""
        m = inv(self.chain(el))
        pp, pts = self.anchors(el)
        X0, Y0 = ap(m, x0 * PT - OX, y0 * PT - OY)
        X1, Y1 = ap(m, x1 * PT - OX, y1 * PT - OY)
        ox = [p[0] for p in pts]; oy = [p[1] for p in pts]
        mnx, mxx, mny, mxy = min(ox), max(ox), min(oy), max(oy)
        for node, (x, y) in zip(pp, pts):
            nx = min(X0, X1) if abs(x - mnx) < abs(x - mxx) else max(X0, X1)
            ny = min(Y0, Y1) if abs(y - mny) < abs(y - mxy) else max(Y0, Y1)
            v = f'{nx} {ny}'
            for k in ('Anchor', 'LeftDirection', 'RightDirection'):
                node.set(k, v)
        # graphic inside a resized frame is re-fitted by caller
        return el

    def inner_bounds(self, el):
        _, pts = self.anchors(el)
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        return min(xs), min(ys), max(xs), max(ys)

    # ---------- deletion / duplication ----------
    def delete(self, sid):
        el = self.el(sid)
        for tf in el.iter('TextFrame'):
            self._drop_story(tf.get('ParentStory'))
        el.getparent().remove(el)

    def _drop_story(self, st):
        still = any(t.xpath(f'//TextFrame[@ParentStory="{st}"]') for t in self.spreads.values())
        self.deleted_stories.append(st)

    def finalize_story_deletes(self):
        for st in self.deleted_stories:
            used = any(t.xpath(f'//TextFrame[@ParentStory="{st}"]') for t in self.spreads.values())
            if used:
                continue
            for e in self.dm.getroot().iter('{*}Story'):
                if e.get('src') == f'Stories/Story_{st}.xml':
                    e.getparent().remove(e)
            p = f'{self.root}/Stories/Story_{st}.xml'
            if os.path.exists(p):
                os.remove(p)
            self.stories.pop(st, None)

    def duplicate(self, sid):
        """copy a page item (with its stories) next to the original; returns new element"""
        el = self.el(sid)
        new = copy.deepcopy(el)
        idmap = {}
        for e in new.iter():
            if e.get('Self'):
                n = self.newid()
                idmap[e.get('Self')] = n
                e.set('Self', n)
        for tf in new.iter('TextFrame'):
            old = tf.get('ParentStory')
            ns = self.newid('cms')
            st = copy.deepcopy(self.story(old))
            s = st.getroot().find('Story')
            s.set('Self', ns)
            for e in s.iter():
                if e.get('Self') and e is not s:
                    e.set('Self', self.newid())
            self.stories[ns] = st
            tf.set('ParentStory', ns)
            tf.set('PreviousTextFrame', 'n'); tf.set('NextTextFrame', 'n')
            ref = [e for e in self.dm.getroot().iter('{*}Story')][-1]
            ne = copy.deepcopy(ref)
            ne.set('src', f'Stories/Story_{ns}.xml')
            ref.addnext(ne)
        el.addnext(new)
        return new

    # ---------- text ----------
    def runs(self, sid):
        st = self.story(sid)
        return [c for c in st.getroot().iter('Content', 'Br')]

    def set_text(self, sid, mapping):
        """mapping: index -> str (Content) ; None deletes the node (Content or Br)"""
        rs = self.runs(sid)
        for i, v in mapping.items():
            n = rs[i]
            if v is None:
                n.getparent().remove(n)
            else:
                assert n.tag == 'Content', (sid, i, n.tag)
                n.text = v

    def plain(self, sid):
        return ''.join((c.text or '') if c.tag == 'Content' else '\n' for c in self.runs(sid))

    # ---------- images ----------
    def place_image(self, rect_id, path_uri, px_w, px_h, mode='fill', ext='jpg', align=(0.5, 0.5)):
        rect = self.el(rect_id)
        img = rect.find('Image')
        if img is None:
            # build an Image node from a template
            tmpl = self._image_template
            for ch in list(rect):
                if ch.tag in ('PDF', 'EPS', 'Image', 'ImportedPage'):
                    rect.remove(ch)
            img = copy.deepcopy(tmpl)
            img.set('Self', self.newid())
            img.find('Link').set('Self', self.newid())
            rect.append(img)
            rect.set('ContentType', 'GraphicType')
        x0, y0, x1, y1 = self.inner_bounds(rect)
        W, H = x1 - x0, y1 - y0
        s = (max if mode == 'fill' else min)(W / px_w, H / px_h)
        tx = x0 + (W - px_w * s) * align[0]
        ty = y0 + (H - px_h * s) * align[1]
        img.set('ItemTransform', fmt([s, 0, 0, s, tx, ty]))
        img.set('ActualPpi', '72 72')
        img.set('EffectivePpi', f'{round(72/s)} {round(72/s)}')
        fmtname = '$ID/JPEG' if ext == 'jpg' else '$ID/Portable Network Graphics (PNG)'
        img.set('ImageTypeName', fmtname)
        gb = img.find('Properties/GraphicBounds')
        gb.set('Left', '0'); gb.set('Top', '0'); gb.set('Right', str(px_w)); gb.set('Bottom', str(px_h))
        lk = img.find('Link')
        lk.set('LinkResourceURI', path_uri)
        lk.set('LinkResourceFormat', fmtname)
        lk.set('StoredState', 'Normal')
        for a in ('LinkImportStamp', 'LinkImportModificationTime', 'LinkImportTime', 'LinkResourceSize'):
            if a in lk.attrib:
                del lk.attrib[a]
        ffo = rect.find('FrameFittingOption')
        if ffo is not None:
            for a in ('LeftCrop', 'RightCrop', 'TopCrop', 'BottomCrop'):
                if a in ffo.attrib:
                    del ffo.attrib[a]
            ffo.set('FittingOnEmptyFrame', 'FillProportionally' if mode == 'fill' else 'Proportionally')
        return img

    def save(self):
        self.finalize_story_deletes()
        for p, t in self.spreads.items():
            t.write(f'{self.root}/{p}', xml_declaration=True, encoding='UTF-8', standalone=True)
        for sid, t in self.stories.items():
            t.write(f'{self.root}/Stories/Story_{sid}.xml', xml_declaration=True, encoding='UTF-8', standalone=True)
        self.dm.write(f'{self.root}/designmap.xml', xml_declaration=True, encoding='UTF-8', standalone=True)


def shift_points_y(doc, el, near_y_mm, new_y_mm, tol=0.5):
    """move every path point lying at y≈near_y (page mm) to new_y"""
    m = doc.chain(el); mi = inv(m)
    pp, pts = doc.anchors(el)
    for node, (x, y) in zip(pp, pts):
        X, Y = ap(m, x, y)
        if abs((Y + OY) / PT - near_y_mm) < tol:
            nx, ny = ap(mi, X, new_y_mm * PT - OY)
            for k in ('Anchor', 'LeftDirection', 'RightDirection'):
                node.set(k, f'{nx} {ny}')
