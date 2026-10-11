"""Prépare les assets de la vidéo à partir des captures d'écran à la racine du dépôt.

- copie / renomme les captures utilisées
- recadre les fenêtres de réglages (modale) et les vignettes d'articles
- agrandit x2 (Lanczos + léger renforcement) pour garder du texte net pendant les zooms
"""
from pathlib import Path
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "assets"
OUT.mkdir(exist_ok=True)

SHOTS = {
    "feed": "image-1791755793969.png",
    "filtres": "image-1791755802615.png",
    "stats": "image-1791755811107.png",
    "transactions": "image-1791755814130.png",
    "marques": "image-1791755817689.png",
    "rapports": "image-1791755821410.png",
    "stock": "image-1791755825476.png",
    "comptes": "image-1791755830182.png",
    "journal": "image-1791755833248.png",
    "autochat": "image-1791755836436.png",
    "automatisations": "image-1791755839621.png",
    "agent": "image-1791755843100.png",
}
# Fenêtre modale « Paramètres généraux » (bords arrondis gérés en CSS)
MODALS = {
    "prefs-achat": "image-1791755862298.png",
    "paiement": "image-1791755866505.png",
    "livraison": "image-1791755869280.png",
    "apparence": "image-1791755873464.png",
    "messages": "image-1791755877217.png",
}
MODAL_BOX = (121, 71, 1319, 829)


def up2(im: Image.Image) -> Image.Image:
    big = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
    return big.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))


for name, src in SHOTS.items():
    im = Image.open(ROOT / src).convert("RGB")
    up2(im).save(OUT / f"{name}.png", optimize=False)

for name, src in MODALS.items():
    im = Image.open(ROOT / src).convert("RGB").crop(MODAL_BOX)
    up2(im).save(OUT / f"{name}.png", optimize=False)

# Vignettes d'articles du fil d'actualité (48 px, une ligne = 68 px)
feed = Image.open(ROOT / SHOTS["feed"]).convert("RGB")
for i in range(11):
    y = 110 + i * 68
    thumb = feed.crop((263, y, 311, y + 48)).resize((144, 144), Image.LANCZOS)
    thumb.save(OUT / f"thumb{i}.png")

# Photo de l'article sélectionné (panneau de détail)
feed.crop((1037, 161, 1414, 601)).save(OUT / "detail.png")
print("assets ->", OUT)

# Versions légères pour le mur de captures (scène finale)
for name in list(SHOTS) + list(MODALS):
    im = Image.open(OUT / f"{name}.png")
    w = 864
    h = round(im.height * w / im.width)
    im.resize((w, h), Image.LANCZOS).crop((0, 0, w, min(h, 540))).save(OUT / f"wall-{name}.png")
