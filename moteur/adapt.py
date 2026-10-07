"""
Adaptation des affiches de films au format de leur cadre, SANS rien couper (validé par Adrien le 07/10/2026).

  écart de format ≤ 0,5 %  → image d'origine
  sinon                    → « méthode D » partout (décision d'Adrien du 07/10/2026, jamais de déformation) :
                             affiche entière, les bandes manquantes sont complétées en prolongeant ses propres
                             bords (dernières colonnes/lignes de pixels) puis floutées
  (avertissement au-delà de 5 % d'écart : bandes assez larges pour mériter un coup d'œil)

Le fichier adapté est écrit à côté de l'original : « <nom> [cadre 0750].jpg » (0750 = largeur/hauteur × 1000),
il est donc relié et livré comme les autres images. Résultat déterministe (même entrée → même fichier).
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SEUIL_AVERTIR = 0.05
SEUIL_IDENTIQUE = 0.005


def nom_adapte(nom, ratio):
    base, _ = os.path.splitext(nom)
    return f'{base} [cadre {int(round(ratio * 1000)):04d}].jpg'


def _prolonge(src, W, H):
    """affiche entière centrée dans W×H, bords prolongés + flou (méthode D)"""
    w, h = src.size
    s = min(W / w, H / h)
    fg = src.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
    fw, fh = fg.size
    ox, oy = (W - fw) // 2, (H - fh) // 2
    a = np.asarray(fg).astype(float)
    out = np.zeros((H, W, 3))
    out[oy:oy + fh, ox:ox + fw] = a
    k = max(4, round(min(fw, fh) / 100))                       # épaisseur du bord échantillonné
    cote = ox > 0                                               # bandes à gauche/droite (sinon haut/bas)
    if cote:
        out[:, :ox] = a[:, :k].mean(1, keepdims=True)
        out[:, ox + fw:] = a[:, -k:].mean(1, keepdims=True)
        garde = (ox + k, 0, ox + fw - k, H)
    else:
        out[:oy, :] = a[:k].mean(0, keepdims=True)
        out[oy + fh:, :] = a[-k:].mean(0, keepdims=True)
        garde = (0, oy + k, W, oy + fh - k)
    ext = Image.fromarray(out.clip(0, 255).astype('uint8'))
    r = max(3, round(min(W, H) / 130))
    flou = ext.filter(ImageFilter.GaussianBlur(r))
    m = Image.new('L', (W, H), 255)
    ImageDraw.Draw(m).rectangle(garde, fill=0)
    m = m.filter(ImageFilter.GaussianBlur(max(2, r // 2)))
    res = Image.composite(flou, ext, m)
    res.paste(fg.crop((garde[0] - ox, garde[1] - oy, garde[2] - ox, garde[3] - oy)), (garde[0], garde[1]))
    return res


def adapte(chemin, ratio, avertir=None):
    """renvoie le nom de fichier à lier (l'original ou la version adaptée, créée si besoin)"""
    src = Image.open(chemin).convert('RGB')
    w, h = src.size
    ecart = (w / h) / ratio - 1
    nom = os.path.basename(chemin)
    if abs(ecart) <= SEUIL_IDENTIQUE:
        return nom
    sortie = os.path.join(os.path.dirname(chemin), nom_adapte(nom, ratio))
    if abs(ecart) > SEUIL_AVERTIR and avertir is not None:
        msg = (f"Affiche « {nom} » complétée (format {ecart:+.0%}) : à vérifier, "
               f"remplissage génératif Photoshop possible pour un résultat parfait")
        if msg not in avertir:
            avertir.append(msg)
    if os.path.exists(sortie):
        return os.path.basename(sortie)
    if ratio < w / h:                       # image plus large que le cadre : on garde la largeur
        W, H = w, round(w / ratio)
    else:                                   # image plus haute : on garde la hauteur
        W, H = round(h * ratio), h
    res = _prolonge(src, W, H)
    res.save(sortie, quality=93, dpi=(72, 72))
    return os.path.basename(sortie)
