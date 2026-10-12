# VYNTI — vidéo motion design (v2)

Vidéo promo **1920 × 1080 · 60 i/s · 60 s**, style SaaS blanc puis sombre, montée d'après le document
*Script motion design VYNTI* (8 séquences calées sur une musique à 120 BPM, drop à 0:46).

▶️ **[VYNTI-motion-design.mp4](VYNTI-motion-design.mp4)** · miniature : [VYNTI-miniature.png](VYNTI-miniature.png)

## Déroulé

| Temps | Séquence | À l'image |
|---|---|---|
| 0:00 | 1 · Accroche | Le Fil d'actualité couché à 55° défile à 3 000 px/s, freine, verrouille « Gilet polaire pour femme · 12,00 € » (rangée verte) ; les autres annonces s'éteignent une à une ; notification « Nouvelle annonce » ; *VYNTI les voit **en premier.*** ; recul de caméra jusqu'à la fenêtre entière |
| 0:06 | 2 · Surveiller | Trois annonces s'insèrent en direct, notifications empilées ; avancée × 1,9 vers le panneau, la liste recule et se floute ; l'encart **Bénéfice potentiel** se détache et compte jusqu'à **+103,39 €** ; la ligne Filtre fonce vers la caméra |
| 0:16 | 3 · Cibler | Raccord sur forme vers l'écran Filtres ; une adresse Vinted se tape dans « Depuis une URL » et se découpe en trois critères (FR, « Veste patagonia », ≤ 15 €) ; les interrupteurs s'allument sur les temps |
| 0:22 | 4 · Acheter | Fouetté vers la carte Sécurité · Paiement automatique, vue éclatée en 3D, réglages activés sur les temps, plafond 25,00 €, bouclier vert ; la carte se retourne |
| 0:28 | 5 · Négocier | Au dos, le canevas de la règle « Offre sur favori » ; une impulsion bleue mène à la conversation : offre de 40,50 €, **Offre acceptée** ; puis l'agent IA rédige une réponse « À valider », le curseur clique **Valider** |
| 0:38 | 6 · Piloter | Carte Résultats de l'AutoChat (barres sur 30 jours), raccord par le chiffre vers les Statistiques : 4 tuiles en vue éclatée, bénéfice net par mois, mois record en vert |
| 0:46 | 7 · Tout VYNTI | Le drop : grille de six cases vivantes (Conversations, Comptes, Stock, Discord, Journal, Apparence) ; l'interrupteur « Thème sombre » propage le sombre sur toute la grille en révélation circulaire ; implosion vers un point |
| 0:54 | 8 · Signature | Sur fond sombre, le logo se construit triangle par triangle, « VYNTI », *Achetez avant les autres.*, bouton **vynti.fr** |

Règles du script appliquées partout : aucune image vide ni fondu au blanc (chaque raccord passe par un élément de l'interface), un seul point focal par plan, texte d'interface lisible ou flouté, dérive permanente de la caméra, chaque séquence sur un premier temps, flou de mouvement à 180° uniquement sur les raccords et les fouettés, vocabulaire de 11 mouvements avec les courbes cubic-bezier du document.

## Son

Bande-son entièrement synthétisée par `audio.py` (aucun sample, donc libre de droits) :

- musique à 120 BPM en do majeur : intro filtrée (passe-bas de 400 Hz à 20 kHz), groove A à 0:06, groove B avec la basse à 32,5 s, montée avec caisse claire inversée, 100 ms de silence, **drop à 0:46**, quasi-silence à 53,75 s, résolution sur l'accord final à 56,4 s ;
- les **55 bruitages de la feuille** à leurs temps, crêtes et places dans le champ (ticks, bascules, pops, frappe, carillon de signature à 0:04,2 / 0:32,3 / 0:55,4…) ;
- mixage : ducking de la musique sous les impacts et carillons, creux de 2 dB vers 2–4 kHz, passe-haut 120 Hz et pièce courte sur l'interface, subs en mono ;
- maître mesuré : **−14,1 LUFS intégrés, −1,2 dBTP**, 10,5 LU d'écart dynamique (13 dB entre l'intro et le drop), limiteur à 2 dB de réduction au plus, 48 kHz.

La piste a été mesurée, pas écoutée : à valider à l'oreille. Pour mettre une autre musique :
`ffmpeg -i VYNTI-motion-design.mp4 -i musique.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -shortest sortie.mp4`

## Contenu à vérifier avant diffusion

- **Montants du compte réel** (7 853 € de chiffre d'affaires, 2 567 € de bénéfice, 32,7 % de marge, 80 ventes, bénéfices mensuels) : repris des captures, comme dans la v1. À remplacer par ceux de la démo si vous ne voulez pas les publier.
- **Données illustratives** (pas de capture correspondante) : chiffres de la carte Résultats de l'AutoChat (1 284, 312, 146, 58, 9), conversation « Anorak Carhartt » à 40,50 €, réponse de l'agent, pseudonymes (lina.vtg, camille.b…), noms de comptes (Boutique, Vintage, Achats). Le script demande de reprendre un vrai brouillon de l'agent obtenu avec « Essayer ».
- **Achat sans intervention** : le script demande de vérifier qu'il fonctionne en réel ; sinon retirer la ligne « Finaliser l'achat » de la séquence 4.
- Les photos d'annonces sont celles des captures (vraies annonces Vinted) : le script conseille de les remplacer par des photos d'articles à vous.
- Les captures **Profil** (e-mail) et **Conversations** (pseudos réels) ne sont pas utilisées.

## Fabrication

- `scene.html` : toute l'animation (HTML/CSS/JS). L'interface est **redessinée en vectoriel** (texte net à tous les zooms, thème clair et sombre) ; seules les captures du Fil d'actualité servent de cadre. `renderFrame(t)` fixe l'état exact de chaque élément à l'instant *t* ; ouvrir `scene.html?t=12.5` pour voir une image.
- `render.mjs` : Chromium headless (Playwright) → ffmpeg. Flou de mouvement : sur les plans marqués, chaque image est la moyenne de 6 sous-images réparties sur un obturateur à 180°.
- `audio.py` : synthèse et mixage de la bande-son à partir de la feuille de bruitages exportée par la timeline (`out/cues.json`).
- `prepare.py` : prépare les captures (agrandissement ×2, vignettes, fenêtre évidée).

### Régénérer

Prérequis : Node 18+ avec `playwright` (Chromium), Python 3 avec `numpy`, `scipy`, `Pillow`, et `ffmpeg`.

```bash
cd vynti-video
./build.sh                    # 1080p60, ~20 min sur 4 cœurs
SCALE=2 ./build.sh            # rendu 4K pour YouTube
EXPORTS=1 ./build.sh          # + H.264 18 Mbit/s deux passes et maître ProRes 422 HQ
node render.mjs --stills 8.5,22,45   # aperçus PNG dans out/stills/
```

### Modifier

- **Textes des titres** : tableau `COPY` dans `scene.html` (texte, temps d'entrée et de sortie).
- **Minutage** : chaque séquence est écrite en temps absolus, calés sur la grille de 120 BPM (une mesure = 2 s) ; la feuille de bruitages (`CUES`) et les repères musicaux (`MARKS`) sont dans le même fichier, la musique suit automatiquement.
- **Courbes** : objet `C` (vocabulaire de mouvement du script).
