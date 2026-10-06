---
name: "programme-7emeart"
description: "Produire le programme mensuel 3 volets (InDesign/IDML) du cinéma Le 7e Art à Cerizay et son affiche A3, à partir de sa grille horaire, avec le kit du dépôt GitHub adrienccs/programme-7emeArt."
---

# Programme mensuel du 7e Art (Cerizay) + affiche A3

Adrien (Copy Color Service, Bressuire) réalise chaque mois le programme papier du cinéma **Le 7e Art** à Cerizay
(3 volets A4 italienne, fonds perdus 3 mm, charte **rouge #D41818 / noir**) ET l'affiche A3 du même mois.
Projet distinct du Commynes : ne jamais modifier les dépôts des autres cinémas depuis ce projet.
Livrables : TOUJOURS des dossiers d'assemblage complets, UN zip par document (< 30 Mo) — IDML + Links + Document fonts
+ « Relier les liens.jsx » + aperçus.

## 🔒 Maquette verrouillée (validée le 06/10/2026 : programme v16, affiche v09)

La mise en page doit être IDENTIQUE d'un mois à l'autre ; seul le contenu change.
- Ne JAMAIS modifier `cinemas/7emeart.json`, `moteur/*.py`, `outils/logo_cinema.py`, `outils/bloc_cinekids.py` pour un
  nouveau mois : tout passe par `mois/7emeart-AAAA-MM/mois.json` et les images du mois.
- Avant CHAQUE livraison : `python3 outils/verif_maquette.py verifier --idml OUT/_idml --nom programme` et
  `… --idml OUT_AFF/_idml --nom affiche` → « identique à la référence validée » obligatoire.
- Changement de maquette seulement sur demande explicite d'Adrien → modifier, faire valider, puis `verif_maquette.py figer`
  (programme et affiche), noter dans PROCEDURE.md, pousser `reference/`.

## 1. Récupérer le kit (toujours en premier)

1. `add_repo` owner `adrienccs`, repo `programme-7emeArt`, access `push`, puis
   `git clone --depth 1 https://github.com/adrienccs/programme-7emeArt /home/claude/programme-7emeart`.
2. Lire `PROCEDURE.md` EN ENTIER (sections « Spécificités du 7e Art », « Affiche A3 », « MAQUETTE VERROUILLÉE »).
3. Modèle du mois : `mois/7emeart-2026-10/mois.json` (référence validée).

## 2. Entrées du mois

- Grille du cinéma (PDF de l'ancien programme, Excel, photo…) : 4 semaines Mer→Mar. Rendre à 220 dpi et ZOOMER sur
  chaque grille pour lire les styles. Relire deux fois. Si Adrien renvoie un fichier, vérifier qu'il diffère (`cmp`).
- Codes des séances (identiques à l'original, vérifier contre sa légende) : `r` rouge = 4,50 € · `rs` rouge souligné =
  goûter Super U (aussi 4,50 €) · italique = courts-métrages (`"court": true`) · `v` violet SEUL = Ciné à 1 € (lundi 20h30)
  · `b`/`bs` bleu = événements (Ciné-Ados, Ciné-séniors) · cases fusionnées « Avant-première » / « Séance spéciale… »
  (`fusion`) · cases grisées (`fermes` jeudi, `gris`). Signaler à Adrien toute incohérence de l'original.
- Les fiches/événements du PDF reçu peuvent dater de l'an dernier : seules les GRILLES font foi.
- **TMDB automatique** : écrire `mois/7emeart-AAAA-MM/films.txt`, committer, pousser ; si l'Action ne part pas :
  `gh api -X POST repos/adrienccs/programme-7emeArt/actions/workflows/tmdb.yml/dispatches -f ref=main -f 'inputs[dossier]=mois/7emeart-AAAA-MM'`,
  attendre ~1 min, `git pull --rebase`, lire `tmdb/RAPPORT.md`. Titre introuvable → titre exact par recherche web.
- Demander à Adrien UNIQUEMENT ce qui manque : affiches < 1000 px, absentes, en anglais/teaser, films hors TMDB.
- Commits du bot TMDB (actions@github.com) : normaux, ne jamais réécrire l'historique de main.

## 3. Construire le programme

1. Images → `mois/…/images/` préfixe « 7EA » (`prep_images.py normalise`, ≤ 2400 px). Bandeaux d'événements :
   `prep_images.py bandeau SRC "7EA bandeau xxx.jpg" --haut-mm 31.5` (cadrer un visage, regarder le résultat).
2. `mois.json` : `semaines` (4), `fiches` par semaine (1 à 4) = TOUTES les avant-premières de la semaine puis les plus
   gros films (chaque gros film résumé au moins une fois dans le mois ; le moteur trie par 1re séance et place le film
   de l'image de remplissage juste avant elle) ; pas de vide dans un volet (4e fiche, `"h_ligne": 18` si besoin) ;
   résumés courts (2-3 lignes), casting 2-3 noms ; `prochainement` = 3 « évènements ce mois-ci » ; couverture = 6 affiches.
3. Vacances scolaires : bloc Ciné-Kids « crayons + film jeunesse » avec `outils/bloc_cinekids.py` :
   programme `--largeur 89.7 --hauteur 31.5` → `"visuel_programme"` ; affiche (colonne) avec la taille affichée par
   affiche.py → `"visuel_affiche_colonne"` ; + `"vedette_affiche": true` sur cet événement.
4. `python3 moteur/programme.py --kit . --cinema cinemas/7emeart.json --mois mois/7emeart-AAAA-MM/mois.json --images mois/7emeart-AAAA-MM/images --out OUT`
   (lire les `ATTENTION :`).
5. `RENDER_FONTS=assets/polices RENDER_LINKS="OUT/<nom>/Links:assets/cinemas/7emeart:assets/communs" python3 moteur/render.py OUT/_idml OUT/apercu`
   → `OVERSET:` hors `uc46c`, `ud404`, `ud41d` = raccourcir le texte du mois ; regarder les 2 PNG (soulignés/italiques visibles).
6. `python3 outils/verif_maquette.py verifier --idml OUT/_idml --nom programme`
7. `python3 moteur/assembler.py --kit . --cinema cinemas/7emeart.json --sortie OUT --nom "<nom_fichier>" --images mois/7emeart-AAAA-MM/images --version vNN --apercus <aperçus>`
   → un seul zip ; vérifier que tous les `LinkResourceURI` commencent par `file:/`.

## 3b. Affiche A3 (avec chaque programme)

`python3 moteur/affiche.py --kit . --cinema cinemas/7emeart.json --mois mois/7emeart-AAAA-MM/mois.json --images mois/7emeart-AAAA-MM/images --out OUT_AFF`,
render.py (RENDER_LINKS + `assets/communs-hd`), `verif_maquette.py verifier --nom affiche`, assembler.py `--nom "AFFICHE A3 7E ART …"`.
Disposition Argentonnay : événements à gauche (Ciné-Kids vertical en haut), grilles à droite sans bandeau semaine.

## 4. Livrer et sauvegarder

- Envoyer les zips (jamais un IDML seul). Rappel : ouvrir l'IDML, Enregistrer sous en .indd dans le dossier, lancer
  « Relier les liens.jsx ».
- Copier IDML + aperçus dans `livrables/7emeart-AAAA-MM/` (+ VERSION.txt), supprimer les photos non utilisées,
  `git add -A && git commit && git push`.
- Ton avec Adrien : français, direct, tutoiement.
