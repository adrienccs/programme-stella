#!/usr/bin/env python3
"""
Dossier d'assemblage complet (IDML + Links + Document fonts + script de reliage + aperçus).

  python3 moteur/assembler.py --kit . --cinema cinemas/7emeart.json --sortie SORTIE --nom "NOM" \
          --images mois/<id>-AAAA-MM/images --version v11 [--apercus SORTIE/apercu]

- Les images sont copiées dans Links/ sous des noms « sûrs » (sans accents, apostrophes ni virgules)
  pour éviter les soucis d'encodage Mac/Linux.
- Les liens de l'IDML pointent vers <dossier_assemblage_mac>/<NOM>/Links/<fichier> : si Adrien dézippe le
  dossier à cet endroit, tout est relié dès l'ouverture. Sinon : script « Relier les liens.jsx » (1 clic).
"""
import argparse, glob, json, os, re, shutil, unicodedata, urllib.parse, zipfile

ap = argparse.ArgumentParser()
ap.add_argument('--kit', required=True); ap.add_argument('--cinema', required=True)
ap.add_argument('--sortie', required=True); ap.add_argument('--nom', required=True)
ap.add_argument('--images', required=True); ap.add_argument('--version', required=True)
ap.add_argument('--apercus', default=None)
A = ap.parse_args()
CIN = json.load(open(A.cinema, encoding='utf-8'))
SRC = os.path.join(A.sortie, '_idml')
DIRS = [A.images, os.path.join(A.kit, 'assets', 'cinemas', CIN['id']), os.path.join(A.kit, 'assets', 'communs-hd'),
        os.path.join(A.kit, 'assets', 'communs')]


def nfc(s):
    return unicodedata.normalize('NFC', s)


def safe(name):
    base = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    base = re.sub(r"[’'`,;:()\[\]]", '', base)
    base = re.sub(r'\s+', ' ', base).strip()
    return base or 'image'


NOMV = f'{A.nom} {A.version}'          # version dans le nom : impossible de confondre deux livraisons
DEST = os.path.join(A.sortie, 'assemblage', NOMV)
shutil.rmtree(os.path.join(A.sortie, 'assemblage'), ignore_errors=True)
os.makedirs(os.path.join(DEST, 'Links'))
shutil.copytree(os.path.join(A.kit, 'assets', 'polices-indesign'), os.path.join(DEST, 'Document fonts'))
shutil.copy(os.path.join(A.kit, 'outils', 'Relier les liens.jsx'), DEST)

base_mac = CIN.get('dossier_assemblage_mac', '').rstrip('/')
new_prefix = (base_mac + '/' + urllib.parse.quote(NOMV) + '/Links/') if base_mac else None

renamed, missing = {}, []
for sp in glob.glob(os.path.join(SRC, 'Spreads', '*.xml')) + glob.glob(os.path.join(SRC, 'MasterSpreads', '*.xml')):
    xml = open(sp, encoding='utf-8').read()

    def fix(m):
        uri = m.group(1)
        name = nfc(urllib.parse.unquote(uri.split('/')[-1]))
        if name not in renamed:
            for d in DIRS:
                if not os.path.isdir(d):
                    continue
                hit = [f for f in os.listdir(d) if nfc(f) == name]
                if hit:
                    new = safe(name)
                    src_, dst_ = os.path.join(d, hit[0]), os.path.join(DEST, 'Links', new)
                    if new.lower().endswith(('.jpg', '.jpeg')) and os.path.getsize(src_) > 5e6:
                        # JPEG très lourd (ex. projecteurs 6240 px, 12 Mo) : recompressé à l'IDENTIQUE en pixels
                        # (même cadrage dans InDesign) pour que le dossier tienne en UN seul envoi < 30 Mo
                        from PIL import Image as _I
                        _im = _I.open(src_); _im.save(dst_, quality=85, dpi=_im.info.get('dpi', (72, 72)), optimize=True)
                    else:
                        shutil.copy(src_, dst_)
                    renamed[name] = new
                    break
            else:
                missing.append(name); renamed[name] = name
        new = renamed[name]
        prefix = new_prefix or uri[:uri.rfind('/') + 1]
        if not prefix.startswith('file:/'):        # garde-fou : un lien sans chemin file:/ est ignoré par InDesign
            prefix = 'file:/Volumes/Clients/Links/'
        return f'LinkResourceURI="{prefix}{urllib.parse.quote(new)}"'
    xml = re.sub(r'LinkResourceURI="([^"]+)"', fix, xml)
    open(sp, 'w', encoding='utf-8').write(xml)

idml = os.path.join(DEST, NOMV + '.idml')
with zipfile.ZipFile(idml, 'w') as z:
    z.write(os.path.join(SRC, 'mimetype'), 'mimetype', compress_type=zipfile.ZIP_STORED)
    for root, _, files in os.walk(SRC):
        for f in sorted(files):
            p = os.path.join(root, f); a = os.path.relpath(p, SRC)
            if a != 'mimetype':
                z.write(p, a, compress_type=zipfile.ZIP_DEFLATED)
if A.apercus:
    pages = [i for i in (1, 2) if os.path.exists(f'{A.apercus}-{i}.png')]
    for i, lab in ((1, 'interieur'), (2, 'exterieur')):
        p = f'{A.apercus}-{i}.png'
        if os.path.exists(p):
            shutil.copy(p, os.path.join(DEST, f'APERCU {lab}.png' if len(pages) > 1 else 'APERCU.png'))

lieu = (urllib.parse.unquote(base_mac.replace('file:', '')) + '/') if base_mac else '(non défini)'
open(os.path.join(DEST, 'LISEZ-MOI.txt'), 'w', encoding='utf-8').write(f"""{NOMV}
Dossier d'assemblage complet

  {NOMV}.idml      → à ouvrir dans InDesign
  Links/                → {len(renamed)} images liées (noms sans accents : pas de souci d'encodage)
  Document fonts/       → polices du document (activées automatiquement par InDesign)
  Relier les liens.jsx  → script qui relie TOUTES les images en une fois

LIENS — 2 façons, sans relier image par image :
 A. Dézipper ce dossier dans : {lieu}
    → les liens sont trouvés directement à l'ouverture.
 B. Ailleurs : ouvrir l'IDML, puis lancer le script « Relier les liens.jsx »
    (Fenêtre > Utilitaires > Scripts ; la 1re fois : clic droit sur « Utilisateur » > Faire apparaître dans
    le Finder, y copier le script) → choisir le dossier Links → tout est relié.
 Ensuite : Fichier > Enregistrer sous… en .indd DANS ce dossier (à côté de Links). Les ouvertures suivantes
 du .indd retrouvent les liens toutes seules.

Polices : Helvetica Neue 77 Bold Condensed n'est pas fournie (déjà installée sur le poste de PAO).
Polices sous licence : usage interne pour ce document uniquement.
""")
zp = os.path.join(A.sortie, f'{NOMV} - ASSEMBLAGE.zip')
if os.path.exists(zp):
    os.remove(zp)
shutil.make_archive(zp[:-4], 'zip', os.path.join(A.sortie, 'assemblage'), NOMV)
print('ASSEMBLAGE', zp, f'({len(renamed)} liens)', 'MANQUANTS:', missing)
