# VYNTI — vidéo motion design

Vidéo promo **1920×1080 · 60 i/s · ~52 s**, style SaaS blanc, construite à partir des captures d'écran de l'app (racine du dépôt).

▶️ **[VYNTI-motion-design.mp4](VYNTI-motion-design.mp4)** · miniature : [VYNTI-miniature.png](VYNTI-miniature.png)

## Déroulé

| Temps | Scène | Contenu |
|---|---|---|
| 0:00 | Intro | Le logo s'assemble (3 triangles), « VYNTI », *Le bot Vinted taillé pour les revendeurs.* |
| 0:03 | Accroche | *Sur Vinted, les meilleures affaires partent en quelques secondes.* → *VYNTI les voit **en premier.*** sur un flux d'annonces réelles |
| 0:07 | 01 · Surveiller | Fil d'actualité en 3D, notifications « Nouvelle annonce », zoom caméra sur le **bénéfice potentiel** (+103,39 € qui se calcule) |
| 0:14 | 02 · Cibler | Écran Filtres, la ligne de filtres se détache, critères qui apparaissent, le curseur arme les 2 filtres |
| 0:20 | 03 · Acheter | Préférences d'achat, quarantaine / anti-republication / paiement automatique activé au clic, plafond 25 € |
| 0:27 | 04 · Négocier | Agent IA : automatisation *Favori reçu → Proposer −15 % → Me prévenir*, l'IA tape son offre, le vendeur accepte |
| 0:34 | 05 · Piloter | Statistiques (défilement), KPI animés (7 853 € de CA, 2 567 € de bénéfice net, 32,7 % de marge) et graphique mensuel |
| 0:41 | Toutes les fonctions | Mur de captures en perspective, *Tout votre business Vinted. Une seule app.* + pastilles de fonctionnalités |
| 0:47 | Outro | Logo, *Achetez avant les autres.* |

Les chiffres affichés viennent des captures (rapport mensuel, fil d'actualité). La conversation de négociation et les notifications sont des mises en scène illustratives.

> Confidentialité : la capture **Profil** (adresse e-mail) et la capture **Conversations** (pseudos d'autres membres Vinted) ne sont volontairement pas utilisées.

## Son

Bande-son entièrement synthétisée par `audio.py` (aucun sample, donc libre de droits) : nappe + arpège + groove doux à 120 BPM, et bruitages calés image par image sur l'animation (whoosh, pops, clics du curseur, frappe clavier, carillons, impacts). Le *drop* tombe à l'arrivée du fil d'actualité, une coupure précède le mur de captures et l'accord final accompagne le logo. Loudness ≈ −16,7 LUFS.

Pour mettre ta propre musique à la place :

```bash
ffmpeg -i VYNTI-motion-design.mp4 -i ma-musique.mp3 -map 0:v -map 1:a -c:v copy -c:a aac -shortest sortie.mp4
```

## Fonctionnement

- `scene.html` : toute l'animation en HTML/CSS/JS. `renderFrame(t)` fixe l'état exact de chaque élément à l'instant *t* (aucune animation CSS, donc rendu 100 % déterministe). Ouvre `scene.html?t=12.5` dans un navigateur pour voir une image précise.
- `render.mjs` : Chromium headless (Playwright) capture chaque image et l'envoie à ffmpeg (x264), sur plusieurs workers en parallèle.
- `audio.py` : synthèse de la bande-son à partir des repères exportés par la timeline (`out/cues.json`).
- `prepare.py` : prépare les captures (recadrage des fenêtres de réglages, vignettes, agrandissement ×2 pour des zooms nets).

### Régénérer

Prérequis : Node 18+ avec `playwright` (Chromium), Python 3 avec `numpy`, `scipy`, `Pillow`, et `ffmpeg`.

```bash
cd vynti-video
./build.sh                  # ~10 min sur 4 cœurs
FPS=30 WORKERS=4 ./build.sh # version plus rapide
node render.mjs --stills 8.5,22,45   # aperçus PNG dans out/stills/
```

### Modifier

- **Textes** : directement dans le HTML de chaque scène (`#s0` … `#s8`) dans `scene.html`.
- **Durées** : l'objet `SC` (début/fin de chaque scène, en secondes) ; les temps internes de chaque scène sont relatifs à son début. La musique suit automatiquement (`audio.py` lit les scènes dans `cues.json`).
- **Couleurs** : variables CSS `--ink`, `--green`, etc. en haut de `scene.html`.
