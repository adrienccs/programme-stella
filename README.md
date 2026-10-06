# Programme du cinéma Le 7e Art (Cerizay) — Copy Color Service

Programme mensuel du cinéma **Le 7e Art** à Cerizay (maquette 3 volets reprise du Fauteuil Rouge, A4 italienne, fonds perdus 3 mm, charte rouge #D41818 / noir).
Kit dérivé de `adrienccs/programme-commynes` (oct. 2026) — ne jamais modifier ce dépôt-là depuis ici.
Ce dépôt ne concerne **que le 7e Art** : les autres cinémas sont des projets séparés, avec leur propre dépôt.
Le kit génère un **IDML** à ouvrir dans InDesign + un dossier **Links** + un **aperçu PNG/PDF**.

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

## Dépôt

Tout le kit vit dans le dépôt GitHub **privé** `adrienccs/programme-7emeart` (Le 7e Art uniquement).
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
   Copier/normaliser les images retenues dans images/ avec le préfixe 7EA.
3. **Liste d'images** : envoyer à Adrien la liste exacte des visuels manquants (affiches HD, photos
   pour les images de remplissage, visuels événements « sans texte »).
4. **Images** : `prep_images.py normalise` (webp → jpg 72 ppi) ; bandeaux événements :
   `prep_images.py bandeau photo.jpg "XXX bandeau nom.jpg" --haut-mm 35 --x .. --y ..`
   (le visage/sujet doit tomber dans la zone claire, au centre-droit). Préfixe des fichiers = `prefixe_images`.
5. **Fiche mois** `mois/<id>-AAAA-MM/mois.json` (modèle : `mois/7emeart-2026-10/mois.json`).
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
- Bandeau bas : « Toutes les informations et réservations sur cinema7emeart.com ».
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

## Spécificités du 7e Art (validées au 1er mois, oct.–nov. 2026)

- 1 volet = 1 SEMAINE complète (mercredi → mardi) : clé `semaines` dans la fiche mois (au lieu de `weekends`).
- Fiches résumé : seulement les films listés dans `"fiches": [clés]`, TOUJOURS triées automatiquement par 1re séance
  de la semaine (toutes lignes du film confondues ; ordre imposé seulement via `ordre_fiches`) (1 à 4 ; 3 si la grille a 8 lignes),
  la grille peut avoir jusqu'à 9 lignes. Les courts-métrages et avant-premières jeunesse n'ont pas de fiche.
- Image de remplissage : le film qu'elle illustre passe en DERNIÈRE fiche du volet, juste avant l'image
  (seule exception à l'ordre de diffusion ; clé `"film"` dans `image_remplissage`, sinon déduite du nom de l'image).
- Choix des fiches : 1) TOUTES les avant-premières de la semaine ont leur fiche dans cette semaine (le moteur
  avertit sinon), 2) on complète avec les plus gros films ; chaque gros film populaire a son résumé AU MOINS UNE FOIS
  dans le mois (alerte sinon ; les courts-métrages en sont dispensés) ; un film qui revient
  plusieurs semaines est présenté là où il reste de la place.
- Ordre de la grille = ordre de saisie (`ordre_grille: "saisie"` dans la fiche cinéma), comme sur la grille du cinéma.
- Lignes de grille : `{"film": clé, "seances": {"0": ["20h30", {"h": "16h00", "s": "rsi"}]}, options}`
  - styles de séance `s` = ceux du programme ORIGINAL du cinéma (validé client 05/10/2026) :
    `r` rouge = séance à 4,50 € · `s` souligné = goûter offert par Super U (une séance goûter est donc `rs`,
    elle est aussi à 4,50 €) · `i` italique (auto pour les courts) · `v` violet SEUL, jamais souligné = Ciné à 1 € (lundi 20h30)
    · `b`/`bs` bleu = événement (Ciné-Ados, Ciné-séniors).
    Relever chaque séance en ZOOMANT sur l'original, puis vérifier qu'elle colle à la légende : si l'original se
    contredit (ex. lundi 20h30 en rouge souligné, film non court en italique), appliquer la légende et le signaler ;
  - options : `etiquette` (« Ciné-Ados », « Avant-première »… ajoutée sous le titre), `fusion` {de, a, texte}
    (case fusionnée couleur : « Avant-première », « Séance spéciale… »), `gris` [jours] (cases grisées) ;
  - semaine : `fermes` [jours] = colonne grisée (jeudi fermé) ; film : `"court": true` → titre et séances en italique.
- Légende sous chaque grille (`legende_grille` = lignes de [texte, style], coupées à la main, mots-clés dans leur style :
  « Rouge » en rouge, « Souligné » souligné, « Italique » en italique…), hauteur de ligne 20 pt (`h_ligne_grille`).
- L'aperçu (render.py) dessine soulignés et italiques (Skew) : toujours vérifier qu'ils apparaissent.
- Volet central : « évènements ce mois-ci » (Ciné-Ados, Ciné-Kids, Ciné-séniors…), 3 bandeaux de 31,5 mm.
- Partenaires : ceux du Commynes + logo ville de Cerizay (`partenaires_en_plus`, redessiné en vectoriel).
- Logo « Le 7e Art / Cerizay » vectorisé depuis l'ancien programme (`outils/logo_vecto.py`) : SVG, PDF, PNG HD.
- Titre de fiche > 37 caractères : chasse réduite automatiquement (76 %).
- Site du bandeau bas : cinemale7emeart.com (celui de l'ancien programme). Préfixe des images : `7EA`.
- Tarifs Cerizay (06/10/2026, alignés sur La Châtaigneraie) : -14 ans & courts-métrages 4,50 · -25 ans et étudiants 6,20 · plein 7,60 · réduit 6,60.
- Livraison : TOUJOURS un seul zip (< 30 Mo). L'assembleur recompresse à pixels identiques les JPEG > 5 Mo (projecteurs
  12 Mo → 1,4 Mo) et le fauteuil est un PNG (`fauteuil` = « 7EA fauteuil rouge.png », plus le PSD de 7 Mo).
  Ne plus faire de zip « LIENS COMMUNS » (liens oubliés = cadres « ? » dans l'en-tête, retour 06/10/2026). Images du mois ≤ 2400 px.
- `dossier_liens_mac` doit TOUJOURS être un chemin `file:/…/` : un lien sans chemin est ignoré par InDesign
  (cadres vides, rien dans le panneau Liens, script inopérant). Le moteur et l'assembleur ont un garde-fou.
- Affiches des fiches : même taille dans TOUS les volets (la plus petite place disponible commande) ;
  le texte du résumé garde toute la hauteur de son créneau.
- Volet avec du vide : ajouter une fiche (4 max) plutôt que laisser un blanc. Si ça déborde, resserrer la grille
  de cette semaine avec `"h_ligne": 18` (au lieu de 20 pt) et raccourcir le résumé fautif, plutôt que réduire les affiches.

## Affiche A3 (7e Art)

```
python3 moteur/affiche.py --kit . --cinema cinemas/7emeart.json --mois mois/7emeart-AAAA-MM/mois.json \
       --images mois/7emeart-AAAA-MM/images --out SORTIE_AFF
RENDER_FONTS=assets/polices RENDER_LINKS="SORTIE_AFF/<nom>/Links:assets/cinemas/7emeart:assets/communs-hd:assets/communs" \
  python3 moteur/render.py SORTIE_AFF/_idml SORTIE_AFF/apercu
python3 moteur/assembler.py --kit . --cinema cinemas/7emeart.json --sortie SORTIE_AFF \
       --nom "AFFICHE A3 7E ART …" --images mois/7emeart-AAAA-MM/images --version vNN --apercus SORTIE_AFF/apercu
```
Moteur repris du Commynes (`moteur/affiche.py`), adapté au format SEMAINE (déclenché par `semaines` dans mois.json) :
- en-tête projecteurs + logo + fauteuil rouge (`fauteuil_affiche` = « 7EA fauteuil rouge.png ») + 6 affiches + bandeau dates ;
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
`python3 outils/logo_cinema.py "Le 7e Art" "Cerizay" "#D41818" "assets/cinemas/7emeart/7EA logo le 7e art"`
→ SVG + PDF vectoriels + PNG HD. L'ancien logo (CERIZAY en capitales) est conservé dans `assets/cinemas/7emeart/ancien/`.
- Visuel Ciné-Kids de l'affiche (V2 validée 06/10/2026) : crayons de couleur vectoriels + « CINÉ-KIDS » multicolore
  (Fredoka) + dates/goûter + photo d'un film jeunesse fondue à droite, cadre rouge. Généré par
  `python3 outils/visuel_cinekids.py --photo <photo film> --dates "du 17 oct. au 2 nov." --out "mois/…/images/7EA visuel cine kids"`,
  converti en JPG, puis `"visuel_affiche": "7EA visuel cine kids.jpg"` sur l'événement vedette dans mois.json.
- Bloc Ciné-Kids de l'affiche (V2 validée 06/10/2026) : crayons de couleur vectoriels + « CINÉ-KIDS » multicolore (Fredoka)
  + dates en rouge + photo d'un film jeunesse fondue à droite, cadre rouge. Généré par
  `python3 outils/bloc_cinekids.py --photo … --dates "du 17 oct. au 2 nov." --ligne1 … --ligne2 … --sortie "mois/…/images/7EA bloc cine kids.png"`
  puis `"visuel_affiche": "7EA bloc cine kids.png"` sur l'événement vedette dans mois.json (remplace photo + textes du bandeau).
  À refaire à chaque vacances scolaires (autres dates, autre film).
- Programme : même bloc Ciné-Kids au format bandeau (89,7 × 31,5 mm, mise en page compacte automatique) :
  `outils/bloc_cinekids.py … --largeur 89.7 --hauteur 31.5 --sortie "mois/…/images/7EA bloc cine kids programme.png"`
  puis `"visuel_programme": "7EA bloc cine kids programme.png"` sur l'événement dans mois.json.
- Retour Adrien 06/10/2026 (2) : programme → logos des remerciements répartis sur TOUTE la largeur du cadre
  (`remerciements_pleine_largeur: true`, `remerciements_echelle: 0.95`) ; affiche → disposition d'Argentonnay
  (`affiche_disposition: "colonnes"`) : colonne gauche = bloc Ciné-Kids vertical (`visuel_affiche_colonne`, généré par
  `outils/bloc_cinekids.py --largeur L --hauteur H` avec la taille affichée par affiche.py) + cadre « évènements » avec les
  autres bandeaux du programme ; colonne droite (`affiche_largeur_grilles`, 172 mm) = les 4 grilles + la légende.
- Bandeau bas « Toutes les informations… » (retour 06/10/2026) : le gabarit décalait le texte de -4 pt (BaselineShift) et
  le haut du bandeau passe sous le cadre des tarifs → BaselineShift 0, centrage vertical sur la partie rouge visible
  (marge haute 3,3 mm), corps `bandeau_bas_corps` (9,6 pt = max sur une ligne avec cinemale7emeart.com) ; affiche :
  `affiche_bandeau_bas_corps` (14 pt). L'aperçu (render.py) tient compte des marges intérieures des cadres de texte.

## 🔒 MAQUETTE VERROUILLÉE (validée par Adrien le 06/10/2026 — programme v16, affiche A3 v09)

La mise en page doit être IDENTIQUE d'un mois à l'autre. Seul le CONTENU change (films, horaires, événements, images).
- Ne JAMAIS modifier `cinemas/7emeart.json`, `moteur/*.py`, `outils/logo_cinema.py`, `outils/bloc_cinekids.py` pour un
  nouveau mois. Tout passe par `mois/7emeart-AAAA-MM/mois.json` et les images du mois.
- Contrôle OBLIGATOIRE avant chaque livraison (après render.py) :
  `python3 outils/verif_maquette.py verifier --idml SORTIE/_idml --nom programme`
  `python3 outils/verif_maquette.py verifier --idml SORTIE_AFF/_idml --nom affiche`
  → doit afficher « identique à la référence validée ». Sinon : corriger le mois (texte trop long, mauvais champ…),
  ne pas toucher au moteur.
- Changement de maquette uniquement sur demande explicite d'Adrien : modifier, faire valider l'aperçu, puis
  `verif_maquette.py figer …` (les deux) + noter le changement ici, et pousser `reference/` sur GitHub.
- Références : `reference/maquette-programme.json`, `reference/maquette-affiche.json` ; livrables de référence :
  `livrables/7emeart-2026-10/` (IDML + aperçus).

Récapitulatif de la maquette figée :
- Programme : 1 volet = 1 semaine ; fiches = avant-premières puis gros films, triées par 1re séance (film de l'image de
  remplissage juste avant elle) ; affiches de fiche de même taille ; grilles stylées (rouge 4,50 € · souligné goûter ·
  italique courts · violet seul Ciné à 1 € · bleu événements) + légende 2 lignes ; volet central : 3 bandeaux
  « évènements ce mois-ci » (Ciné-Kids = bloc crayons + film jeunesse), remerciements en pleine largeur, tarifs,
  bandeau bas 9,6 pt centré ; couverture : logo Advent Pro « Le 7e Art / Cerizay », fauteuil rouge, 6 affiches, encart.
- Affiche A3 : disposition Argentonnay (événements à gauche avec bloc Ciné-Kids vertical, grilles à droite sans
  bandeau semaine, dates dans la case « HORAIRES »), légende, tarifs, bandeau bas 14 pt, pied de page projecteurs.
- Livraison : un seul zip par document (< 30 Mo), tous les liens `file:/`.
