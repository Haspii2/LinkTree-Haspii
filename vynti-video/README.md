# VYNTI — vidéo motion design (v3)

Vidéo promo **4K UHD 3840 × 2160 · 60 i/s · 60 s**, style SaaS blanc et neutre, sombre pour la signature.
La v3 fusionne les deux versions précédentes : le mur d'annonces, la deuxième fenêtre des filtres et le
fond de pages de l'app de la v1, le découpage, le son et les raccords de la v2 ; caméra et typographie refaites.

▶️ **[VYNTI-motion-design-4K.mp4](VYNTI-motion-design-4K.mp4)** (4K) · [VYNTI-motion-design.mp4](VYNTI-motion-design.mp4) (1080p, réduite depuis la 4K) · miniature : [VYNTI-miniature.png](VYNTI-miniature.png)

## Déroulé

| Temps | Séquence | À l'image |
|---|---|---|
| 0:00 | Accroche | Un mur d'annonces Vinted en perspective défile vers la caméra ; la caméra avance dans le mur en suivant le flux, sans flou de profondeur (une brume légère donne la distance). *Sur Vinted, les meilleures affaires partent en quelques secondes.* Le mur freine, « Gilet polaire pour femme · 12,00 € » se soulève avec l'étiquette **Nouvelle annonce** : *VYNTI les voit en premier.* |
| 0:05 | Raccord | L'annonce se redresse face à la caméra et devient la première ligne du Fil d'actualité ; la fenêtre VYNTI se construit autour d'elle ; le mur se redresse et recule, il reste en fond |
| 0:06 | 01 · Surveiller | Fenêtre redessinée en vectoriel (barre latérale, fil, panneau, barre d'état) ; trois annonces arrivent en direct avec leurs notifications ; la caméra tourne doucement puis avance sur le panneau, l'encart **Bénéfice potentiel** se soulève et compte jusqu'à **+103,39 €** — aucun flou, tout reste lisible |
| 0:14 | 02 · Cibler | Le curseur quitte l'encart et traverse la fenêtre jusqu'à « Filtres » dans la barre latérale, la caméra le suit ; l'écran Filtres glisse en place ; la deuxième fenêtre (les filtres en grand) monte au premier plan ; une adresse Vinted collée devient un filtre (FR, « Veste patagonia », ≤ 15 €) ; le curseur arme les deux filtres : **2 filtres armés**, première prise |
| 0:21 | Raccord | Glissé de caméra à travers un monde de pages de l'app en profondeur (Préférences d'achat, AutoChat, Statistiques, Transactions, Journal…) |
| 0:23 | 03 · Acheter | Carte Sécurité · Paiement automatique devant la page Préférences d'achat : vue éclatée, interrupteurs armés sur les temps, plafond 25,00 €, bouclier validé ; la carte se retourne |
| 0:28 | 04 · Négocier | Au dos, la règle « Offre sur favori » ; une impulsion mène à la conversation : offre de 40,50 €, **Offre acceptée** ; l'agent IA rédige une réponse « À valider », le curseur clique **Valider** |
| 0:37 | 05 · Piloter | Automatisations et Résultats de l'AutoChat sur 30 jours ; raccord par le chiffre vers les Statistiques (tuiles en vue éclatée, bénéfice net par mois), devant un mur incliné de pages de l'app qui défile |
| 0:46 | Tout VYNTI | Le drop : grille de six cases vivantes (Conversations, Comptes, Stock, Discord, Journal, Apparence) devant le mur de pages ; l'interrupteur « Thème sombre » propage le sombre en révélation circulaire ; implosion vers un point |
| 0:54 | Signature | Le logo se construit triangle par triangle, « VYNTI », *Achetez avant les autres.*, bouton **vynti.fr** |

## Direction artistique

- **Palette neutre** : blanc, gris, encre. Aucun texte vert ou bleu ; la seule couleur est celle des petits points d'état « en direct » et des photos d'articles. Interrupteurs, chiffres, boutons et accents en encre.
- **Typographie** : Inter Display pour les titres, en deux tons (encre / gris), interlettrage serré. Les titres montent ligne par ligne derrière un masque, sans flou ; les étiquettes de chapitre (01 · Surveiller…) sont des pastilles noires qui se déroulent.
- **Caméra** : une seule trajectoire continue pour les séquences 1 à 5 (un monde commun : mur, fenêtre, maquette, cartes, pages en profondeur), interpolée en Hermite monotone (vitesse continue, sans dépassement), avec une respiration très légère. Les raccords sont des mouvements (glissé, suivi du curseur, redressement de l'annonce, raccord par le chiffre), jamais des fondus au blanc.
- **Profondeur sans flou** : perspective, parallaxe des pages en profondeur, brume, ombres. Le flou de mouvement (obturateur à 180°) n'existe que sur les mouvements rapides.

## Netteté 4K

Sous une perspective CSS, Chromium pixellise chaque calque à l'échelle de sa mise en page et non à celle de la caméra : un zoom de caméra donnait des interfaces floues. La scène agrandit donc la mise en page du monde (propriété `zoom`, par paliers de 2^¼) et la caméra n'applique que le reste de l'échelle, toujours ≤ 1. Le rendu se fait à 2 pixels par pixel CSS (capture 3840 × 2160). L'interface est entièrement redessinée en HTML vectoriel ; seules les pages en arrière-plan et les photos d'articles viennent des captures.

## Son

Bande-son entièrement synthétisée par `audio.py` (aucun sample, donc libre de droits), recalée sur la v3 :

- musique à 120 BPM : intro filtrée, groove à 0:06, basse à 32,5 s, montée, 100 ms de silence, **drop à 0:46**, résolution sur l'accord final ;
- bruitages calés sur l'image (défilement, verrouillage, carillon de signature, insertions, clics du curseur, frappe de l'adresse, interrupteurs, glissés, retournement, impulsion, valider, compteurs, drop, impacts du logo) ;
- maître mesuré : **−14,1 LUFS intégrés, −1,2 dBTP**, limiteur à 2 dB de réduction au plus, 48 kHz.

La piste a été mesurée, pas écoutée : à valider à l'oreille. Pour mettre une autre musique :
`ffmpeg -i VYNTI-motion-design-4K.mp4 -i musique.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -shortest sortie.mp4`

## Contenu à vérifier avant diffusion

- **Montants du compte réel** (7 853 € de chiffre d'affaires, 2 567 € de bénéfice, 32,7 % de marge, 80 ventes, bénéfices mensuels) : repris des captures. À remplacer par ceux de la démo si vous ne voulez pas les publier.
- **Données illustratives** (pas de capture correspondante) : chiffres de la carte Résultats de l'AutoChat, conversation « Anorak Carhartt » à 40,50 €, réponse de l'agent, pseudonymes (lina.vtg, camille.b…), comptes (Boutique, Vintage, Achats), filtre créé depuis une URL et sa première prise.
- **Achat sans intervention** : vérifier qu'il fonctionne en réel ; sinon retirer la ligne « Finaliser l'achat » de la séquence 3.
- Les photos d'articles sont celles des captures (vraies annonces Vinted) : à remplacer par des photos d'articles à vous si besoin.
- Les captures **Profil** (e-mail) et **Conversations** (pseudos réels) ne sont pas utilisées.

## Fabrication

- `scene.html` : toute l'animation (HTML/CSS/JS). `renderFrame(t)` fixe l'état exact de chaque élément à l'instant *t* ; ouvrir `scene.html?t=12.5` pour voir une image.
- `render.mjs` : Chromium headless (Playwright) → `avg.py` (moyenne des sous-images du flou de mouvement) → ffmpeg, sur plusieurs processus en parallèle.
- `audio.py` : synthèse et mixage de la bande-son à partir de la feuille de bruitages exportée par la timeline (`out/cues.json`).
- `prepare.py` : prépare les captures (agrandissement ×2, vignettes et photo aux coins arrondis).

### Régénérer

Prérequis : Node 18+ avec `playwright` (Chromium), Python 3 avec `numpy`, `scipy`, `Pillow`, et `ffmpeg`.

```bash
cd vynti-video
./build.sh                    # 4K60 + version 1080p, environ 1 h sur 4 cœurs
SCALE=1 ./build.sh            # rendu direct en 1080p, plus rapide
EXPORTS=1 ./build.sh          # + H.264 1080p 18 Mbit/s deux passes et maître ProRes 422 HQ
node render.mjs --stills 8.5,22,45 [--scale 2]   # aperçus PNG dans out/stills/
```

### Modifier

- **Textes** : tableau `COPY` dans `scene.html` (texte, temps d'entrée et de sortie ; `<br>` sépare les lignes).
- **Caméra** : `buildCamera()` (clés de la trajectoire commune), `buildDCam()` (statistiques et grille).
- **Minutage** : temps absolus calés sur 120 BPM (une mesure = 2 s) ; la feuille de bruitages (`CUES`) et les repères musicaux (`MARKS`) sont dans le même fichier, la musique suit automatiquement.
- **Courbes** : objet `C` (vocabulaire de mouvement).
