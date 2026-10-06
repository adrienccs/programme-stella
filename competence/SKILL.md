---
name: "programme-stella"
description: "Produire le programme mensuel 3 volets (InDesign/IDML) du cinéma Le Stella à Moncoutant-sur-Sèvre et son affiche A3, à partir de sa grille horaire, avec le kit du dépôt GitHub adrienccs/programme-stella."
---

# Programme mensuel du Stella (Moncoutant-sur-Sèvre) + affiche A3

Adrien (Copy Color Service, Bressuire) réalise chaque mois le programme papier du cinéma **Le Stella** à
Moncoutant-sur-Sèvre (3 volets A4 italienne, fonds perdus 3 mm, charte **orange #F59042 / noir**) ET l'affiche A3 du même mois.
Projet distinct : ne jamais modifier les dépôts des autres cinémas (7e Art, Commynes, Belle épine, CinéKids) depuis ce projet.
Le client est tatillon : respecter à la lettre les codes de mise en page de PROCEDURE.md.
Livrables : TOUJOURS des dossiers d'assemblage complets, UN zip par document (< 30 Mo) — IDML + Links + Document fonts
+ « Relier les liens.jsx » + aperçus.

## 🔒 Maquette

v01 livrée le 06/10/2026. Dès qu'Adrien la valide : `verif_maquette.py figer` (programme et affiche), pousser `reference/`.
Ensuite la mise en page doit être IDENTIQUE d'un mois à l'autre ; seul le contenu change :
- Ne JAMAIS modifier `cinemas/stella.json`, `moteur/*.py`, `outils/logo_cinema.py`, `outils/bloc_cinekids.py` pour un
  nouveau mois : tout passe par `mois/stella-AAAA-MM/mois.json` et les images du mois.
- Avant CHAQUE livraison (maquette figée) : `python3 outils/verif_maquette.py verifier --idml OUT/_idml --nom programme`
  et `… --idml OUT_AFF/_idml --nom affiche` → « identique à la référence validée » obligatoire.

## 1. Récupérer le kit (toujours en premier)

1. `add_repo` owner `adrienccs`, repo `programme-stella`, access `push`, puis
   `git clone --depth 1 https://github.com/adrienccs/programme-stella /home/claude/programme-stella`.
2. Lire `PROCEDURE.md` EN ENTIER (surtout « Spécificités du Stella », « Affiche A3 (Stella) », « MAQUETTE »).
3. Modèle du mois : `mois/stella-2026-10/mois.json`.
4. Dépendances : `pip install --break-system-packages uharfbuzz cairosvg fonttools`.

## 2. Entrées du mois

- Grille du Stella (PDF « Programme du Stella… ») : 4 semaines Mer→Mar, LUNDI FERMÉ (`"fermes": [5]`). Rendre à 250 dpi
  et ZOOMER sur chaque grille pour lire les styles. Relire deux fois.
- Codes (légende de l'original) : `r` rouge = 4,50 € pour tous (en rouge même si le cinéma est orange) · `s` souligné =
  goûter Super U (`rs`) · italique = courts-métrages (`"court": true`) · `v` bleu ciel = Ciné à 1 € le jeudi soir
  (Monsévriens) · `b`/`bs` orange foncé = Ciné famille (2 € Monsévriens) · avant-premières = case fusionnée
  « Avant-première » (`fusion` {de, a}) sur les jours vides avant la séance. Signaler à Adrien toute incohérence de l'original
  (titres mal orthographiés, ex. « Docubo » → Ducobu ; durées différentes des autres cinémas : la grille du Stella fait foi).
- Tarifs et abonnements = ceux de Cerizay (déjà dans `cinemas/stella.json`).
- Film inconnu (ex. Ciné-Ado sans titre) : fiche + ligne de grille + bandeau « Film en attente ».
- Films déjà traités au 7e Art le même mois : on peut COPIER (jamais modifier) ses fiches/affiches depuis
  `adrienccs/programme-7emeArt` (clone en lecture), en renommant le préfixe 7EA → STE.
- **TMDB automatique** : écrire `mois/stella-AAAA-MM/films.txt`, committer, pousser ; si l'Action ne part pas :
  `gh api -X POST repos/adrienccs/programme-stella/actions/workflows/tmdb.yml/dispatches -f ref=main -f 'inputs[dossier]=mois/stella-AAAA-MM'`,
  attendre ~1 min, `git pull --rebase`, lire `tmdb/RAPPORT.md`. Titre introuvable → recherche web.
- Demander à Adrien UNIQUEMENT ce qui manque (affiches < 1000 px utilisées en grand, absentes, en anglais/teaser).

## 3. Construire le programme

1. Images → `mois/…/images/` préfixe « STE » (`prep_images.py normalise`, ≤ 2400 px). Bandeaux d'événements :
   `prep_images.py bandeau SRC "STE bandeau xxx.jpg" --haut-mm 31.5` (+ version affiche 134,5 × 26 mm).
2. `mois.json` : `semaines` (4, chacune `"fermes": [5]`), `fiches` 1 à 4 ; semaine à 9-10 lignes → `"h_ligne": 18` et
   3 fiches max (sinon affiches réduites partout et textes qui se chevauchent) ; priorités : films d'une seule semaine,
   gros films, film en attente ; chaque gros film résumé au moins une fois dans le mois si la place le permet (lister à
   Adrien les ATTENTION restantes) ; résumés courts (2-3 lignes), casting 2-3 noms ; `prochainement` = 3 « évènements ce
   mois-ci » (ordre chronologique) ; couverture = 6 affiches de films diffusés.
3. Vacances scolaires : bloc Ciné-Kids avec `outils/bloc_cinekids.py … --couleur "#F59042"` :
   programme `--largeur 89.7 --hauteur 31.5` → `"visuel_programme"` ; affiche colonne (taille affichée par affiche.py,
   121,4 × 111,5) → `"visuel_affiche_colonne"` ; + `"vedette_affiche": true`.
4. `python3 moteur/programme.py --kit . --cinema cinemas/stella.json --mois mois/stella-AAAA-MM/mois.json --images mois/stella-AAAA-MM/images --out OUT`
   (lire les `ATTENTION :`).
5. `RENDER_FONTS=assets/polices RENDER_LINKS="OUT/<nom>/Links:assets/cinemas/stella:assets/communs" python3 moteur/render.py OUT/_idml OUT/apercu`
   → `OVERSET:` hors `uc46c`, `ud404`, `ud41d` = raccourcir le texte du mois ; regarder les 2 PNG (soulignés, italiques,
   couleurs, cases fusionnées, lundi grisé, pas de chevauchement de fiches).
6. Maquette figée : `python3 outils/verif_maquette.py verifier --idml OUT/_idml --nom programme`.
7. `python3 moteur/assembler.py --kit . --cinema cinemas/stella.json --sortie OUT --nom "<nom_fichier>" --images mois/stella-AAAA-MM/images --version vNN --apercus OUT/apercu`
   → un seul zip ; vérifier que tous les `LinkResourceURI` commencent par `file:/`.

## 3b. Affiche A3 (avec chaque programme)

`python3 moteur/affiche.py --kit . --cinema cinemas/stella.json --mois mois/stella-AAAA-MM/mois.json --images mois/stella-AAAA-MM/images --out OUT_AFF`,
render.py (RENDER_LINKS avec `assets/cinemas/stella:assets/communs-hd:assets/communs`), `verif_maquette.py verifier --nom affiche`
(maquette figée), assembler.py `--nom "AFFICHE A3 STELLA …"`.
Disposition Argentonnay : bloc Ciné-Kids + événements à gauche, 4 grilles à droite sans bandeau semaine.

## 4. Livrer et sauvegarder

- Envoyer les zips (jamais un IDML seul). Rappel : ouvrir l'IDML, Enregistrer sous en .indd dans le dossier, lancer
  « Relier les liens.jsx ».
- Copier IDML + aperçus dans `livrables/stella-AAAA-MM/` (+ VERSION.txt), supprimer les photos non utilisées,
  `git add -A && git commit && git push`.
- Ton avec Adrien : français, direct, tutoiement.
