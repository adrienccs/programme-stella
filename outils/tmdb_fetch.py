#!/usr/bin/env python3
"""
Récupère sur TMDB (en français) les fiches, affiches HD et photos des films listés dans
mois/<id>-AAAA-MM/films.txt  (une ligne par film : « Titre » ou « Titre | année » ou « Titre | tmdb:12345 »).

Sortie : mois/<id>-AAAA-MM/tmdb/
  fiches.json                → réalisateur, casting, durée, pays, genres, sortie FR, résumé FR, id TMDB
  <slug> affiche.jpg         → affiche HD (langue fr de préférence)
  <slug> photo 1..3.jpg      → photos du film sans texte (backdrops), pour remplissage et bandeaux
  RAPPORT.md                 → ce qui a été trouvé / à vérifier
Clé : variable d'environnement TMDB_API_KEY (clé v3 de 32 caractères OU jeton v4 « eyJ… »).
"""
import json, os, re, sys, time, unicodedata, urllib.parse, urllib.request

KEY = os.environ.get('TMDB_API_KEY', '').strip()
if not KEY:
    sys.exit('TMDB_API_KEY manquant')
V4 = KEY.startswith('eyJ')
API = 'https://api.themoviedb.org/3'
IMG = 'https://image.tmdb.org/t/p/original'


def get(path, **params):
    if not V4:
        params['api_key'] = KEY
    url = f'{API}{path}?{urllib.parse.urlencode(params)}'
    req = urllib.request.Request(url, headers={'accept': 'application/json',
                                               **({'Authorization': f'Bearer {KEY}'} if V4 else {})})
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            err = e; time.sleep(2)
    raise err


def download(path, dest):
    with urllib.request.urlopen(IMG + path, timeout=60) as r, open(dest, 'wb') as f:
        f.write(r.read())


def empreinte(path):
    try:
        from PIL import Image
        im = Image.open(path).convert('L').resize((9, 8))
        px = list(im.getdata())
        return [px[r * 9 + c] > px[r * 9 + c + 1] for r in range(8) for c in range(8)]
    except Exception:
        return [os.path.getsize(path)]


def slug(t):
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', t).strip()


def duree(minutes):
    return f'{minutes // 60}h{minutes % 60:02d}' if minutes else ''


def run(folder):
    src = os.path.join(folder, 'films.txt')
    out = os.path.join(folder, 'tmdb')
    os.makedirs(out, exist_ok=True)
    fiches, rapport = {}, ['# Récupération TMDB', '']
    for line in open(src, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = [p.strip() for p in line.split('|')]
        titre, extra = parts[0], (parts[1] if len(parts) > 1 else '')
        if extra.startswith('tmdb:'):
            mid = int(extra[5:])
        else:
            q = {'query': titre, 'language': 'fr-FR', 'region': 'FR', 'include_adult': 'false'}
            if extra.isdigit():
                q['year'] = extra
            res = get('/search/movie', **q).get('results', [])
            if not res:
                rapport.append(f'- ❌ **{titre}** : introuvable (ajouter « | tmdb:ID » dans films.txt)')
                continue
            res.sort(key=lambda r: (r.get('release_date', '') < '2025', -r.get('popularity', 0)))
            mid = res[0]['id']
        m = get(f'/movie/{mid}', language='fr-FR', append_to_response='credits,release_dates,images',
                include_image_language='fr,null,en')
        crew = m.get('credits', {}).get('crew', [])
        cast = m.get('credits', {}).get('cast', [])
        sortie_fr = ''
        for rd in m.get('release_dates', {}).get('results', []):
            if rd['iso_3166_1'] == 'FR':
                ds = sorted(x['release_date'][:10] for x in rd['release_dates'] if x.get('type') in (2, 3))
                sortie_fr = ds[0] if ds else ''
        s = slug(titre)
        fiche = {
            'titre': m.get('title') or titre, 'titre_original': m.get('original_title'),
            'tmdb_id': mid, 'duree': duree(m.get('runtime') or 0),
            'pays': ', '.join(c['name'] for c in m.get('production_countries', [])),
            'genre': ', '.join(g['name'] for g in m.get('genres', [])),
            'realisateur': ', '.join(c['name'] for c in crew if c.get('job') == 'Director'),
            'avec': ', '.join(c['name'] for c in cast[:3]),
            'sortie_fr': sortie_fr, 'resume_tmdb': m.get('overview', ''),
            'affiche': None, 'photos': [],
        }
        posters = m.get('images', {}).get('posters', [])
        posters.sort(key=lambda p: (p.get('iso_639_1') != 'fr', -p.get('vote_average', 0), -p.get('width', 0)))
        pp = posters[0]['file_path'] if posters else m.get('poster_path')
        if pp:
            fn = f'{s} affiche.jpg'; download(pp, os.path.join(out, fn)); fiche['affiche'] = fn
            w = posters[0].get('width') if posters else '?'
            fiche['affiche_px'] = w
        backs = [b for b in m.get('images', {}).get('backdrops', []) if b.get('iso_639_1') in (None, '')]
        backs.sort(key=lambda b: (-b.get('vote_average', 0), -b.get('width', 0)))
        seen = []
        for b in backs:
            if len(fiche['photos']) >= 3:
                break
            fn = f"{s} photo {len(fiche['photos']) + 1}.jpg"
            dest = os.path.join(out, fn); download(b['file_path'], dest)
            sig = empreinte(dest)
            if any(sum(x != y for x, y in zip(sig, o)) < 6 for o in seen):   # doublon (même image, autre version)
                os.remove(dest); continue
            seen.append(sig); fiche['photos'].append(fn)
        fiches[s] = fiche
        warn = [] if fiche['resume_tmdb'] else ['pas de résumé FR']
        if not fiche['affiche']: warn.append("pas d'affiche")
        elif (fiche.get('affiche_px') or 0) < 1000: warn.append(f"affiche trop petite pour l'impression ({fiche.get('affiche_px')} px) → à fournir")
        if not fiche['photos']: warn.append('pas de photo sans texte')
        rapport.append(f"- {'⚠️' if warn else '✅'} **{titre}** → {fiche['titre']} (TMDB {mid}, sortie FR {sortie_fr or '?'}, "
                       f"{fiche['duree'] or '?'}, affiche {fiche.get('affiche_px', '?')} px, {len(fiche['photos'])} photo(s))"
                       + (f" — {', '.join(warn)}" if warn else ''))
    json.dump(fiches, open(os.path.join(out, 'fiches.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(os.path.join(out, 'RAPPORT.md'), 'w', encoding='utf-8').write('\n'.join(rapport) + '\n')
    print('\n'.join(rapport))


if __name__ == '__main__':
    for f in sys.argv[1:]:
        run(f)
