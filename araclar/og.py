"""site/og.png paylaşım görselini üretir (Pillow; yalnız yerelde gerekir).

Siluetler bir anlık görüntüdeki gerçek uçakların konumundan gelir: x = boylam, y = yükseklik.
    python araclar/og.py
"""
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

KOK = Path(__file__).resolve().parent.parent
W, H = 1200, 630
FONT = "C:/Windows/Fonts/seguibl.ttf"
FONT2 = "C:/Windows/Fonts/segoeuib.ttf"


def renk(a):
    return (255, 107, 53) if a < 3000 else (255, 183, 3) if a < 8000 else (76, 201, 240)


def ucak(d, x, y, b, yon, r):
    pts = [(0, -1), (.18, -.3), (1, .25), (1, .45), (.18, .2), (.14, .8), (.4, 1), (-.4, 1), (-.14, .8),
           (-.18, .2), (-1, .45), (-1, .25), (-.18, -.3)]
    a = math.radians(yon)
    c, s = math.cos(a), math.sin(a)
    d.polygon([(x + b * (px * c - py * s), y + b * (px * s + py * c)) for px, py in pts], fill=r)


def main():
    img = Image.new("RGB", (W, H))
    p = img.load()
    for yy in range(H):
        k = yy / H
        c = tuple(int(a + (b - a) * k) for a, b in zip((3, 7, 18), (26, 42, 94)))
        for xx in range(W):
            p[xx, yy] = c
    kat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(kat)
    veri = json.loads((KOK / "site" / "veri" / "son.json").read_text(encoding="utf-8"))
    for u in veri["ucaklar"]:
        if u["g"] or u["a"] is None:
            continue
        x = (u["lo"] - 27.4) / 3.0 * W
        y = 40 + (1 - min(1, u["a"] / 12500)) * (H - 80)
        dogu = math.sin(math.radians(u["y"] or 90)) >= 0
        ucak(d, x, y, 13 if u["i"] else 9, 90 if dogu else -90, renk(u["a"]) + ((200 if u["i"] else 120),))
    img = Image.alpha_composite(img.convert("RGBA"), kat)
    # yazının arkasına yumuşak koyu alan
    golge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(golge).rounded_rectangle((90, 150, 1110, 480), 60, fill=(3, 7, 18, 170))
    img = Image.alpha_composite(img, golge.filter(ImageFilter.GaussianBlur(40)))
    d = ImageDraw.Draw(img)
    f1, f2, f3 = ImageFont.truetype(FONT, 76), ImageFont.truetype(FONT2, 34), ImageFont.truetype(FONT2, 26)
    for i, satir in enumerate(["İstanbul semalarında", "şu an kaç uçak var?"]):
        w = d.textlength(satir, font=f1)
        d.text(((W - w) / 2, 175 + i * 92), satir, font=f1, fill=(255, 255, 255))
    alt = "Açık ADS-B verisiyle harita ve saat saat defter"
    d.text(((W - d.textlength(alt, font=f2)) / 2, 380), alt, font=f2, fill=(255, 209, 102))
    adr = "birtohum.github.io/istanbul-semalari"
    d.text(((W - d.textlength(adr, font=f3)) / 2, 560), adr, font=f3, fill=(170, 185, 220))
    img.convert("RGB").save(KOK / "site" / "og.png", optimize=True)
    print("site/og.png")


if __name__ == "__main__":
    main()
