# HASPII — Bio Page

Page bio : fond vidéo plein écran, écran "click to enter" flouté, carte en verre transparent qui s'incline avec la souris, bannière vidéo fondue dans la carte, stats Discord live. Typographie : police système + [Technor](https://www.fontshare.com/fonts/technor) (Fontshare) pour la machine à écrire et le bloc Discord.

**Stack : un seul fichier `index.html`** (HTML/CSS/JS vanilla, zéro build, zéro dépendance).

## Modifier le contenu

Tout se règle dans le bloc `CONFIG` en haut du `<script>` dans [index.html](index.html) :

| Clé | Rôle |
|---|---|
| `name`, `handle` | Pseudo affiché (carte + intro + titre d'onglet) |
| `typewriter` | Phrases de la machine à écrire |
| `backgroundVideo`, `bannerVideo`, `avatarVideo` | URLs des vidéos (Cloudinary ou lien direct .mp4). `bannerVideo: ""` pour une carte sans bannière |
| `overlay` | Pluie de billets au-dessus de la carte : `src` (vidéo locale), `keyColor` (couleur rendue transparente), `tolerance`/`softness` (réglage du keying). `src: ""` pour désactiver |
| `discord` | Code d'invitation (stats live), nom, logo, valeurs de secours |
| `socials` | Liste des réseaux — types dispo : `discord`, `telegram`, `github`, `tiktok`, `instagram`, `youtube`, `x`, `mail`, `monero` |
| `viewsBase` | Base du compteur de vues (incrément local par visiteur) |
| `frontProtections` | `true`/`false` — blocage clic droit / F12 / copie |

Chaque entrée de `socials` accepte soit `url` (ouvre le lien), soit `copy` (copie la valeur dans le presse-papier au clic, avec infobulle "copié ✓") :

```js
socials: [
  { type: "discord",  url: "https://discord.gg/..." },
  { type: "instagram", url: "https://instagram.com/..." },
  { type: "monero",   copy: "89ZKB..." },   // clic = adresse copiée
],
```

## Tester en local

```bash
npx serve haspii-bio
```

## Déployer sur Vercel

Option 1 — glisser-déposer : va sur [vercel.com/new](https://vercel.com/new), glisse le dossier `haspii-bio`, c'est en ligne.

Option 2 — CLI :

```bash
npm i -g vercel
cd haspii-bio
vercel --prod
```

Aucune config nécessaire (site 100 % statique).

## Notes

- Les vidéos Cloudinary sont automatiquement compressées et redimensionnées à la volée (`q_auto,c_limit,w_…` injecté dans l'URL, adapté à la taille d'affichage : fond 1440px, bannière 760px, avatar 320px). Les URLs non-Cloudinary ou déjà transformées sont utilisées telles quelles.
- La bannière n'a pas de bord net : elle se dissout dans la carte via un masque elliptique à courbe douce (smootherstep), complété par un halo flouté de la vidéo (canvas basse résolution, ~15 img/s) qui prolonge ses couleurs dans le verre.
- Les vidéos restent en MP4 H.264 (compatible partout, iOS compris), sont muettes/en boucle/`playsinline` pour l'autoplay mobile, se mettent en pause quand l'onglet est caché, et se relancent au premier tap si l'autoplay est refusé.

- Le compteur de vues est local au navigateur (base + incréments). Pour un vrai compteur global, il faut brancher une petite API (ex. Vercel KV / Upstash) sur `initViews()`.
- Les stats Discord viennent de l'API publique `discord.com/api/v10/invites/<code>?with_counts=true`, rafraîchies toutes les 30 s.
