#!/usr/bin/env python3
"""Generate all original art for the "Sunless Shrine" one-shot bundle.

Everything here is drawn from scratch with Pillow so the whole adventure is
freely redistributable (CC BY 4.0) with no third-party asset licensing. Re-run
to regenerate; tweak the ROOMS / palette to make your own map.

    python3 build_assets.py

Outputs PNGs into maps/ tokens/ portraits/ secret/ handouts/ next to this file.
"""
from __future__ import annotations

import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
CELL = 70
COLS, ROWS = 30, 22
W, H = COLS * CELL, ROWS * CELL
SEED = 7

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(sz: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT if bold else FONT_R, sz)


def out(*parts: str) -> str:
    p = os.path.join(HERE, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


# --- palette ----------------------------------------------------------------
ROCK = (20, 21, 27)
ROCK_EDGE = (10, 10, 14)
FLOOR = (74, 69, 62)
FLOOR_HI = (99, 92, 82)
GROUT = (41, 38, 34)
WATER = (34, 73, 99)
WATER_HI = (70, 128, 158)
WEB = (214, 218, 226)
BONE = (205, 199, 181)
GLOW = (126, 196, 122)       # sickly "sunless" green
GLOW_CORE = (190, 238, 170)
GOLD = (214, 178, 94)

# Rooms: (col, row, w, h) in cells
ROOMS = {
    "entrance": (1, 1, 5, 4),
    "warren":   (8, 1, 5, 4),
    "webs":     (1, 8, 6, 5),
    "bones":    (10, 8, 7, 5),
    "shrine":   (20, 6, 9, 10),
    "crypt":    (9, 16, 6, 5),
}
# Corridors: (col, row, w, h)
CORRIDORS = [
    (6, 2, 2, 2),    # entrance -> warren
    (2, 5, 2, 3),    # entrance -> webs
    (11, 5, 2, 3),   # warren -> bones
    (7, 10, 3, 2),   # webs -> bones
    (17, 10, 3, 2),  # bones -> shrine
    (12, 13, 2, 3),  # bones -> crypt
]


def cell_rect(c, r, w, h):
    return (c * CELL, r * CELL, (c + w) * CELL, (r + h) * CELL)


# --- battlemap --------------------------------------------------------------

def draw_map():
    random.seed(SEED)
    img = Image.new("RGB", (W, H), ROCK)
    d = ImageDraw.Draw(img)

    floors = [cell_rect(*r) for r in ROOMS.values()] + [cell_rect(*c) for c in CORRIDORS]

    # Floor fills with faint flagstone grout.
    for (x0, y0, x1, y1) in floors:
        d.rectangle((x0, y0, x1, y1), fill=FLOOR)
    for (x0, y0, x1, y1) in floors:
        for gx in range(x0, x1, CELL):
            d.line((gx, y0, gx, y1), fill=GROUT, width=1)
        for gy in range(y0, y1, CELL):
            d.line((x0, gy, x1, gy), fill=GROUT, width=1)
        # subtle flagstone highlights
        for _ in range((x1 - x0) * (y1 - y0) // 9000):
            fx = random.randint(x0 + 4, x1 - 8)
            fy = random.randint(y0 + 4, y1 - 8)
            d.rectangle((fx, fy, fx + random.randint(2, 6), fy + random.randint(2, 5)), fill=FLOOR_HI)

    # Features -------------------------------------------------------------
    # Webbed gallery: cobweb strands across the room corners.
    wx0, wy0, wx1, wy1 = cell_rect(*ROOMS["webs"])
    for _ in range(90):
        ax = random.choice([wx0, wx1]); ay = random.randint(wy0, wy1)
        bx = random.randint(wx0, wx1); by = random.choice([wy0, wy1])
        d.line((ax, ay, bx, by), fill=WEB, width=1)
    for cx, cy in [(wx0, wy0), (wx1, wy0), (wx0, wy1), (wx1, wy1)]:
        for rad in range(16, 120, 14):
            d.arc((cx - rad, cy - rad, cx + rad, cy + rad), 0, 360, fill=WEB, width=1)

    # Hall of bones: scattered bones / rubble.
    bx0, by0, bx1, by1 = cell_rect(*ROOMS["bones"])
    for _ in range(220):
        px = random.randint(bx0 + 6, bx1 - 10); py = random.randint(by0 + 6, by1 - 10)
        if random.random() < 0.5:
            d.line((px, py, px + random.randint(6, 16), py + random.randint(-4, 4)), fill=BONE, width=2)
        else:
            d.ellipse((px, py, px + 5, py + 5), fill=BONE)

    # Flooded crypt: water pool with ripples.
    cx0, cy0, cx1, cy1 = cell_rect(*ROOMS["crypt"])
    d.rectangle((cx0 + 10, cy0 + 10, cx1 - 10, cy1 - 10), fill=WATER)
    for _ in range(40):
        rx = random.randint(cx0 + 16, cx1 - 30); ry = random.randint(cy0 + 16, cy1 - 30)
        rr = random.randint(6, 26)
        d.arc((rx, ry, rx + rr, ry + rr // 2), 0, 180, fill=WATER_HI, width=1)

    # Entrance stair: steps leading in from the top-left.
    ex0, ey0, ex1, ey1 = cell_rect(*ROOMS["entrance"])
    for i, sy in enumerate(range(ey0 + 8, ey0 + 8 + 6 * 14, 14)):
        d.line((ex0 + 8, sy, ex0 + 8 + 70, sy), fill=FLOOR_HI, width=3)

    # Grain overlay.
    noise = Image.effect_noise((W, H), 22).convert("RGB")
    img = Image.blend(img, noise, 0.08)
    d = ImageDraw.Draw(img, "RGBA")

    # Sunless altar in the shrine: a dead sun-disc radiating sickly light.
    sx0, sy0, sx1, sy1 = cell_rect(*ROOMS["shrine"])
    acx, acy = (sx0 + sx1) // 2, sy0 + (sy1 - sy0) * 2 // 5
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for rad, a in [(300, 26), (220, 36), (150, 54), (90, 90)]:
        gd.ellipse((acx - rad, acy - rad, acx + rad, acy + rad), fill=GLOW + (a,))
    glow = glow.filter(ImageFilter.GaussianBlur(24))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img, "RGBA")
    # Altar block + sun disc.
    d.rectangle((acx - 55, acy - 36, acx + 55, acy + 36), fill=(40, 36, 46), outline=(16, 14, 20), width=3)
    d.ellipse((acx - 40, acy - 40, acx + 40, acy + 40), outline=GLOW_CORE, width=4)
    for ang in range(0, 360, 30):
        import math
        a = math.radians(ang)
        d.line((acx + 40 * math.cos(a), acy + 40 * math.sin(a),
                acx + 62 * math.cos(a), acy + 62 * math.sin(a)), fill=GLOW_CORE, width=3)

    # Walls: crisp room outlines (not corridors, so openings read through).
    for r in ROOMS.values():
        x0, y0, x1, y1 = cell_rect(*r)
        d.rectangle((x0, y0, x1, y1), outline=ROCK_EDGE, width=6)
        d.rectangle((x0 + 3, y0 + 3, x1 - 3, y1 - 3), outline=(52, 48, 44), width=1)

    img.save(out("maps", "sunless-shrine.png"))
    return acx, acy


# --- tokens -----------------------------------------------------------------

def token(name, label, base, ring, glyph_rgb=(245, 245, 245), folder="tokens"):
    S = 160
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((6, 6, S - 6, S - 6), fill=ring)
    d.ellipse((14, 14, S - 14, S - 14), fill=base)
    # top highlight
    hi = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hi)
    hd.ellipse((26, 20, S - 40, S // 2), fill=(255, 255, 255, 42))
    img = Image.alpha_composite(img, hi.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(img)
    f = font(74)
    tb = d.textbbox((0, 0), label, font=f)
    d.text(((S - (tb[2] - tb[0])) / 2, (S - (tb[3] - tb[1])) / 2 - tb[1]), label, font=f, fill=glyph_rgb)
    d.ellipse((6, 6, S - 6, S - 6), outline=(0, 0, 0, 90), width=3)
    img.save(out(folder, name + ".png"))


# --- portraits / handouts ---------------------------------------------------

def panel(name, title, subtitle, base_top, base_bot, glyph, glyph_rgb, folder="portraits"):
    Wp, Hp = 560, 720
    img = Image.new("RGB", (Wp, Hp), base_top)
    d = ImageDraw.Draw(img)
    for y in range(Hp):
        t = y / Hp
        d.line((0, y, Wp, y), fill=tuple(int(base_top[i] + (base_bot[i] - base_top[i]) * t) for i in range(3)))
    img = Image.blend(img, Image.effect_noise((Wp, Hp), 20).convert("RGB"), 0.07)
    d = ImageDraw.Draw(img, "RGBA")
    # big glyph
    gf = font(300)
    tb = d.textbbox((0, 0), glyph, font=gf)
    d.text(((Wp - (tb[2] - tb[0])) / 2 - tb[0], 150), glyph, font=gf, fill=glyph_rgb + (235,))
    # frame
    d.rectangle((16, 16, Wp - 16, Hp - 16), outline=GOLD, width=4)
    d.rectangle((24, 24, Wp - 24, Hp - 24), outline=(0, 0, 0, 120), width=1)
    # title banner
    d.rectangle((0, Hp - 150, Wp, Hp - 60), fill=(0, 0, 0, 150))
    tf, sf = font(46), font(24, bold=False)
    tb = d.textbbox((0, 0), title, font=tf)
    d.text(((Wp - (tb[2] - tb[0])) / 2, Hp - 142), title, font=tf, fill=(245, 240, 230))
    tb = d.textbbox((0, 0), subtitle, font=sf)
    d.text(((Wp - (tb[2] - tb[0])) / 2, Hp - 92), subtitle, font=sf, fill=(205, 198, 182))
    img.save(out(folder, name + ".png"))


def explorers_map(acx, acy):
    """A player handout: parchment-framed version with room numbers."""
    base = Image.open(os.path.join(HERE, "maps", "sunless-shrine.png")).convert("RGB")
    # warm parchment wash
    wash = Image.new("RGB", base.size, (62, 48, 28))
    base = Image.blend(base, wash, 0.28)
    pad = 60
    img = Image.new("RGB", (W + pad * 2, H + pad * 2), (42, 32, 20))
    img.paste(base, (pad, pad))
    d = ImageDraw.Draw(img)
    d.rectangle((pad - 10, pad - 10, pad + W + 10, pad + H + 10), outline=GOLD, width=5)
    labels = {"entrance": ("1", "Descent"), "warren": ("2", "Warren"), "webs": ("3", "Gallery"),
              "bones": ("4", "Hall of Bones"), "shrine": ("5", "Sunless Shrine"), "crypt": ("6", "Flooded Crypt")}
    f = font(40); fs = font(24, bold=False)
    for key, (col, row, w, h) in ROOMS.items():
        cx = pad + (col + w / 2) * CELL
        cy = pad + (row + h / 2) * CELL
        num, nm = labels[key]
        d.ellipse((cx - 26, cy - 26, cx + 26, cy + 26), fill=(28, 22, 14), outline=GOLD, width=3)
        tb = d.textbbox((0, 0), num, font=f)
        d.text((cx - (tb[2] - tb[0]) / 2, cy - (tb[3] - tb[1]) / 2 - tb[1]), num, font=f, fill=GOLD)
        tb = d.textbbox((0, 0), nm, font=fs)
        d.text((cx - (tb[2] - tb[0]) / 2, cy + 30), nm, font=fs, fill=(238, 224, 198))
    tf = font(64)
    d.text((pad + 20, 8), "The Sunless Shrine", font=tf, fill=GOLD)
    img.save(out("handouts", "explorers-map.png"))


def warning_glyph():
    Wp = Hp = 640
    img = Image.new("RGB", (Wp, Hp), (26, 22, 16))
    img = Image.blend(img, Image.effect_noise((Wp, Hp), 26).convert("RGB"), 0.1)
    d = ImageDraw.Draw(img, "RGBA")
    import math
    cx, cy = Wp // 2, Hp // 2
    d.ellipse((cx - 210, cy - 210, cx + 210, cy + 210), outline=(120, 100, 60), width=6)
    d.ellipse((cx - 150, cy - 150, cx + 150, cy + 150), outline=GLOW + (220,), width=4)
    for ang in range(0, 360, 20):
        a = math.radians(ang)
        d.line((cx + 150 * math.cos(a), cy + 150 * math.sin(a),
                cx + 205 * math.cos(a), cy + 205 * math.sin(a)), fill=(120, 100, 60), width=3)
    # a barred sun
    d.ellipse((cx - 90, cy - 90, cx + 90, cy + 90), fill=(14, 20, 12), outline=GLOW_CORE + (235,), width=5)
    d.line((cx - 120, cy + 120, cx + 120, cy - 120), fill=(190, 60, 60, 235), width=10)
    f = font(34, bold=False)
    msg = "TURN BACK — THE SUN IS DEAD HERE"
    tb = d.textbbox((0, 0), msg, font=f)
    d.text((cx - (tb[2] - tb[0]) / 2, Hp - 70), msg, font=f, fill=(206, 196, 172))
    img.save(out("handouts", "warning-glyph.png"))


def main():
    acx, acy = draw_map()
    # Monster + PC tokens
    token("giant-rat", "R", (92, 74, 58), (54, 42, 32))
    token("stirge", "S", (124, 70, 96), (72, 40, 56))
    token("giant-spider", "Sp", (46, 52, 60), (24, 28, 34), glyph_rgb=(220, 224, 230))
    token("skeleton", "Sk", (196, 192, 176), (120, 116, 104), glyph_rgb=(40, 36, 30))
    token("cult-fanatic", "K", (78, 44, 92), (150, 230, 150))
    token("pc-fighter", "F", (158, 58, 48), (90, 30, 26))
    token("pc-cleric", "C", (206, 180, 86), (140, 116, 40), glyph_rgb=(40, 34, 18))
    token("pc-rogue", "R", (58, 104, 72), (30, 60, 42))
    token("pc-wizard", "W", (64, 86, 150), (34, 48, 96))
    # Public display portraits (shown when a player clicks the token)
    panel("cult-fanatic", "Keeper of the Flame", "Hooded figure at the altar",
          (44, 26, 54), (18, 12, 24), "✝", GLOW_CORE)
    panel("giant-spider", "Pale Gallery Spider", "Something stirs in the webs",
          (30, 34, 40), (12, 14, 18), "\U0001F577", (210, 214, 222)) if False else panel(
          "giant-spider", "Pale Gallery Spider", "Something stirs in the webs",
          (30, 34, 40), (12, 14, 18), "*", (210, 214, 222))
    # DM-only secret: the Keeper's true form
    panel("cult-fanatic-true", "A Hollow Thing", "Beneath the hood: no face, only cold light",
          (16, 24, 18), (6, 10, 8), "☠", GLOW_CORE, folder="secret")
    explorers_map(acx, acy)
    warning_glyph()
    print("Assets written under", HERE)


if __name__ == "__main__":
    main()
