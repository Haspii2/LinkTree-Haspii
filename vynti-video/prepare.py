"""Prépare les assets de la vidéo à partir des captures d'écran à la racine du dépôt.

- copie / renomme les captures utilisées
- recadre les fenêtres de réglages (modale) et les vignettes d'articles
- agrandit x2 (Lanczos + léger renforcement) pour garder du texte net pendant les zooms
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

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

def rounded(im: Image.Image, r: int) -> Image.Image:
    """Coins arrondis cuits dans l'alpha (suréchantillonnés ×4) : bords lisses même en perspective,
    là où un border-radius CSS sur une image transformée en 3D crénelle."""
    m = Image.new("L", (im.width * 4, im.height * 4), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, m.width - 1, m.height - 1), r * 4, fill=255)
    out = im.convert("RGBA")
    out.putalpha(m.resize(im.size, Image.LANCZOS))
    return out


# Vignettes d'articles du fil d'actualité (48 px, une ligne = 68 px), agrandies à 224 px
# (56 px affichés × zoom 2 × écran 2x) pour ne jamais être agrandies par le navigateur
feed = Image.open(ROOT / SHOTS["feed"]).convert("RGB")
for i in range(11):
    y = 110 + i * 68
    src = feed.crop((263, y, 311, y + 48))
    big = src.resize((224, 224), Image.BICUBIC).filter(ImageFilter.UnsharpMask(radius=2, percent=40, threshold=1))
    rounded(big, 40).save(OUT / f"thumb{i}.png")

# Photo de l'article sélectionné (panneau de détail) : format 396 × 250, ×3, coins arrondis
detail = feed.crop((1037, 161, 1414, 601))
detail.save(OUT / "detail.png")
d = detail.crop((0, 73, 377, 311)).resize((1188, 750), Image.LANCZOS)
rounded(d.filter(ImageFilter.UnsharpMask(radius=2, percent=50, threshold=2)), 30).save(OUT / "detail-r.png")
print("assets ->", OUT)

# Versions légères pour le mur de captures (scène finale)
for name in list(SHOTS) + list(MODALS):
    im = Image.open(OUT / f"{name}.png")
    w = 864
    h = round(im.height * w / im.width)
    im.resize((w, h), Image.LANCZOS).crop((0, 0, w, min(h, 540))).save(OUT / f"wall-{name}.png")
