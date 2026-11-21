#!/usr/bin/env python3
"""AETHORIA - a travel poster for a place that isn't there.

Writes /output/entry.png (1024x1024, PNG, pure standard library).

The poster shows the floating isles of Aethoria at golden hour: green-topped
islands adrift in a peach sky, waterfalls spilling off their edges into a sea
of cloud, a little airship crossing the sun, and the place name set large in
a hand-built geometric deco face. Everything is drawn procedurally - no
images, no fonts, no network - so the program runs in a bare sandbox.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024
OUT = os.environ.get("MAKEFUN_OUTPUT", "/output/entry.png")

buf = bytearray(W * H * 3)


# ---------------------------------------------------------------- pixels
def blend(x, y, r, g, b, a):
    """Alpha-blend one pixel. a is 0..1."""
    if a <= 0.0 or x < 0 or x >= W or y < 0 or y >= H:
        return
    if a > 1.0:
        a = 1.0
    i = (y * W + x) * 3
    ia = 1.0 - a
    buf[i] = int(buf[i] * ia + r * a + 0.5)
    buf[i + 1] = int(buf[i + 1] * ia + g * a + 0.5)
    buf[i + 2] = int(buf[i + 2] * ia + b * a + 0.5)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp3(c1, c2, t):
    return (lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t))


# ---------------------------------------------------------------- sky
def paint_sky():
    # Deep indigo dusk at the top melting into a golden horizon.
    stops = [
        (0.00, (24, 30, 72)),
        (0.28, (88, 62, 122)),
        (0.48, (196, 104, 102)),
        (0.62, (243, 168, 108)),
        (0.72, (250, 208, 146)),
        (1.00, (250, 224, 176)),
    ]
    for y in range(H):
        t = y / (H - 1)
        for k in range(len(stops) - 1):
            t0, c0 = stops[k]
            t1, c1 = stops[k + 1]
            if t0 <= t <= t1:
                f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
                # A whisper of row-level variation so the gradient never bands.
                f += 0.012 * math.sin(y * 0.11)
                r, g, b = lerp3(c0, c1, max(0.0, min(1.0, f)))
                break
        else:
            r, g, b = stops[-1][1]
        row = bytes((int(r), int(g), int(b))) * W
        buf[y * W * 3:(y + 1) * W * 3] = row


def soft_disc(cx, cy, radius, color, alpha):
    """A radial glow: brightest at the centre, fading to nothing."""
    x0 = max(0, int(cx - radius))
    x1 = min(W - 1, int(cx + radius) + 1)
    y0 = max(0, int(cy - radius))
    y1 = min(H - 1, int(cy + radius) + 1)
    r2 = radius * radius
    for y in range(y0, y1 + 1):
        dy = y - cy
        for x in range(x0, x1 + 1):
            dx = x - cx
            d2 = (dx * dx + dy * dy) / r2
            if d2 < 1.0:
                fall = (1.0 - d2)
                blend(x, y, color[0], color[1], color[2], alpha * fall * fall)


def soft_ellipse(cx, cy, rx, ry, color, alpha):
    """A soft-edged filled ellipse (cloud puff, haze, glow)."""
    x0 = max(0, int(cx - rx))
    x1 = min(W - 1, int(cx + rx) + 1)
    y0 = max(0, int(cy - ry))
    y1 = min(H - 1, int(cy + ry) + 1)
    for y in range(y0, y1 + 1):
        ny = (y - cy) / ry
        ny2 = ny * ny
        if ny2 >= 1.0:
            continue
        half = rx * math.sqrt(1.0 - ny2)
        xa = max(x0, int(cx - half))
        xb = min(x1, int(cx + half))
        for x in range(xa, xb + 1):
            nx = (x - cx) / rx
            d2 = nx * nx + ny2
            if d2 < 1.0:
                fall = 1.0 - d2
                blend(x, y, color[0], color[1], color[2], alpha * fall * fall)


def ellipse_rows(cx, cy, rx, ry, c_top, c_bot):
    """A crisp ellipse filled with a vertical colour gradient."""
    for y in range(max(0, int(cy - ry)), min(H - 1, int(cy + ry)) + 1):
        ny = (y - cy) / ry
        ny2 = ny * ny
        if ny2 >= 1.0:
            continue
        half = rx * math.sqrt(1.0 - ny2)
        t = (y - (cy - ry)) / (2.0 * ry)
        r, g, b = lerp3(c_top, c_bot, max(0.0, min(1.0, t)))
        xa = max(0, int(cx - half))
        xb = min(W - 1, int(cx + half))
        i = (y * W + xa) * 3
        row = bytes((int(r), int(g), int(b))) * (xb - xa + 1)
        buf[i:i + len(row)] = row


# ---------------------------------------------------------------- shapes
def fill_poly(points, color, alpha=1.0):
    """Scanline fill of a simple polygon (even-odd)."""
    if len(points) < 3:
        return
    ys = [p[1] for p in points]
    y0 = max(0, int(min(ys)))
    y1 = min(H - 1, int(max(ys)))
    n = len(points)
    for y in range(y0, y1 + 1):
        yc = y + 0.5
        xs = []
        for k in range(n):
            x1, y1p = points[k]
            x2, y2p = points[(k + 1) % n]
            if (y1p <= yc < y2p) or (y2p <= yc < y1p):
                xs.append(x1 + (yc - y1p) * (x2 - x1) / (y2p - y1p))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            xa = max(0, int(math.ceil(xs[k])))
            xb = min(W - 1, int(xs[k + 1]))
            for x in range(xa, xb + 1):
                blend(x, y, color[0], color[1], color[2], alpha)


def disc(cx, cy, radius, color, alpha=1.0):
    """A crisp filled disc."""
    x0 = max(0, int(cx - radius))
    x1 = min(W - 1, int(cx + radius) + 1)
    y0 = max(0, int(cy - radius))
    y1 = min(H - 1, int(cy + radius) + 1)
    r2 = radius * radius
    for y in range(y0, y1 + 1):
        dy = y - cy
        for x in range(x0, x1 + 1):
            dx = x - cx
            if dx * dx + dy * dy <= r2:
                blend(x, y, color[0], color[1], color[2], alpha)


def bird(x, y, s, color):
    """One distant bird: two short strokes in a shallow V."""
    fill_poly([(x - s, y - s * 0.45), (x - s * 0.55, y - s * 0.45),
               (x, y), (x - s * 0.55, y + s * 0.28),
               (x - s, y + s * 0.28)], color)
    fill_poly([(x + s, y - s * 0.45), (x + s * 0.55, y - s * 0.45),
               (x, y), (x + s * 0.55, y + s * 0.28),
               (x + s, y + s * 0.28)], color)


# ---------------------------------------------------------------- islands
def island(cx, top_y, half_w, depth, with_fall=True, fall_x=None,
           fall_len=120, haze=1.0,
           c_top=(146, 92, 58), c_bot=(74, 44, 34)):
    """A floating island: green cap, rocky cone underneath, waterfall."""
    # Rocky underside: a tapering cone, gradient from warm rock to dark root.
    for y in range(int(top_y + 4), int(top_y + depth) + 1):
        t = (y - top_y) / depth
        hw = half_w * (1.0 - t) ** 0.85
        r, g, b = lerp3(c_top, c_bot, t)
        xa = max(0, int(cx - hw))
        xb = min(W - 1, int(cx + hw))
        i = (y * W + xa) * 3
        row = bytes((int(r), int(g), int(b))) * (xb - xa + 1)
        buf[i:i + len(row)] = row
    # A few darker rock ribs for texture.
    for k, frac in enumerate((0.22, 0.5, 0.78)):
        rx = cx + (frac - 0.5) * 2 * half_w * 0.55
        ry0 = top_y + 10
        ry1 = top_y + depth * (0.55 + 0.2 * frac)
        for y in range(int(ry0), int(ry1) + 1):
            t = (y - top_y) / depth
            hw = half_w * (1.0 - t) ** 0.85
            xx = int(rx + (cx - rx) * t * 0.7)
            for dx in (-1, 0, 1):
                blend(xx + dx, y, 58, 34, 28, 0.35 * haze)
    # Grassy cap: layered ellipses, light on top, deep green at the rim.
    ellipse_rows(cx, top_y - 2, half_w, 30, (122, 178, 92), (52, 104, 62))
    ellipse_rows(cx, top_y - 8, half_w * 0.86, 22, (146, 198, 110), (74, 128, 74))
    # Waterfall spilling off the edge into the cloud sea.
    if with_fall:
        fx = cx + (fall_x if fall_x is not None else half_w * 0.55)
        base = int(top_y + fall_len)
        for y in range(int(top_y + 2), base + 1):
            wob = int(3.0 * math.sin(y * 0.045))
            xx = int(fx) + wob
            fade = 1.0 - 0.35 * (y - top_y) / max(1, fall_len)
            for dx in range(-4, 5):
                a = (0.85 - abs(dx) * 0.09) * fade * haze
                blend(xx + dx, y, 214, 236, 244, a)
            if y % 9 == 0:  # a bright thread inside the fall
                blend(xx - 1, y, 255, 255, 255, 0.8 * haze)
                blend(xx + 1, y, 255, 255, 255, 0.6 * haze)
        soft_ellipse(fx, base + 6, 26, 10, (235, 244, 250), 0.85 * haze)


def tree(x, y, s):
    """A tiny pine on an island cap."""
    fill_poly([(x, y - s), (x + s * 0.55, y), (x - s * 0.55, y)], (38, 84, 52))
    fill_poly([(x, y - s * 0.55), (x + s * 0.45, y + s * 0.35),
               (x - s * 0.45, y + s * 0.35)], (28, 66, 42))
    for yy in range(int(y), int(y + s * 0.35) + 1):
        blend(int(x), yy, 92, 62, 40, 1.0)


def lighthouse(x, base_y):
    """A small white lighthouse on the main isle, lamp lit."""
    soft_disc(x, base_y - 52, 34, (255, 214, 130), 0.5)
    fill_poly([(x - 9, base_y), (x - 7, base_y - 46), (x + 7, base_y - 46),
               (x + 9, base_y)], (250, 244, 226))
    fill_poly([(x - 9, base_y - 14), (x + 9, base_y - 14),
               (x + 9, base_y - 8), (x - 9, base_y - 8)], (196, 74, 60))
    fill_poly([(x - 9, base_y - 34), (x + 9, base_y - 34),
               (x + 9, base_y - 28), (x - 9, base_y - 28)], (196, 74, 60))
    fill_poly([(x - 8, base_y - 58), (x + 8, base_y - 58),
               (x + 8, base_y - 46), (x - 8, base_y - 46)], (52, 44, 66))
    fill_poly([(x - 11, base_y - 58), (x + 11, base_y - 58),
               (x, base_y - 68)], (52, 44, 66))
    disc(x, base_y - 52, 4, (255, 226, 140))


def airship(cx, cy, s):
    """A small red-and-cream airship crossing the sun's side of the sky."""
    ellipse_rows(cx, cy, int(52 * s), int(17 * s),
                 (214, 96, 74), (176, 62, 52))
    ellipse_rows(cx, cy + int(4 * s), int(40 * s), int(9 * s),
                 (250, 238, 210), (232, 214, 180))
    fill_poly([(cx - int(52 * s), cy - int(4 * s)),
               (cx - int(38 * s), cy - int(16 * s)),
               (cx - int(30 * s), cy - int(2 * s))], (176, 62, 52))
    fill_poly([(cx - int(52 * s), cy + int(4 * s)),
               (cx - int(38 * s), cy + int(16 * s)),
               (cx - int(30 * s), cy + int(2 * s))], (176, 62, 52))
    fill_poly([(cx - int(12 * s), cy + int(16 * s)),
               (cx + int(12 * s), cy + int(16 * s)),
               (cx + int(9 * s), cy + int(26 * s)),
               (cx - int(9 * s), cy + int(26 * s))], (96, 66, 58))
    disc(cx + int(46 * s), cy - int(2 * s), int(3 * s), (250, 238, 210))


def cloud_sea():
    """The sea of cloud the isles float above."""
    for y in range(700, H):
        t = (y - 700) / (H - 700)
        r, g, b = lerp3((244, 190, 150), (252, 234, 200), t)
        row = bytes((int(r), int(g), int(b))) * W
        buf[y * W * 3:(y + 1) * W * 3] = row
    puffs = [
        (90, 760, 150, 42, 0.75), (260, 800, 190, 52, 0.85),
        (470, 745, 170, 46, 0.8), (680, 800, 200, 54, 0.85),
        (880, 750, 170, 46, 0.8), (1010, 810, 150, 50, 0.85),
        (40, 880, 170, 48, 0.85), (240, 920, 210, 56, 0.9),
        (480, 880, 190, 50, 0.85), (720, 930, 220, 58, 0.9),
        (950, 890, 180, 50, 0.85), (150, 990, 220, 48, 0.9),
        (560, 990, 240, 52, 0.9), (900, 1000, 220, 50, 0.9),
        (330, 700, 150, 34, 0.55), (760, 705, 160, 34, 0.55),
        # A broken line of puffs straddling the sea's top edge, so the
        # horizon never reads as a straight cut across the poster.
        (60, 698, 140, 36, 0.7), (190, 692, 150, 34, 0.7),
        (340, 700, 150, 36, 0.7), (490, 694, 160, 34, 0.7),
        (640, 700, 150, 36, 0.7), (790, 694, 150, 34, 0.7),
        (930, 700, 150, 36, 0.7), (1030, 696, 130, 32, 0.7),
    ]
    for cx, cy, rx, ry, a in puffs:
        soft_ellipse(cx, cy, rx, ry, (255, 246, 230), a)
    # A few high wisps so the sky is not empty.
    for cx, cy, rx, ry, a in [
        (180, 330, 120, 16, 0.4), (420, 250, 150, 14, 0.35),
        (880, 330, 130, 15, 0.4), (640, 150, 110, 12, 0.3),
    ]:
        soft_ellipse(cx, cy, rx, ry, (255, 228, 200), a)


# ---------------------------------------------------------------- title
# A hand-built geometric deco face on a 10 x 14 grid. Each letter is a list
# of contours; holes are wound counter-clockwise, outlines clockwise, and
# the fill uses the nonzero winding rule.
LETTERS = {
    "A": [[(0, 14), (5, 0), (10, 14)],
          [(5, 5.5), (3.4, 11), (6.6, 11)],
          [(2.9, 9.2), (7.1, 9.2), (7.1, 11), (2.9, 11)]],
    "E": [[(0, 0), (10, 0), (10, 1.8), (1.8, 1.8), (1.8, 6.1), (7.6, 6.1),
           (7.6, 7.9), (1.8, 7.9), (1.8, 12.2), (10, 12.2), (10, 14),
           (0, 14)]],
    "T": [[(0, 0), (10, 0), (10, 1.8), (5.9, 1.8), (5.9, 14), (4.1, 14),
           (4.1, 1.8), (0, 1.8)]],
    "H": [[(0, 0), (1.8, 0), (1.8, 6.1), (8.2, 6.1), (8.2, 0), (10, 0),
           (10, 14), (8.2, 14), (8.2, 7.9), (1.8, 7.9), (1.8, 14),
           (0, 14)]],
    "O": [[(0, 0), (10, 0), (10, 14), (0, 14)],
          [(1.8, 1.8), (1.8, 12.2), (8.2, 12.2), (8.2, 1.8)]],
    "R": [[(0, 0), (10, 0), (10, 7.5), (7.0, 7.5), (10, 14), (8.0, 14),
           (5.6, 7.5), (1.8, 7.5), (1.8, 14), (0, 14)],
          [(1.8, 1.8), (1.8, 5.7), (8.2, 5.7), (8.2, 1.8)]],
    "I": [[(2.5, 0), (7.5, 0), (7.5, 1.8), (5.9, 1.8), (5.9, 12.2),
           (7.5, 12.2), (7.5, 14), (2.5, 14), (2.5, 12.2), (4.1, 12.2),
           (4.1, 1.8), (2.5, 1.8)]],
}


def render_title(text, x0, y0, scale, gap):
    """Render the place name with 3x supersampling for smooth edges."""
    ss = 3
    width = int((len(text) * 10 + (len(text) - 1) * (gap / scale)) * scale)
    height = int(14 * scale)
    mw, mh = width * ss, height * ss
    mask = bytearray(mw * mh)
    # Nonzero-winding scanline fill into the supersampled mask. All of a
    # letter's contours share one event list per scanline, so a hole wound
    # the other way cancels the outline instead of filling itself in.
    for li, ch in enumerate(text):
        ox = li * (10 * scale + gap)
        contours = [[(ox + px_ * scale, py_ * scale) for px_, py_ in c]
                    for c in LETTERS[ch]]
        ys = [p[1] for c in contours for p in c]
        y_lo = max(0, int(min(ys) * ss))
        y_hi = min(mh - 1, int(max(ys) * ss))
        for yy in range(y_lo, y_hi + 1):
            yc = (yy + 0.5) / ss
            events = []
            for pts in contours:
                n = len(pts)
                for k in range(n):
                    x1, y1 = pts[k]
                    x2, y2 = pts[(k + 1) % n]
                    if y1 <= yc < y2:
                        events.append((x1 + (yc - y1) * (x2 - x1) / (y2 - y1), 1))
                    elif y2 <= yc < y1:
                        events.append((x1 + (yc - y1) * (x2 - x1) / (y2 - y1), -1))
            events.sort()
            wind = 0
            prev = None
            for ex, w in events:
                if prev is not None and wind != 0:
                    xa = max(0, int(prev * ss))
                    xb = min(mw - 1, int(ex * ss))
                    base = yy * mw
                    for mx in range(xa, xb + 1):
                        mask[base + mx] = 1
                wind += w
                prev = ex
    # Composite the mask: a soft dark shadow, then the cream face.
    for pass_ in ((5, 7, (46, 24, 56), 0.45), (0, 0, (255, 244, 214), 1.0)):
        dx, dy, color, strength = pass_
        for y in range(height):
            for x in range(width):
                cov = 0
                base = (y * ss) * mw + x * ss
                for sy in range(ss):
                    row = base + sy * mw
                    cov += mask[row] + mask[row + 1] + mask[row + 2]
                if cov:
                    blend(x0 + x + dx, y0 + y + dy,
                          color[0], color[1], color[2],
                          strength * cov / (ss * ss))
    return width, height


# ---------------------------------------------------------------- png
def write_png(path):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += buf[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 6)

    def chunk(typ, data):
        out = struct.pack(">I", len(data)) + typ + data
        return out + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", comp) + chunk(b"IEND", b""))
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ---------------------------------------------------------------- poster
def main():
    paint_sky()

    # The sun, low and warm, upper right.
    soft_disc(775, 215, 260, (255, 206, 130), 0.55)
    soft_disc(775, 215, 130, (255, 226, 160), 0.7)
    disc(775, 215, 58, (255, 246, 205))
    disc(775, 215, 48, (255, 250, 224))

    # Two hazy isles far away, for depth.
    island(150, 470, 70, 60, with_fall=False, haze=0.4)
    soft_ellipse(150, 470, 70, 26, (250, 210, 170), 0.35)
    island(905, 420, 60, 52, with_fall=False, haze=0.4)
    soft_ellipse(905, 420, 60, 24, (250, 210, 170), 0.35)

    # Airship and birds in the open sky.
    airship(215, 185, 1.0)
    for bx, by, bs in ((330, 300, 13), (360, 322, 10), (300, 330, 9),
                       (620, 260, 11), (655, 282, 9), (700, 150, 10)):
        bird(bx, by, bs, (58, 40, 70))

    # The main isle, lighthouse lit, waterfall spilling to the clouds.
    island(400, 440, 215, 205, with_fall=True, fall_x=118, fall_len=210)
    tree(300, 428, 22)
    tree(340, 424, 17)
    tree(500, 430, 19)
    tree(535, 434, 14)
    lighthouse(400, 432)

    # The second isle, smaller, drifting right and lower.
    island(760, 545, 130, 130, with_fall=True, fall_x=-72, fall_len=130)
    tree(720, 536, 15)
    tree(800, 538, 12)

    # Cloud sea, then foam where the falls land.
    cloud_sea()
    soft_ellipse(518, 656, 30, 11, (240, 248, 252), 0.9)
    soft_ellipse(688, 681, 24, 9, (240, 248, 252), 0.9)

    # A soft dark halo behind the title so the name stays legible.
    soft_ellipse(512, 912, 460, 78, (52, 28, 62), 0.30)

    # The place name, and nothing else: no quotes, no ratings, no copy.
    tw, th = render_title("AETHORIA", 113, 852, 120 / 14.0, 16)
    # Thin gold rules flanking the name.
    for y in (908, 909, 910):
        for x in range(38, 92):
            blend(x, y, 232, 190, 110, 0.95)
        for x in range(932, 986):
            blend(x, y, 232, 190, 110, 0.95)
    for cx in (64, 960):
        fill_poly([(cx, 900), (cx + 8, 909), (cx, 918), (cx - 8, 909)],
                  (232, 190, 110))

    size = write_png(OUT)
    print("wrote %s (%d bytes, %dx%d)" % (OUT, size, W, H))


if __name__ == "__main__":
    main()
