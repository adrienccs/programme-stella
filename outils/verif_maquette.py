#!/usr/bin/env python3
"""
Verrou de mise en page (demande d'Adrien, 06/10/2026) : la maquette doit être IDENTIQUE d'un mois à l'autre.

  # figer la référence (seulement quand Adrien valide un changement de maquette) :
  python3 outils/verif_maquette.py figer   --idml SORTIE/_idml        --nom programme
  python3 outils/verif_maquette.py figer   --idml SORTIE_AFF/_idml    --nom affiche
  # contrôler un nouveau mois (OBLIGATOIRE avant livraison) :
  python3 outils/verif_maquette.py verifier --idml SORTIE/_idml       --nom programme
  python3 outils/verif_maquette.py verifier --idml SORTIE_AFF/_idml   --nom affiche

Compare la position/taille (tolérance 0,3 mm) de tous les blocs FIXES du gabarit (logo, fauteuil, bandeau des dates,
couverture, remerciements, tarifs, bandeau bas, adresse, colonnes, légende…), ainsi que l'empreinte des réglages
(fiche cinéma + moteur). Les blocs qui dépendent du contenu du mois (fiches, grilles, bandeaux d'événements,
affiches) sont ignorés. Toute différence = la maquette a bougé → corriger, ou faire valider par Adrien puis « figer ».
"""
import argparse, glob, hashlib, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'moteur'))
from lxml import etree
from idmllib import Doc, ITEMS

KIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
REF = os.path.join(KIT, 'reference')
# blocs qui varient avec le contenu du mois (identifiants du gabarit) → non contrôlés
VARIABLES = {
    'programme': {'uc035', 'ud126', 'ud145', 'ud1a6', 'uc043', 'ud157', 'ud170', 'ud1a7', 'uc054', 'ud1cc', 'ud200', 'ud1e5',
                  'ud24f', 'ud109', 'ubdf0', 'ud0c7', 'ud0e9'},
    'affiche': {'uc035', 'ud126', 'ud145', 'ud1a6', 'uc043', 'ud157', 'ud170', 'ud1a7', 'uc054', 'ud1cc', 'ud200', 'ud1e5',
                'ud24f', 'ud109', 'ubdf0', 'ud0e9', 'uc37d', 'uc380', 'uc89e', 'uc8b5', 'uc8c1', 'uc8cd'},
}
REGLAGES = ['cinemas/stella.json', 'moteur/programme.py', 'moteur/affiche.py', 'moteur/grid.py', 'moteur/idmllib.py',
            'moteur/assembler.py', 'moteur/adapt.py', 'outils/logo_cinema.py', 'outils/bloc_cinekids.py']


def empreinte_reglages():
    h = {}
    for f in REGLAGES:
        p = os.path.join(KIT, f)
        if os.path.exists(p):
            h[f] = hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]
    return h


def blocs(idml, nom):
    d = Doc(idml)
    out = {}
    for sp in d.spreads.values():
        for el in sp.getroot().iter(*ITEMS):
            sid = el.get('Self') or ''
            if sid.startswith('cmy') or sid in VARIABLES[nom]:      # copies générées / blocs du mois
                continue
            par = el.getparent()
            if par is not None and par.tag not in ('Spread', 'Group'):
                continue
            try:
                x0, y0, x1, y1 = d.bbox(el)
            except Exception:
                continue
            out[sid] = [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['figer', 'verifier'])
    ap.add_argument('--idml', required=True); ap.add_argument('--nom', required=True, choices=['programme', 'affiche'])
    ap.add_argument('--tol', type=float, default=0.3)
    a = ap.parse_args()
    ref_p = os.path.join(REF, f'maquette-{a.nom}.json')
    cur = {'blocs': blocs(a.idml, a.nom), 'reglages': empreinte_reglages()}
    if a.action == 'figer':
        os.makedirs(REF, exist_ok=True)
        json.dump(cur, open(ref_p, 'w'), indent=1, sort_keys=True)
        print(f'Référence figée : {ref_p} ({len(cur["blocs"])} blocs fixes)')
        return
    ref = json.load(open(ref_p))
    diffs = []
    for sid, b in ref['blocs'].items():
        c = cur['blocs'].get(sid)
        if c is None:
            diffs.append(f'bloc {sid} ABSENT')
        elif max(abs(u - v) for u, v in zip(b, c)) > a.tol:
            diffs.append(f'bloc {sid} déplacé/redimensionné : {b} → {c}')
    for sid in cur['blocs']:
        if sid not in ref['blocs']:
            diffs.append(f'bloc {sid} NOUVEAU')
    for f, h in ref['reglages'].items():
        if cur['reglages'].get(f) != h:
            diffs.append(f'réglage modifié depuis la référence : {f}')
    if diffs:
        print(f'MAQUETTE {a.nom.upper()} : {len(diffs)} différence(s) avec la référence validée')
        for x in diffs:
            print('  -', x)
        sys.exit(1)
    print(f'MAQUETTE {a.nom.upper()} : identique à la référence validée ({len(ref["blocs"])} blocs fixes contrôlés)')


if __name__ == '__main__':
    main()
