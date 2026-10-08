#!/usr/bin/env python3
"""
Contrôle de début de conversation, côté cinéma (copié dans chaque dépôt par programme-commun/outils/synchro.py) :

  git clone --depth 1 https://github.com/adrienccs/programme-commun /home/claude/programme-commun
  python3 commun/verif.py /home/claude/programme-commun

OK → la copie locale du code commun (légendes, bandeau…) est à jour.
À SYNCHRONISER → NE PAS construire : prévenir Adrien (un élément commun a changé et ce cinéma n'a pas encore
été mis à jour ; la mise à jour se fait depuis programme-commun, puis on refige le verrou du cinéma).
"""
import hashlib, os, sys

ICI = os.path.dirname(os.path.abspath(__file__))


def empreinte(dossier):
    h = hashlib.sha256()
    for root, dirs, files in os.walk(dossier):
        dirs[:] = sorted(x for x in dirs if x != '__pycache__')
        for f in sorted(files):
            if f == 'VERSION.txt' or f.endswith('.pyc'):
                continue
            p = os.path.join(root, f)
            h.update(os.path.relpath(p, dossier).encode())
            h.update(open(p, 'rb').read())
    return h.hexdigest()[:16]


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    ref = os.path.join(sys.argv[1], 'commun')
    a, b = empreinte(ref), empreinte(ICI)
    if a == b:
        print(f'COMMUN : OK ({b})')
    else:
        print(f'COMMUN : À SYNCHRONISER (programme-commun {a}, copie locale {b}) → ne pas construire, prévenir Adrien')
        sys.exit(1)
