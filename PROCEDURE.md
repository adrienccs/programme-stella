# Programme du cinéma Le Stella (Moncoutant-sur-Sèvre) — Copy Color Service

Programme mensuel du cinéma **Le Stella** à Moncoutant-sur-Sèvre (maquette 3 volets reprise du 7e Art / Fauteuil Rouge,
A4 italienne, fonds perdus 3 mm, charte **orange #F59042 / noir**) + affiche A3 du même mois.
Kit dérivé de `adrienccs/programme-7emeArt` (06/10/2026) — ne JAMAIS modifier le dépôt du 7e Art (ni des autres cinémas) depuis ici.
Ce dépôt ne concerne **que le Stella**. Le kit génère un **IDML** + **Links** + **aperçus**, livrés en dossier d'assemblage zippé.

## Organisation

```
kit/
  PROCEDURE.md                 ← ce fichier
  moteur/                      ← scripts
    programme.py               ← construit l'IDML à partir des 2 fiches JSON
    grid.py                    ← grilles horaires
    idmllib.py                 ← outils IDML (géométrie, textes, images)
    render.py                  ← aperçu approximatif + détection des textes en excès
    prep_images.py             ← bandeaux événements, conversion d'images
  cinemas/<id>.json            ← fiche fixe par cinéma
  mois/<id>-AAAA-MM/mois.json  ← contenu de chaque mois
  mois/<id>-AAAA-MM/images/    ← affiches, photos et bandeaux du mois
  livrables/<id>-AAAA-MM/      ← IDML livré + aperçus (archive)
  assets/                      ← gabarit, liens d'origine, polices (aperçu), logos
    gabarit/GABARIT_3_VOLETS.idml
    communs/                   ← liens d'origine de la maquette (partenaires, projecteurs, fauteuil…)
    polices/                   ← polices pour l'aperçu uniquement
    cinemas/<id>/              ← logo, fauteuil recoloré, etc.
```

Côté Mac, les liens pointent vers `dossier_liens_mac` (fiche cinéma) : on dépose l'IDML et le contenu
de `Links` dans ce dossier → tout se relie seul. Sinon : panneau Liens → « Relier à un dossier ».

## Affiches de films : jamais coupées (depuis le 07/10/2026)

Les affiches de films (fiches, couverture, affiche A3) sont adaptées automatiquement au format de leur cadre par
`moteur/adapt.py` (même module que les autres cinémas) : dès que le format diffère (> 0,5 %), « méthode D » validée
par Adrien — affiche ENTIÈRE, les bandes manquantes complétées en prolongeant ses propres bords, floutés ; jamais de
déformation ni de recadrage. Au-delà de 5 % d'écart (affiches TMDB en 2:3), le moteur affiche
`ATTENTION : Affiche « … » complétée` → le signaler à Adrien (remplissage génératif Photoshop possible).
Les fichiers « <nom> [cadre 0750].jpg » sont créés dans `images/` du mois : les committer.
(`cadrage_affiche` n'a plus d'effet visible : l'affiche entière tient dans le cadre.)

## Dépôt

Tout le kit vit dans le dépôt GitHub **privé** `adrienccs/programme-stella` (Le Stella uniquement).
- Début de séance : `git clone` du dépôt (ou `git pull`).
- Fin de séance : `git add -A && git commit -m "<cinéma> <mois> : …" && git push`
  (fiche mois, images du mois, livrable IDML + aperçus, et toute évolution du moteur).
Le dépôt doit rester privé (polices commerciales dans `assets/polices`).

## Déroulé d'un mois

1. **Entrées d'Adrien** : la grille horaire (Excel, PDF, photo…), les événements (avant-premières,
   soirées, « prochainement »), et les affiches HD + 2-3 photos de films.
2. **Infos films** (recherche web) : réalisateur, casting (3 noms max), date de sortie, durée, pays,
   genre, résumé. Signaler toute info incertaine à Adrien.
2b. **TMDB automatique** (GitHub Actions, clé dans le secret `TMDB_API_KEY`) : écrire
   `mois/<id>-AAAA-MM/films.txt` (un titre par ligne ; « Titre | 2026 » ou « Titre | tmdb:ID » si ambigu),
   committer + pousser, attendre ~1 min (`git fetch` jusqu'au commit « TMDB : … »), puis `git pull`.
   Résultat dans `mois/<id>-AAAA-MM/tmdb/` : fiches.json (réal., casting, durée, pays, genre, sortie FR,
   résumé FR), « <film> affiche.jpg », « <film> photo 1..3.jpg » (sans texte, souvent 4K), RAPPORT.md.
   ⚠️ Les DURÉES et HORAIRES font foi d'après la grille du cinéma, pas TMDB. Résumés TMDB à raccourcir.
   Les affiches < 1000 px (signalées dans RAPPORT.md) ou en version teaser → demander la HD à Adrien.
   Copier/normaliser les images retenues dans images/ avec le préfixe STE.
3. **Liste d'images** : envoyer à Adrien la liste exacte des visuels manquants (affiches HD, photos
   pour les images de remplissage, visuels événements « sans texte »).
4. **Images** : `prep_images.py normalise` (webp → jpg 72 ppi) ; bandeaux événements :
   `prep_images.py bandeau photo.jpg "XXX bandeau nom.jpg" --haut-mm 35 --x .. --y ..`
   (le visage/sujet doit tomber dans la zone claire, au centre-droit). Préfixe des fichiers = `prefixe_images`.
5. **Fiche mois** `mois/<id>-AAAA-MM/mois.json` (modèle : `mois/stella-2026-10/mois.json`).
6. **Construction** :
   ```
   python3 moteur/programme.py --kit KIT --cinema cinemas/<id>.json --mois mois/<id>-AAAA-MM/mois.json \
          --images mois/<id>-AAAA-MM/images --out SORTIE
   ```
7. **Contrôle** (obligatoire) :
   ```
   RENDER_FONTS=KIT/assets/polices RENDER_LINKS="SORTIE/<nom>/Links:KIT/assets/cinemas/<id>:KIT/assets/communs" \
     python3 moteur/render.py SORTIE/_idml SORTIE/apercu
   ```
   - lire la ligne `OVERSET:` → tout cadre listé (hors `uc46c`, `ud404`, `ud41d`, faux positifs connus)
     = texte qui déborde : raccourcir le résumé ou le casting dans la fiche mois, relancer ;
   - regarder les 2 PNG (apercu-1 = intérieur, apercu-2 = extérieur).
     L'aperçu ne trace pas les courbes (coins arrondis en pans coupés) ni les marges de cellules : normal.
8. **Livraison** — toujours un dossier d'assemblage complet :
   ```
   python3 moteur/assembler.py --kit . --cinema cinemas/<id>.json --sortie SORTIE --nom "<nom_fichier>" \
          --images mois/<id>-AAAA-MM/images --version vNN --apercus SORTIE/apercu
   ```
   → `SORTIE/<nom> vNN - ASSEMBLAGE.zip` : IDML + Links (noms sans accents) + Document fonts +
   « Relier les liens.jsx » + LISEZ-MOI + aperçus. À lancer APRÈS render.py (il réécrit les liens de `_idml`).
   Les liens pointent vers `dossier_assemblage_mac` (fiche cinéma) si renseigné ; sinon le script .jsx
   relie tout en un clic. Ne jamais livrer un IDML seul (Adrien devait relier les images une par une).
   Puis committer et pousser le mois (fiche, images, livrable).
## Règles de mise en page (validées avec Adrien, oct. 2026)

- 1 volet = 1 week-end : intérieur gauche, milieu, droite, puis extérieur gauche. 1 à 4 films par volet.
- Chaque volet : bandeau couleur centré « week-end du … » (≤ 32 caractères, sinon `titre_volet` abrégé),
  fiches (affiche 27×36 mm, 3 mm d'air entre affiches), image de remplissage, grille en bas.
- Grilles : films triés automatiquement dans l'ORDRE DE DIFFUSION (1re séance du week-end) ; les fiches
  résumés aussi, sauf ordre imposé par `"ordre_fiches": [clés]` dans le week-end. Tarif d'un événement
  spécial : à l'intérieur seulement, pas sur l'encart de couverture.
- Grilles : ligne des jours en couleur avec « HORAIRES », titre du film ligne 1 / durée ligne 2,
  **alternance de lignes blanc / gris clair** (gris 211 à 45 %) — demande client du 03/10/2026 —,
  heures en 77 Bold Condensed, bas arrondi (tracé en U d'origine).
- Événement spécial : `"position": "haut"` = bloc AVANT les résumés du volet (logique soirée + résumé du film),
  avec son tarif dans `ligne_grasse`.
- Événement spécial (ex. soirée anniversaire) : bandeau noir + bandeau photo + cadre couleur au premier
  plan dans son volet, **et** encart sur la couverture (calque « affiches films »).
- Prochainement (0 à 3) : extérieur milieu, cadre gris + bandeaux photo, dates en gros. La hauteur des bandeaux
  s'adapte au nombre (2 → 44 mm, 3 → 28,7 mm) : le moteur affiche la hauteur à utiliser pour `prep_images.py bandeau`.
- Volet central (retour client 03/10/2026) : logos des remerciements réduits (72 %), cadre serré, tarifs et
  abonnements sans espaces blancs entre paragraphes, calés vers le bas, mention Copy Color au pied de page.
  Zone événements = 15 → 113,5 mm (variable d'env. PRO_BOTTOM pour ajuster) ; 3 bandeaux = 31,5 mm chacun.
- Photos d'événements : on peut les teinter dans l'esprit de l'événement (ex. Octobre Rose → duotone rose/violet).
- Couverture (retour client 03/10/2026) : logo agrandi, bandeau des dates plus haut et texte 12 pt,
  fauteuil remonté, icônes réseaux centrées sur le bloc adresse. Pas de film non diffusé en couverture.
- Bandeau bas : « Toutes les informations et réservations sur cinemalestella.com ».
- Abonnements : citer toutes les salles (Bressuire, Argentonnay, Cerizay, Moncoutant, La Châtaigneraie,
  La Tranche-sur-Mer, Jard-sur-Mer, Talmont-Saint-Hilaire) — à simplifier quand le groupe aura changé de nom.
- Mention : « SCIC Cinémas Bocage » (avec un s).
- Couleur du cinéma : remplace tous les rouges/verts du gabarit (nuancier renommé).
- Polices absentes du Mac d'Adrien (Helvetica Neue 37 Thin / 47 Light / 57 Condensed) → 67 Medium Condensed.
- Fonds perdus : le volet couverture (fond noir, projecteurs, fauteuil) est prolongé à 300,6 mm (3 mm + marge) ;
  contrôle automatique possible : aucun bloc plein ne doit s'arrêter entre le bord de coupe et le fond perdu.
- Le cadre magenta de repère du gabarit (couverture, calque GABARIT) est supprimé : il ne doit jamais apparaître.
- Résumés : courts (4-5 lignes max), casting 2-3 noms ; mieux vaut couper que déborder.

## Fiche mois : champs

- `nom_fichier`, `periode` {du, au_num, au_exposant ("er" pour le 1er), au_mois, annee}
- `films` {clé: {titre, duree, pays, resume, realisateur, sortie, avec|null, genre, affiche, grille?}}
  `grille` = nom dans la grille (texte, ou [ligne1, ligne2] pour forcer la coupure)
- `weekends` [{titre, titre_volet?, jours[7] (Mer→Mar), films: [[clé, {"jour 0-6": ["20h30", …]}]],
  image_remplissage? {image, cadrage [x,y]}}]
- `evenement_special`? {volet, bandeau, image, surtitre, titre, ligne, ligne_grasse, date{jour,num,mois,heure}}
- `prochainement` [≤3 × {image, surtitre, titre, ligne, ligne_grasse, date{…, exposant?}}]
- `couverture` {affiches [≤6 : grande gauche, grande droite, 4 petites], encart? {surtitre, titre, ligne}}

## Fiche cinéma : champs

`id, nom, ville, couleur (#hex), nom_couleur, logo, fauteuil?, dossier_liens_mac, prefixe_images,
titre_prochainement, slogan, mention_gestion, contact[3 lignes], bandeau_bas[texte, texte gras],
tarifs[…], abonnements[…]` — éléments de tarifs : `{titre}`, `{ligne, prix, detail?}`, `{sous}`,
`{texte}`, `{note}`, `{fort}`, `{centre}`.

## Spécificités du Stella (1er mois : 14 oct. – 10 nov. 2026)

Mêmes règles que le 7e Art (1 volet = 1 SEMAINE mer→mar, clé `semaines`, fiches triées par 1re séance, image de
remplissage, légende 2 lignes, 3 bandeaux « évènements ce mois-ci », remerciements pleine largeur, affiche A3 en colonnes).
Différences propres au Stella :
- Couleur du cinéma **#F59042** (orange) : bandeaux, en-têtes de grille, nuancier « Orange Stella ». Préfixe des images : `STE`.
- **Séances « r » (4,50 €) en ROUGE** et non dans la couleur du cinéma : nuance `rouge` dans `couleurs_grille`
  (moteur : `grid.ROUGE`). Codes de séance (légende de l'original du Stella) :
  `r` rouge = 4,50 € pour tous · `s` souligné = goûter Super U (séance goûter = `rs`) · `i` italique = courts-métrages
  (auto avec `"court": true`) · `v` **bleu ciel** (nuance « Grille violet » = #1BA1E2) = Ciné à 1 € le JEUDI soir
  (Monsévriens, justificatif) · `b` **orange foncé** (nuance « Grille bleu » = #E8650A) = Ciné famille (2 € Monsévriens),
  souligné si goûter (`bs`).
- **Lundi fermé** : `"fermes": [5]` sur chaque semaine (colonne grisée).
- Avant-premières : case fusionnée « Avant-première » (`fusion` {de, a}) sur les jours vides avant la séance, comme au 7e Art.
- Une semaine peut avoir jusqu’à **10 lignes** de grille (limite relevée pour le Stella) → `"h_ligne": 18` et 3 fiches ; à 9 lignes, `"h_ligne": 17` permet 4 fiches avec des résumés de 2 lignes (validé v02).
- Les films du programme Ciné-Kids peuvent ne pas avoir de fiche (programme dédié, validé par Adrien le 06/10/2026).
- Hauteur des affiches de fiche = la plus petite place du mois : éviter 4 fiches dans une semaine à 9-10 lignes
  (sinon « fiches serrées » et chevauchement des textes). Priorités des fiches : films qui ne passent qu'une semaine,
  gros films, film en attente (Ciné-Ado) ; les avant-premières jeunesse/courts n'ont pas de fiche si la place manque
  (le moteur l'affiche en ATTENTION : à signaler à Adrien).
- Film pas encore connu (ex. Ciné-Ado) : JAMAIS « en attente » (retour 07/10/2026) → on brode : « Ciné-Ado : film surprise »,
  visuel « STE cine ado film surprise.jpg » (point d'interrogation orange, projecteurs, confettis), fiche au ton ado,
  ligne de grille « Film surprise · Ciné-Ado », bandeau « Film surprise — dévoilé très bientôt ». Remplacer dès que le titre arrive.
- Affiche de film au format 2:3 dont le titre est coupé (cadres 3:4 → ~6 % rognés en haut et en bas) : créer
  « STE <film> entiere.jpg » = affiche élargie à 0,76 de ratio avec ses bords prolongés en flou assombri, puis
  `"affiche"` + `"cadrage_affiche": [0.5, 0.5]` dans le film (et dans `couverture.affiches`). Ex. Heart of the Beast (07/10/2026).
- Couverture : Facebook SEUL (`reseaux_visibles` = [0, 0.11] du fichier RÉSEAUX.ai, recentré — comme Cerizay), retour 08/10/2026.
- Titres des grilles (retour client 08/10/2026, `titres_grille_entiers: true`) : JAMAIS de titre coupé en « gros + petit ».
  Titre entier sur UNE ligne, resserré au besoin (chasse ≥ 80 %, `grid.TITRE_CHASSE_MIN`) ; sinon 2 lignes coupées au plus
  équilibré, la 2e partie à la MÊME taille et dans le même style, puis « · durée » en petit (ex. « Ducobu et le fantôme /
  de St-Potache · 1h30 »). Sur l'affiche, mesure faite au corps final (`affiche_corps_grille`). Les tableaux `grille` en liste
  dans mois.json ne servent plus qu'à défaut.
- Logo : `outils/logo_cinema.py "Le Stella" "Moncoutant-sur-Sèvre" "#F59042" "assets/cinemas/stella/STE logo le stella"`.
- Fauteuil : `STE fauteuil orange.png` (fauteuil rouge du 7e Art recoloré en orange).
- Partenaires : ceux du 7e Art, logo ville de Cerizay remplacé par celui de Moncoutant-sur-Sèvre (`STE logo ville moncoutant.png`).
- Contact (3 lignes) : « Cinéma « Le Stella » - 11 rue Jeanne d’Arc » / « 79320 Moncoutant-sur-Sèvre » / « 05 49 72 81 28 ».
- Site du bandeau bas : cinemalestella.com. Mention : Cinéma géré et animé par la SCIC Cinémas Bocage.
- Tarifs et abonnements : MÊME BLOC que Cerizay et La Châtaigneraie (retour 07/10/2026) : titre « TARIFS 2026 MONCOUTANT »,
  * sur les tarifs avec justificatif + « * Justificatifs obligatoires », « Valables à… » sous « ABONNEMENTS 2026 »,
  « (Places valables 1 an) » sous les formules. Contremarques : « Cinéchèques, ANCV et CCU acceptés » (PAS Fleury Michon au Stella).
  Affiche : `affiche_tarifs` = 0,97 (débordement à partir de 1,08 dans l'aperçu → garder ≈ 4 mm de marge, InDesign compose
  un peu plus haut que l'aperçu).
- Déclinaisons de l'orange (retour 07/10/2026, comme Cerizay/La Châtaigneraie) : les gris du gabarit prennent une teinte orange
  (`declinaisons` : fond titre de fiche #FEF7F1, barre durée/pays #FCDDC4, alternance des lignes de grille #FBD3B3, aussi sur l'affiche).
- Remerciements : logo Région Nouvelle-Aquitaine à la place de Poitou-Charentes Cinéma (`remplacer_logos`,
  `STE logo region nouvelle-aquitaine.png`) ; logos réduits (`remerciements_echelle` 0,82) pour faire place au logo de Moncoutant.
- Ciné-Kids : `outils/bloc_cinekids.py … --couleur "#F59042"` (programme 89,7 × 31,5 ; affiche colonne 121,4 × 121,0).
- Affiche A3 (retour Adrien 06/10/2026, v03) : textes des grilles à corps FIXES (`affiche_corps_grille` : titre 8,6 · durée 6,6 ·
  horaires 9,5 · jours 8 · dates 10 · cases fusionnées 8 pt), lignes de 20 pt pour toutes les semaines (`affiche_h_ligne`),
  bas des grilles à 338 mm (`affiche_bas_grilles`). Ne pas dépasser : au-delà, les cases débordent (contrôle render.py).

## Affiche A3 (Stella)

```
python3 moteur/affiche.py --kit . --cinema cinemas/stella.json --mois mois/stella-AAAA-MM/mois.json \
       --images mois/stella-AAAA-MM/images --out SORTIE_AFF
RENDER_FONTS=assets/polices RENDER_LINKS="SORTIE_AFF/<nom>/Links:assets/cinemas/stella:assets/communs-hd:assets/communs" \
  python3 moteur/render.py SORTIE_AFF/_idml SORTIE_AFF/apercu
python3 moteur/assembler.py --kit . --cinema cinemas/stella.json --sortie SORTIE_AFF \
       --nom "AFFICHE A3 STELLA …" --images mois/stella-AAAA-MM/images --version vNN --apercus SORTIE_AFF/apercu
```
Moteur repris du Commynes (`moteur/affiche.py`), adapté au format SEMAINE (déclenché par `semaines` dans mois.json) :
- en-tête projecteurs + logo + fauteuil rouge (`fauteuil_affiche` = « STE fauteuil orange.png ») + 6 affiches + bandeau dates ;
- grilles sur 2 colonnes (semaines 1-2 à gauche, 3-4 à droite), mêmes styles de séances que le programme,
  agrandies automatiquement (échelle commune aux 2 colonnes), légende unique sur 2 lignes sous les grilles ;
- rangée de 3 bandeaux « évènements ce mois-ci » (89,7 × 31,5 mm, mêmes images que le programme) ;
- tarifs | abonnements, bandeau réservations, pied de page projecteurs + adresse.
Bas des grilles réglable dans la fiche cinéma (`affiche_bas_grilles`, 321 mm) ou par `AFF_BODY_B` si les tarifs débordent.
- Retour client 06/10/2026 : PAS de bandeau « semaine » sur l'affiche (les dates de la semaine remplacent « HORAIRES »
  dans la 1re case de chaque grille ; `affiche_titres_semaine: true` pour les remettre).
- Événement à mettre en avant (ex. Ciné-Kids) : `"vedette_affiche": true` dans `prochainement` → bandeau pleine largeur
  (36 mm, titre 26 pt en couleur), les autres événements côte à côte dessous (26 mm). Images dédiées à l'affiche :
  `image_affiche_vedette` (273 × 36 mm) et `image_affiche` (134,5 × 26 mm), préparées avec
  `prep_images.py bandeau … --larg-mm 273 --haut-mm 36 --clair-de 0.52 --clair-a 0.76` (ou 134.5 × 26, clair 0.42–0.74).
- Réglages affiche dans la fiche cinéma : `affiche_bas_grilles` (328,5) et `affiche_tarifs` (1,12).


## Logo uniformisé du réseau (validé par Adrien le 06/10/2026, demande client)

Police **Advent Pro** (Google Fonts, licence OFL, fichiers dans `assets/polices-logo/`) — c'est la police du logo du Commynes.
Règle commune à TOUS les cinémas : ligne 1 = nom du cinéma en Advent Pro Light (300), blanc ; ligne 2 = ville en
minuscules avec capitale initiale (« Cerizay », « Argentonnay »), Advent Pro Bold (700), couleur du cinéma, alignée à
droite ; jamais le mot « cinéma » dans le logo ; même emplacement et même hauteur sur le programme et l'affiche.
Proportions, interlettrage et écart entre les lignes calés sur le logo du Commynes (référence) :
`python3 outils/logo_cinema.py "Le Stella" "Moncoutant-sur-Sèvre" "#F59042" "assets/cinemas/stella/STE logo le stella"`
→ SVG + PDF vectoriels + PNG HD.
- Visuel Ciné-Kids de l'affiche (V2 validée 06/10/2026) : crayons de couleur vectoriels + « CINÉ-KIDS » multicolore
  (Fredoka) + dates/goûter + photo d'un film jeunesse fondue à droite, cadre rouge. Généré par
  `python3 outils/visuel_cinekids.py --photo <photo film> --dates "du 17 oct. au 2 nov." --out "mois/…/images/STE visuel cine kids"`,
  converti en JPG, puis `"visuel_affiche": "STE visuel cine kids.jpg"` sur l'événement vedette dans mois.json.
- Bloc Ciné-Kids de l'affiche (V2 validée 06/10/2026) : crayons de couleur vectoriels + « CINÉ-KIDS » multicolore (Fredoka)
  + dates en rouge + photo d'un film jeunesse fondue à droite, cadre rouge. Généré par
  `python3 outils/bloc_cinekids.py --photo … --dates "du 17 oct. au 2 nov." --ligne1 … --ligne2 … --sortie "mois/…/images/STE bloc cine kids.png"`
  puis `"visuel_affiche": "STE bloc cine kids.png"` sur l'événement vedette dans mois.json (remplace photo + textes du bandeau).
  À refaire à chaque vacances scolaires (autres dates, autre film).
- Programme : même bloc Ciné-Kids au format bandeau (89,7 × 31,5 mm, mise en page compacte automatique) :
  `outils/bloc_cinekids.py … --largeur 89.7 --hauteur 31.5 --sortie "mois/…/images/STE bloc cine kids programme.png"`
  puis `"visuel_programme": "STE bloc cine kids programme.png"` sur l'événement dans mois.json.
- Retour Adrien 06/10/2026 (2) : programme → logos des remerciements répartis sur TOUTE la largeur du cadre
  (`remerciements_pleine_largeur: true`, `remerciements_echelle: 0.95`) ; affiche → disposition d'Argentonnay
  (`affiche_disposition: "colonnes"`) : colonne gauche = bloc Ciné-Kids vertical (`visuel_affiche_colonne`, généré par
  `outils/bloc_cinekids.py --largeur L --hauteur H` avec la taille affichée par affiche.py) + cadre « évènements » avec les
  autres bandeaux du programme ; colonne droite (`affiche_largeur_grilles`, 172 mm) = les 4 grilles + la légende.
- Bandeau bas « Toutes les informations… » (retour 06/10/2026) : le gabarit décalait le texte de -4 pt (BaselineShift) et
  le haut du bandeau passe sous le cadre des tarifs → BaselineShift 0, centrage vertical sur la partie rouge visible
  (marge haute 3,3 mm), corps `bandeau_bas_corps` (9,6 pt = max sur une ligne avec cinemale7emeart.com) ; affiche :
  `affiche_bandeau_bas_corps` (14 pt). L'aperçu (render.py) tient compte des marges intérieures des cadres de texte.

## 🔒 MAQUETTE — À FIGER APRÈS VALIDATION D'ADRIEN

v01 livrée le 06/10/2026, en attente de validation. Une fois validée : `python3 outils/verif_maquette.py figer --idml SORTIE/_idml --nom programme`
et `… --nom affiche`, pousser `reference/`, puis la maquette ne change plus d'un mois à l'autre (seul le contenu change) :
ne plus toucher à `cinemas/stella.json`, `moteur/*.py`, `outils/logo_cinema.py`, `outils/bloc_cinekids.py` ;
contrôle `verif_maquette.py verifier` obligatoire avant chaque livraison (« identique à la référence validée »).

Journal :
- 08/10/2026 (programme v08 / affiche v09, référence re-figée) : Facebook seul ; Ciné-Kids jusqu'au 1er novembre ;
  titres des grilles entiers (une ligne resserrée, ou 2 lignes de même taille).
- 07/10/2026 (programme v06 / affiche v07) : affiche Heart of the Beast entière (titre coupé).
- 07/10/2026 (programme v05 / affiche v06) : contremarques sans Fleury Michon ; tarifs affiche 0,97 ; Ciné-Ado « film surprise ».
- 07/10/2026 (programme v04 / affiche v05) : moteur re-synchronisé sur le 7e Art v18/v11 (déclinaisons, remplacer_logos,
  cadrage_affiche, coup de cœur, picto malentendants, légende par codes possibles) puis patchs Stella ré-appliqués
  (séances r en rouge, 10 lignes max, corps fixes de l'affiche) ; tarifs format Cerizay, déclinaisons orange, logo Région.
- 06/10/2026 : création du kit Stella à partir du 7e Art (v16/v09) ; séances 4,50 € en rouge ; 10 lignes de grille max.
- 06/10/2026 (affiche v03) : textes des grilles de l'affiche agrandis (corps fixes, `affiche_corps_grille`, `affiche_h_ligne` 20, bas 338 mm).
- 06/10/2026 (v02) : 4 fiches en semaine 3 grâce à `"h_ligne": 17` (semaine à 9 lignes) + résumés de 2 lignes ; films Ciné-Kids sans fiche = OK (programme Ciné-Kids dédié).
- 08/10/2026 (programme v09 / affiche v10) : bas arrondis des grilles — les coins carrés des cellules de la dernière ligne dépassaient de l'arrondi → `round_bottom` ajoute 2 caches blancs en forme de coin courbe sous le filet (comme le 7e Art et le Fauteuil Rouge), programme et affiche. Rien d'autre.
