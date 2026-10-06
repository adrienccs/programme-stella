// Relier les liens.jsx — Copy Color Service
// Relie en une fois toutes les images manquantes du document ouvert
// à partir du dossier « Links » livré avec le programme.
// Installation : copier ce fichier dans le dossier des scripts InDesign
//   (Fenêtre > Utilitaires > Scripts, clic droit sur « Utilisateur » > Faire apparaître dans le Finder),
// puis double-cliquer sur le script dans le panneau Scripts.
#target indesign
(function () {
    if (!app.documents.length) { alert("Ouvre d'abord le programme (IDML ou INDD)."); return; }
    var doc = app.activeDocument;
    // 1) dossier Links à côté du document (document déjà enregistré en .indd)
    var dossier = null;
    try { var d = Folder(doc.filePath + "/Links"); if (d.exists) dossier = d; } catch (e) {}
    // 2) sinon (IDML ouvert = document « Sans titre ») : on demande une seule fois
    if (!dossier) dossier = Folder.selectDialog("Choisis le dossier « Links » (à côté de l'IDML)");
    if (!dossier) return;

    var ACC = { "à":"a","â":"a","ä":"a","á":"a","ç":"c","é":"e","è":"e","ê":"e","ë":"e","î":"i","ï":"i","í":"i",
                "ô":"o","ö":"o","ó":"o","ù":"u","û":"u","ü":"u","ú":"u","ÿ":"y","œ":"oe","æ":"ae" };
    function cle(s) {
        try { s = decodeURI(s); } catch (e) {}
        s = s.toLowerCase().replace(/[̀-ͯ]/g, "");          // accents décomposés (Mac)
        s = s.replace(/[àâäáçéèêëîïíôöóùûüúÿœæ]/g, function (c) { return ACC[c]; });
        return s.replace(/[^a-z0-9.]/g, "");                            // espaces, apostrophes, tirets…
    }
    var fichiers = dossier.getFiles(), table = {};
    for (var i = 0; i < fichiers.length; i++)
        if (fichiers[i] instanceof File) table[cle(fichiers[i].name)] = fichiers[i];

    var ok = 0, deja = 0, absents = [];
    var liens = doc.links.everyItem().getElements();
    for (var j = 0; j < liens.length; j++) {
        var l = liens[j];
        if (l.status == LinkStatus.NORMAL) { deja++; continue; }
        var f = table[cle(l.name)];
        if (!f) { absents.push(l.name); continue; }
        try { l.relink(f); try { l.update(); } catch (e2) {} ok++; }
        catch (e) { absents.push(l.name + " (" + e + ")"); }
    }
    alert(ok + " lien(s) relié(s), " + deja + " déjà OK." +
          (absents.length ? "\n\nIntrouvables dans le dossier :\n" + absents.join("\n") : "\n\nTout est relié !"));
})();
