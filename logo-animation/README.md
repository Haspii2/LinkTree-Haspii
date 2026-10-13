# Animation du logo — effet `pandore.gif`

`logo-animation.mp4` : le logo de `logo.png` animé avec le mouvement, le timing et les effets lumineux de `pandore.gif`.

| | |
|---|---|
| Définition | 3840 × 2160 (4K UHD) |
| Cadence | 60 images/s |
| Durée | 3,00 s, en boucle parfaite (dernière image → première image sans saut) |
| Codec | H.264 High 4:2:0, CRF 10, BT.709 |

## Déroulé (calé image par image sur le GIF, 25 i/s → 60 i/s)

| Temps | Phase |
|---|---|
| 0,00 – 0,12 s | Logo final, halo doux, zoom lent qui continue la boucle |
| 0,12 s | Coupe franche vers la version 3D « tech » du logo |
| 0,12 – 0,64 s | Plongée caméra ×2,23 avec ralenti en fin de course et roulis d'environ 8° ; logo voxelisé et extrudé, panneaux, parois nervurées, profondeur de champ, bokeh, traînées horizontales |
| 0,64 – 1,24 s | Blanc saturé avec dérive lente |
| 1,24 – 1,60 s | Recul accéléré (×0,63) : la structure s'aplatit et les arêtes en escalier redeviennent nettes |
| 1,60 – 1,92 s | Logo à plat très lumineux, légère perspective (homographies mesurées sur le GIF), traînées, poussières |
| 1,92 – 2,24 s | Glitch : tranches décalées, traînée blanche, contours fantômes, fragments (motif renouvelé à 25 Hz comme dans le GIF) |
| 2,24 – 3,00 s | Retour au calme : lignes résiduelles, halo qui décroît, fond gris qui repasse au noir, zoom lent constant |

## Comment c'est construit

- **Logo** : `logo.png` (256 px) a été vectorisé. Les arêtes sont ajustées par moindres carrés (écart RMS 0,05 px) et les coins arrondis par des Bézier tangentes. L'écart moyen avec le PNG d'origine est de 0,26 %. Le logo est donc rendu net en 4K, sans aucune déformation (`src/fit.json`).
- **Mouvement** : zoom, roulis et homographies mesurés sur chaque image du GIF par alignement ECC, puis interpolés à 60 i/s.
- **Halo et fond** : modèle de halo (somme de flous gaussiens + traînée horizontale + voile) calé par moindres carrés sur chaque image propre du GIF (`src/glow_w.json`).
- La phase 3D du GIF est propre à son logo (cube dans un hexagone). Elle est transposée au V : mêmes ingrédients visuels et même trajectoire de caméra.

## Re-rendre

```bash
pip install numpy scipy opencv-python-headless
python3 src/render_all.py frames 4        # 180 images PNG 4K (≈ 5 min sur 4 cœurs)
./src/encode.sh frames logo-animation.mp4
```

Les réglages se trouvent dans `src/anim.py` (phases à plat, glitch) et `src/scene3d.py` (phase 3D).
