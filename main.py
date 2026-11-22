#!/usr/bin/env python3
"""Steaming Ramen - one picture of food, drawn pixel by pixel.

A single 1024x1024 illustration of a hot bowl of ramen, seen from above:
a big indigo ceramic bowl filled with golden broth, wavy noodles, chashu,
a halved egg, narutomaki, spring onion, nori, chopsticks and soft steam.

Python 3.13 standard library only. No network. Fully deterministic:
every number comes from one fixed-seed generator, so two runs write
byte-identical PNG files.

Usage: python3 main.py
Writes /output/entry.png (override with ENTRY_PNG).
"""

import math
import os
import random
import struct
import zlib

W = 1024
H = 1024
SEED = 20261122

# ---------------------------------------------------------------- canvas

buf = bytearray(W * H * 3)


def put(x, y, r, g, b):
    """Set one pixel, silently ignoring out-of-frame coordinates."""
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i] = r
        buf[i + 1] = g
        buf[i + 2] = b


def blend(x, y, r, g, b, a):
    """Alpha-blend one pixel over what is already there."""
    if 0 <= x < W and 0 <= y < H and a > 0.0:
        if a >= 1.0:
            put(x, y, r, g, b)
            return
        i = (y * W + x) * 3
        inv = 1.0 - a
        buf[i] = int(r * a + buf[i] * inv)
        buf[i + 1] = int(g * a + buf[i + 1] * inv)
        buf[i + 2] = int(b * a + buf[i + 2] * inv)


def disc(cx, cy, rad, color, alpha=1.0):
    """Filled circle."""
    r, g, b = color
    rr = int(rad) + 1
    for y in range(cy - rr, cy + rr + 1):
        dy = y - cy
        half = int(math.sqrt(max(0, rad * rad - dy * dy)))
        for x in range(cx - half, cx + half + 1):
            blend(x, y, r, g, b, alpha)


def ellipse(cx, cy, rx, ry, color, alpha=1.0):
    """Filled axis-aligned ellipse."""
    r, g, b = color
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        dy = (y - cy) / ry
        rem = 1.0 - dy * dy
        if rem < 0:
            continue
        half = int(rx * math.sqrt(rem))
        for x in range(int(cx) - half, int(cx) + half + 1):
            blend(x, y, r, g, b, alpha)


def ring(cx, cy, r_out, r_in, color, alpha=1.0):
    """Annulus: only the band between the two radii is painted."""
    r, g, b = color
    rr = int(r_out) + 1
    for y in range(cy - rr, cy + rr + 1):
        for x in range(cx - rr, cx + rr + 1):
            d = math.hypot(x - cx, y - cy)
            if r_in <= d <= r_out:
                blend(x, y, r, g, b, alpha)


def arc(cx, cy, rad, a0, a1, width, color, alpha=1.0):
    """Thin arc segment, angles in radians."""
    r, g, b = color
    steps = int((a1 - a0) * rad) + 2
    for s in range(steps + 1):
        a = a0 + (a1 - a0) * s / steps
        x = int(cx + rad * math.cos(a))
        y = int(cy + rad * math.sin(a))
        disc(x, y, width, color, alpha)


def thick_line(x0, y0, x1, y1, width, color, alpha=1.0):
    """Line drawn as a chain of small discs (rounded caps)."""
    length = math.hypot(x1 - x0, y1 - y0)
    steps = max(1, int(length / 2.5))
    for s in range(steps + 1):
        t = s / steps
        x = int(x0 + (x1 - x0) * t)
        y = int(y0 + (y1 - y0) * t)
        disc(x, y, width, color, alpha)


def lerp(a, b, t):
    return a + (b - a) * t


# ---------------------------------------------------------------- palette

BROWN_TOP = (66, 43, 28)
BROWN_BOT = (30, 19, 12)
GLOW = (58, 30, 8)
INDIGO = (36, 50, 108)
INDIGO_DARK = (20, 28, 62)
INDIGO_LIGHT = (74, 96, 168)
RIM_SHINE = (158, 182, 232)
BROTH_CENTRE = (246, 180, 82)
BROTH_MID = (224, 138, 44)
BROTH_EDGE = (148, 80, 24)
NOODLE = (250, 222, 138)
NOODLE_SHADE = (178, 128, 48)
CHASHU = (236, 166, 154)
CHASHU_IN = (246, 202, 186)
CHASHU_EDGE = (198, 118, 108)
EGG_WHITE = (250, 245, 234)
YOLK = (240, 140, 38)
YOLK_HI = (255, 184, 74)
NARUTO_WHITE = (250, 248, 240)
NARUTO_PINK = (234, 118, 140)
ONION = (96, 174, 72)
ONION_DARK = (52, 122, 46)
NORI = (26, 36, 26)
NORI_SHEEN = (52, 68, 48)
WOOD = (172, 122, 72)
WOOD_DARK = (118, 78, 44)
STEAM = (255, 248, 236)

rng = random.Random(SEED)

# Bowl geometry: a big bowl, ~75% of the frame, seen from above.
BCX, BCY = 512, 578
BOWL_R = 385
BROTH_R = 328

# ---------------------------------------------------------------- background

# Precompute cheap per-column / per-row grain waves.
sinx = [math.sin(x * 0.05) + 0.6 * math.sin(x * 0.013 + 1.7) for x in range(W)]
siny = [math.sin(y * 0.11) + 0.5 * math.sin(y * 0.031 + 0.6) for y in range(H)]

for y in range(H):
    t = y / (H - 1)
    base_r = lerp(BROWN_TOP[0], BROWN_BOT[0], t)
    base_g = lerp(BROWN_TOP[1], BROWN_BOT[1], t)
    base_b = lerp(BROWN_TOP[2], BROWN_BOT[2], t)
    dy = y - BCY
    row = y * W * 3
    gy = siny[y]
    for x in range(W):
        dx = x - BCX
        d2 = dx * dx + dy * dy
        # Warm glow behind the bowl.
        glow = 0.0
        if d2 < 560 * 560:
            g = 1.0 - math.sqrt(d2) / 560.0
            glow = g * g
        # Very fine wood grain.
        grain = gy * 2.2 + sinx[x] * 1.6
        # Dark vignette towards the corners.
        vig = 1.0
        if d2 > 400 * 400:
            vig = 1.0 - 0.34 * min(1.0, (math.sqrt(d2) - 400.0) / 330.0)
        i = row + x * 3
        buf[i] = max(0, min(255, int((base_r + glow * GLOW[0] + grain) * vig)))
        buf[i + 1] = max(0, min(255, int((base_g + glow * GLOW[1] + grain) * vig)))
        buf[i + 2] = max(0, min(255, int((base_b + glow * GLOW[2] + grain) * vig)))

# ---------------------------------------------------------------- bowl shadow

for k in range(5):
    alpha = 0.10 - k * 0.018
    ellipse(BCX, BCY + 26 + k * 4, BOWL_R + 26 - k * 4, 66 - k * 5,
            (8, 5, 3), alpha)

# ---------------------------------------------------------------- bowl body

# Indigo disc with a gentle top-to-bottom shade.
for y in range(BCY - BOWL_R, BCY + BOWL_R + 1):
    dy = y - BCY
    half = int(math.sqrt(max(0, BOWL_R * BOWL_R - dy * dy)))
    shade = 1.0 - 0.22 * (y - (BCY - BOWL_R)) / (2 * BOWL_R)
    for x in range(BCX - half, BCX + half + 1):
        d = math.hypot(x - BCX, dy)
        edge = max(0.0, (d - (BOWL_R - 26)) / 26.0)
        r = lerp(INDIGO[0], INDIGO_DARK[0], edge) * shade
        g = lerp(INDIGO[1], INDIGO_DARK[1], edge) * shade
        b = lerp(INDIGO[2], INDIGO_DARK[2], edge) * shade
        put(x, y, int(r), int(g), int(b))

# Lighter rim ring and a thin bright arc, top-left.
ring(BCX, BCY, BOWL_R - 8, BOWL_R - 30, INDIGO_LIGHT, 0.55)
ring(BCX, BCY, BOWL_R - 2, BOWL_R - 6, INDIGO_DARK, 0.8)
arc(BCX, BCY, BOWL_R - 19, math.pi * 0.95, math.pi * 1.45, 5, RIM_SHINE, 0.5)

# ---------------------------------------------------------------- broth

for y in range(BCY - BROTH_R, BCY + BROTH_R + 1):
    dy = y - BCY
    half = int(math.sqrt(max(0, BROTH_R * BROTH_R - dy * dy)))
    for x in range(BCX - half, BCX + half + 1):
        t = math.hypot(x - BCX, dy) / BROTH_R
        tt = t * t * 0.85 + t * 0.15
        if tt < 0.5:
            f = tt / 0.5
            r = lerp(BROTH_CENTRE[0], BROTH_MID[0], f)
            g = lerp(BROTH_CENTRE[1], BROTH_MID[1], f)
            b = lerp(BROTH_CENTRE[2], BROTH_MID[2], f)
        else:
            f = (tt - 0.5) / 0.5
            r = lerp(BROTH_MID[0], BROTH_EDGE[0], f)
            g = lerp(BROTH_MID[1], BROTH_EDGE[1], f)
            b = lerp(BROTH_MID[2], BROTH_EDGE[2], f)
        put(x, y, int(r), int(g), int(b))

# Soft glossy highlight, upper-left of the broth.
ellipse(BCX - 118, BCY - 132, 150, 66, (255, 214, 140), 0.20)
ellipse(BCX - 128, BCY - 140, 88, 36, (255, 228, 170), 0.22)

# A few shiny oil droplets.
for _ in range(14):
    ang = rng.uniform(0, math.tau)
    rad = rng.uniform(60, 300)
    ox = int(BCX + rad * math.cos(ang))
    oy = int(BCY + rad * math.sin(ang) * 0.92)
    disc(ox, oy, rng.uniform(4, 9), (255, 205, 120), 0.5)
    disc(ox - 1, oy - 1, 2, (255, 238, 190), 0.7)

# ---------------------------------------------------------------- noodles

def inside_broth(x, y, margin=8):
    return math.hypot(x - BCX, y - BCY) < BROTH_R - margin


for _ in range(48):
    ang = rng.uniform(0, math.tau)
    rad = rng.uniform(0, 235)
    sx = BCX + rad * math.cos(ang)
    sy = BCY + rad * math.sin(ang) * 0.92
    direction = rng.uniform(0, math.tau)
    length = rng.uniform(120, 260)
    amp = rng.uniform(7, 15)
    wl = rng.uniform(48, 78)
    phase = rng.uniform(0, math.tau)
    px, py = math.cos(direction), math.sin(direction)
    qx, qy = -py, px
    pts = []
    steps = int(length / 4)
    for s in range(steps + 1):
        d = s * 4.0
        wob = amp * math.sin(d / wl * math.tau + phase)
        x = sx + px * d + qx * wob
        y = sy + py * d + qy * wob
        if not inside_broth(x, y):
            break
        pts.append((x, y))
    if len(pts) < 6:
        continue
    # Thin dark shadow just under the strand, then the strand itself.
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        thick_line(ax + 3, ay + 4, bx + 3, by + 4, 3, NOODLE_SHADE, 0.45)
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        thick_line(ax, ay, bx, by, 3, NOODLE, 1.0)

# ---------------------------------------------------------------- toppings

# Two chashu slices, left side.
for (cx, cy, rx, ry) in ((352, 520, 72, 62), (398, 648, 66, 58)):
    ellipse(cx, cy, rx, ry, CHASHU_EDGE, 1.0)
    ellipse(cx, cy, rx - 5, ry - 5, CHASHU, 1.0)
    ellipse(cx - 6, cy - 4, rx * 0.58, ry * 0.55, CHASHU_IN, 1.0)
    arc(cx, cy, rx * 0.36, 0.4, 2.4, 3, CHASHU_EDGE, 0.55)

# Half an egg, right side: white, glossy orange yolk, bright dot.
ellipse(706, 618, 80, 62, EGG_WHITE, 1.0)
ellipse(706, 618, 80, 62, (228, 214, 196), 0.25)
disc(710, 622, 35, YOLK, 1.0)
disc(704, 616, 24, YOLK_HI, 0.55)
ellipse(696, 606, 12, 7, (255, 244, 214), 0.85)

# One narutomaki slice, top centre: white disc, pink spiral.
disc(528, 348, 43, NARUTO_WHITE, 1.0)
ring(528, 348, 43, 39, NARUTO_PINK, 0.9)
spiral = []
for s in range(0, 120):
    t = s / 120.0 * math.tau * 2.6
    rr = 4 + t * 2.1
    spiral.append((528 + rr * math.cos(t), 348 + rr * math.sin(t)))
for (ax, ay), (bx, by) in zip(spiral, spiral[1:]):
    thick_line(ax, ay, bx, by, 2, NARUTO_PINK, 1.0)
disc(528, 348, 5, NARUTO_PINK, 1.0)

# Spring onion rings scattered over the broth.
for _ in range(18):
    ang = rng.uniform(0, math.tau)
    rad = rng.uniform(40, 285)
    ox = int(BCX + rad * math.cos(ang))
    oy = int(BCY + rad * math.sin(ang) * 0.92)
    if not inside_broth(ox, oy, 20):
        continue
    ro = rng.uniform(10, 14)
    ring(ox, oy, ro, ro * 0.55, ONION_DARK, 1.0)
    ring(ox, oy, ro * 0.82, ro * 0.55, ONION, 1.0)

# One dark nori sheet at the right edge, leaning on the rim.
for y in range(468, 642):
    for x in range(812, 880):
        if math.hypot(x - BCX, y - BCY) > BROTH_R + 26:
            continue
        # Rounded corners.
        if (x < 826 and y < 482) or (x < 826 and y > 628) or \
           (x > 866 and y < 482) or (x > 866 and y > 628):
            continue
        put(x, y, *NORI)

# ---------------------------------------------------------------- chopsticks

# Two wooden sticks, diagonal across the top-right, resting on the rim.
thick_line(706, 118, 948, 296, 6, WOOD_DARK, 1.0)
thick_line(706, 118, 948, 296, 4, WOOD, 1.0)
thick_line(742, 100, 978, 272, 6, WOOD_DARK, 1.0)
thick_line(742, 100, 978, 272, 4, WOOD, 1.0)
# Darker tips where they meet the bowl.
disc(712, 124, 5, WOOD_DARK, 0.8)
disc(748, 106, 5, WOOD_DARK, 0.8)

# ---------------------------------------------------------------- steam

# Six soft vertical columns above the bowl: many heavily overlapping
# translucent ellipses, so each column reads as one continuous wisp
# that fades and sways gently as it rises. No dots, no zigzag.
columns = [(296, -1), (382, 1), (462, -1), (548, 1), (632, -1), (716, 1)]
for base_x, sway_dir in columns:
    for k in range(18):
        frac = k / 17.0
        y = int(198 - frac * 170)
        sway = sway_dir * math.sin(frac * math.pi * 0.9) * 16
        x = int(base_x + sway + rng.uniform(-2, 2))
        rx = 15 + frac * 11
        ry = 34 - frac * 7
        alpha = 0.075 * (1.0 - frac * 0.7)
        ellipse(x, y, rx, ry, STEAM, alpha)

# ---------------------------------------------------------------- PNG encode

def chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


raw = bytearray()
for y in range(H):
    raw.append(0)  # filter: none
    raw += buf[y * W * 3:(y + 1) * W * 3]

png = b"\x89PNG\r\n\x1a\n"
png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
png += chunk(b"IEND", b"")

out_path = os.environ.get("ENTRY_PNG", "/output/entry.png")
out_dir = os.path.dirname(out_path)
if out_dir and not os.path.isdir(out_dir):
    os.makedirs(out_dir, exist_ok=True)
with open(out_path, "wb") as f:
    f.write(png)

print(f"wrote {out_path}: {len(png)} bytes, {W}x{H}")
