#!/usr/bin/env python3
"""Regenerate the image assets in src/ from src/kursor_source.png (needs Pillow).

Only needed if the mascot art changes; build.py just copies src/ into docs/assets/.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
NAVY, NAVY2, YELLOW, WHITE, MUTED = (10, 16, 34), (17, 26, 50), (255, 214, 10), (245, 247, 252), (160, 172, 200)

k = Image.open(SRC / "kursor_source.png").convert("RGBA")
k = k.crop(k.getbbox())


def fit(img, size):
    im = img.copy()
    im.thumbnail((size, size), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(im, ((size - im.width) // 2, (size - im.height) // 2), im)
    return canvas


# Hero mascot (2x for retina at 160 css px)
fit(k, 320).save(SRC / "kursor-320.webp", quality=82, method=6)

# Favicons: Kursor's face (screen) reads better than the whole body at 32px
for size, name in [(32, "favicon-32.png"), (180, "apple-touch-icon.png")]:
    bg = Image.new("RGBA", (size, size), NAVY + (255,))
    m = fit(k, int(size * 0.86))
    bg.paste(m, ((size - m.width) // 2, (size - m.height) // 2 + size // 40), m)
    if size == 32:
        bg = fit(k, 32)  # transparent works best in browser tabs
    bg.save(SRC / name, optimize=True)


def font(paths, size):
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


BOLD = ["/System/Library/Fonts/Supplemental/Arial Black.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
REG = ["/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
MONO = ["/System/Library/Fonts/Menlo.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]

og = Image.new("RGB", (1200, 630), NAVY)
d = ImageDraw.Draw(og)
d.rectangle([0, 0, 1200, 120], fill=NAVY2)
d.rectangle([0, 120, 1200, 128], fill=YELLOW)
d.text((60, 38), ">_ BYTE-SIZED FIX", font=font(MONO, 40), fill=YELLOW)
d.text((60, 190), "DSA + System Design", font=font(BOLD, 64), fill=WHITE)
d.text((60, 275), "Free course, Hinglish mein", font=font(BOLD, 52), fill=YELLOW)
d.text((60, 380), "100 animated lessons · practice · cheat-sheets", font=font(REG, 32), fill=MUTED)
d.text((60, 430), "UPI, Tatkal, IPL streaming — Indian case studies", font=font(REG, 32), fill=MUTED)
d.text((60, 540), "Free forever · Made by Khola Labs", font=font(REG, 28), fill=MUTED)
m = fit(k, 320)
og.paste(m, (850, 250), m)
og.save(SRC / "og.jpg", quality=86, optimize=True)
print("assets written to", SRC)
