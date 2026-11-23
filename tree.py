import math
import random
import numpy as np
import pygame

# ====================== НАСТРОЙКИ ======================
COLS, ROWS = 170, 96          # разрешение "картинки" в символах
CW, CH = 6, 8                 # размер символа в пикселях окна
FPS = 60
CHARS = " .,:;-~=+*xo#%&@"    # от тёмного к яркому
GREETING = "С НОВЫМ ГОДОМ!"   # поставь "" чтобы убрать надпись

rnd = random.Random(7)
nprng = np.random.default_rng(11)

pygame.init()
W, H = COLS * CW, ROWS * CH
try:
    screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
except Exception:
    screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Winter Night")
clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas,dejavusansmono,menlo,couriernew,monospace", CH + 1, bold=True)

scene = pygame.Surface((COLS, ROWS), 0, 32)   # маленький холст, на нём рисуем
glow = pygame.Surface((COLS, ROWS), 0, 32)    # слой свечения


# ====================== УТИЛИТЫ ======================
def S(c):
    return (max(0, min(255, int(c[0]))), max(0, min(255, int(c[1]))), max(0, min(255, int(c[2]))))


def mul(c, f):
    return S((c[0] * f, c[1] * f, c[2] * f))


def clamp01(x):
    return max(0.0, min(1.0, x))


def ease_out_back(x):
    x = clamp01(x)
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def put(x, y, c):
    if 0 <= x < COLS and 0 <= y < ROWS:
        scene.set_at((x, y), c)


# ====================== ГЕОМЕТРИЯ ЁЛКИ ======================
CX = COLS // 2
GROUND_Y = 80
NT = 7            # ярусов
TH = 15           # высота яруса
HX, HB = 6, GROUND_Y + 1   # домик
LAMP_X = 30


def tier_w(i):   return int(round(31 - i * 3.6))
def tier_yb(i):  return GROUND_Y - 5 - i * 7
def tier_top(i): return tier_yb(i) - TH


TIER_DUR = 1.3
def tier_start(i): return 1.4 + i * 0.95
def tier_end(i):   return tier_start(i) + TIER_DUR


STAR_Y = tier_top(NT - 1) - 4
T_GIFTS = tier_end(NT - 1) - 1.5
T_STAR = tier_end(NT - 1) + 0.2
T_FW = T_STAR + 2.0         # когда начинается салют


def hw_at(i, y):
    f = (y - tier_top(i)) / TH
    if f < 0 or f > 1:
        return -1
    return tier_w(i) * f ** 0.7 + 0.8


def tree_hw(y):
    m = 0
    for i in range(NT):
        h = hw_at(i, y)
        if h > m:
            m = h
    return m


def owner_tier(x, y, margin=2.5):
    for i in range(NT - 1, -1, -1):
        hw = hw_at(i, y)
        if hw > 0 and abs(x - CX) <= hw - margin:
            return i
    return -1


# ====================== ТЕКСТУРА ЯРУСОВ (numpy) ======================
def make_tier(i):
    w = tier_w(i)
    Wt, Ht = 2 * w + 9, TH + 6
    cxl = Wt // 2
    dx = (np.arange(Wt) - cxl).astype(np.float32)[:, None]
    py = np.arange(Ht, dtype=np.float32)[None, :]
    f = np.minimum(py / TH, 1.0)
    nl = nprng.uniform(-0.8, 1.6, Ht).astype(np.float32)[None, :]
    nr = nprng.uniform(-0.8, 1.6, Ht).astype(np.float32)[None, :]
    hw = w * f ** 0.7 + 0.8 + np.where(dx < 0, nl, nr) * np.minimum(1.0, f * 4)
    droop = 3.6 * np.abs(np.sin(dx * 0.55 + i)) * np.minimum(1.0, np.abs(dx) / (w * 0.55))
    bottom = TH - 1 + droop
    mask = (np.abs(dx) <= hw) & (py <= bottom)

    rel = dx / (hw + 1.0)
    light = 0.82 - 0.34 * rel                                         # свет слева
    branch = 0.88 + 0.12 * np.sin(dx / (py + 3.0) * 14 + i * 1.7)     # веточки лучами
    needle = 0.90 + 0.10 * np.sin(np.abs(dx) * 1.3 - py * 1.7 + i)    # иголки
    jitter = nprng.uniform(0.84, 1.14, (Wt, Ht)).astype(np.float32)
    depth = bottom - py
    shadow = np.where(depth < 2.4, 0.5 + 0.2 * np.maximum(depth, 0), 1.0)   # тень под лапой
    center = 1.0 - 0.28 * np.exp(-(dx / (w * 0.35)) ** 2) * f               # темнее у ствола
    k = light * branch * needle * jitter * shadow * center

    col = np.array([36, 150, 66], np.float32)[None, None, :] * k[..., None]
    sparkle = nprng.random((Wt, Ht)) < 0.06
    col = np.where(sparkle[..., None], np.array([150, 235, 120], np.float32) * k[..., None], col)

    edge = mask & ~(np.roll(mask, 1, 0) & np.roll(mask, -1, 0))
    edge2 = mask & ~(np.roll(mask, 2, 0) & np.roll(mask, -2, 0))
    top_edge = mask & ~np.roll(mask, 1, 1)
    low_edge = mask & ~np.roll(mask, -1, 1)
    r1 = nprng.random((Wt, Ht))
    snow = (edge & (py < TH * 0.92) & (r1 < 0.55)) | \
           (edge2 & (py < TH * 0.9) & (r1 > 0.80)) | \
           (top_edge & (r1 < 0.35))
    ice = low_edge & (r1 < 0.15) & ~snow
    lc = np.clip(light, 0.7, 1.05)[..., None]
    col = np.where(snow[..., None], np.array([228, 240, 255], np.float32) * lc, col)
    col = np.where(ice[..., None], np.array([170, 205, 240], np.float32) * lc, col)
    col = np.clip(col, 0, 255).astype(np.uint8)

    s = pygame.Surface((Wt, Ht), pygame.SRCALPHA)
    a3 = pygame.surfarray.pixels3d(s)
    a3[:] = col
    del a3
    aa = pygame.surfarray.pixels_alpha(s)
    aa[:] = (mask * 255).astype(np.uint8)
    del aa
    return s, Wt, Ht


TIERS = [make_tier(i) for i in range(NT)]

# ====================== УКРАШЕНИЯ ======================
ORN = [(230, 40, 50), (240, 200, 60), (70, 130, 255), (220, 90, 230), (240, 240, 250), (60, 220, 200)]
LC = [(255, 70, 70), (255, 225, 90), (90, 170, 255), (255, 120, 240), (120, 255, 150)]


def random_point_on_tree(margin):
    while True:
        x = rnd.randint(CX - 32, CX + 32)
        y = rnd.randint(tier_top(NT - 1) + 3, tier_yb(0))
        o = owner_tier(x, y, margin)
        if o >= 0:
            return x, y, o


ornaments = []     # (x, y, цвет, время появления, большой?)
for _ in range(55):
    x, y, o = random_point_on_tree(3.5)
    ornaments.append((x, y, rnd.choice(ORN), tier_end(o) + rnd.uniform(0.2, 1.4), rnd.random() < 0.4))

lights = []        # (x, y, цвет, фаза, время появления)
for _ in range(150):
    x, y, o = random_point_on_tree(2.5)
    lights.append((x, y, rnd.choice(LC), rnd.uniform(0, 6.28), tier_end(o) + rnd.uniform(0.3, 2.5)))

garland = []       # (x, y, время появления)
for i in range(NT):
    w = tier_w(i)
    for dx in range(-w, w + 1):
        y = tier_yb(i) - 3.5 + 1.8 * math.sin(dx * 0.3 + i)
        hw = hw_at(i, y)
        if hw > 0 and abs(dx) <= hw - 1.5:
            ap = tier_end(i) + 0.3 + (dx + w) * 0.02
            garland.append((CX + dx, int(round(y)), ap))
            if dx % 4 == 0:
                lights.append((CX + dx, int(round(y)), rnd.choice(LC), rnd.uniform(0, 6.28), ap))

gifts = [  # (x, низ, ширина, высота, цвет, лента, время)
    (CX - 47, 89, 14, 11, (200, 40, 55), (255, 220, 90), T_GIFTS),
    (CX + 31, 89, 15, 13, (215, 50, 50), (255, 220, 90), T_GIFTS + 0.4),
    (CX - 31, 91, 10, 8, (60, 100, 220), (240, 240, 255), T_GIFTS + 0.8),
    (CX + 17, 92, 11, 9, (50, 160, 90), (255, 230, 120), T_GIFTS + 1.2),
    (CX + 47, 92, 10, 7, (150, 70, 200), (220, 220, 240), T_GIFTS + 1.6),
    (CX - 15, 93, 8, 6, (240, 170, 50), (200, 40, 60), T_GIFTS + 2.0),
]


# ====================== ФОН ======================
def sky_color(y):
    k = min(y, GROUND_Y) / GROUND_Y
    return (int(4 + 22 * k ** 1.5), int(6 + 34 * k ** 1.5), int(24 + 70 * k ** 1.3))


def gy(x):
    return GROUND_Y + 1.2 * math.sin(x * 0.08) + 0.8 * math.sin(x * 0.21)


def shaded_circle(surf, cx, cy, r, base):
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                k = 0.80 - 0.24 * dx / r - 0.14 * dy / r
                surf.set_at((cx + dx, cy + dy), mul(base, k))


def build_background():
    bg = pygame.Surface((COLS, ROWS), 0, 32)
    for y in range(ROWS):
        pygame.draw.line(bg, sky_color(y), (0, y), (COLS - 1, y))

    # луна с гало и кратерами
    mx, my, MR = COLS - 26, 17, 9
    base = sky_color(my)
    for r in range(26, MR, -1):
        k = (1 - (r - MR) / 17) ** 2
        pygame.draw.circle(bg, S((base[0] + 34 * k, base[1] + 34 * k, base[2] + 28 * k)), (mx, my), r)
    craters = [(-2, -2, 2), (3, 1, 2), (-1, 4, 1.3), (2, -4, 1.2), (-4, 2, 1.2)]
    for dy in range(-MR, MR + 1):
        for dx in range(-MR, MR + 1):
            if dx * dx + dy * dy <= MR * MR:
                b = 0.92 - 0.14 * dx / MR
                for cx_, cy_, cr in craters:
                    if (dx - cx_) ** 2 + (dy - cy_) ** 2 <= cr * cr:
                        b *= 0.82
                bg.set_at((mx + dx, my + dy), mul((255, 238, 190), b))

    # горы
    for x in range(COLS):
        h = 11 + 7 * math.sin(x * 0.045 + 1) + 4 * math.sin(x * 0.11 + 2) + 2 * math.sin(x * 0.23)
        top = int(GROUND_Y - 8 - h)
        pygame.draw.line(bg, (22, 34, 84), (x, top), (x, GROUND_Y))
        bg.set_at((x, top), (70, 92, 150))
        bg.set_at((x, top + 1), (46, 64, 120))
    # холмы
    for x in range(COLS):
        h = 6 + 4 * math.sin(x * 0.07 + 3) + 2 * math.sin(x * 0.17)
        top = int(GROUND_Y - 3 - h)
        pygame.draw.line(bg, (14, 24, 64), (x, top), (x, GROUND_Y))
    # лес в два ряда
    for base_y, colr in [(GROUND_Y - 3, (12, 28, 74)), (GROUND_Y, (8, 18, 52))]:
        x = rnd.randint(-2, 3)
        while x < COLS + 4:
            h = rnd.randint(8, 15)
            pygame.draw.polygon(bg, colr, [(x - h // 3 - 1, base_y), (x, base_y - h), (x + h // 3 + 1, base_y)])
            if 0 <= x < COLS:
                bg.set_at((x, base_y - h), (110, 140, 200))
                bg.set_at((x, base_y - h + 1), (60, 84, 150))
            x += rnd.randint(3, 6)

    # домик
    pygame.draw.rect(bg, (70, 44, 44), (HX, HB - 11, 19, 11))
    for k in range(0, 19, 3):
        pygame.draw.line(bg, (58, 36, 38), (HX + k, HB - 11), (HX + k, HB - 1))
    pygame.draw.rect(bg, (60, 40, 40), (HX + 13, HB - 23, 3, 7))
    pygame.draw.rect(bg, (210, 222, 248), (HX + 12, HB - 24, 5, 1))
    pygame.draw.polygon(bg, (215, 226, 250), [(HX - 2, HB - 11), (HX + 9, HB - 21), (HX + 21, HB - 11)])
    pygame.draw.polygon(bg, (160, 180, 225), [(HX + 9, HB - 21), (HX + 21, HB - 11), (HX + 9, HB - 11)])
    pygame.draw.rect(bg, (40, 28, 28), (HX + 1, HB - 9, 6, 6))
    pygame.draw.rect(bg, (40, 28, 28), (HX + 12, HB - 9, 6, 6))
    pygame.draw.rect(bg, (100, 60, 28), (HX + 8, HB - 5, 3, 5))

    # столб фонаря
    pygame.draw.rect(bg, (40, 42, 60), (LAMP_X, 70, 1, 16))
    pygame.draw.rect(bg, (40, 42, 60), (LAMP_X - 2, 66, 5, 1))
    pygame.draw.rect(bg, (200, 215, 245), (LAMP_X - 1, 65, 3, 1))

    # снежная земля
    for x in range(COLS):
        gtop = int(gy(x))
        for y in range(gtop, ROWS):
            k = (y - gtop) / max(1, ROWS - gtop)
            c = [92 + (36 - 92) * k, 120 + (58 - 120) * k, 190 + (130 - 190) * k]
            n = rnd.uniform(-7, 7) + 10 * math.sin(x * 0.15 + y * 0.6)
            bg.set_at((x, y), S((c[0] + n, c[1] + n, c[2] + n)))
        bg.set_at((x, gtop), (150, 175, 230))

    # снеговик
    sxm = CX + 64
    shaded_circle(bg, sxm, 87, 5, (225, 235, 255))
    shaded_circle(bg, sxm, 80, 4, (225, 235, 255))
    shaded_circle(bg, sxm, 74, 3, (225, 235, 255))
    for ex in (-1, 1):
        bg.set_at((sxm + ex, 73), (20, 20, 30))
    bg.set_at((sxm + 1, 74), (255, 140, 40))
    bg.set_at((sxm + 2, 74), (255, 140, 40))
    pygame.draw.rect(bg, (200, 40, 50), (sxm - 3, 77, 7, 2))
    pygame.draw.rect(bg, (200, 40, 50), (sxm + 2, 77, 2, 5))
    pygame.draw.rect(bg, (25, 25, 35), (sxm - 3, 71, 7, 1))
    pygame.draw.rect(bg, (25, 25, 35), (sxm - 2, 68, 5, 3))
    for by in (80, 83, 86):
        bg.set_at((sxm, by), (30, 30, 40))
    pygame.draw.line(bg, (90, 60, 30), (sxm - 4, 81), (sxm - 9, 78))
    pygame.draw.line(bg, (90, 60, 30), (sxm + 4, 81), (sxm + 9, 78))

    # основание фонаря в снегу
    pygame.draw.rect(bg, (30, 32, 50), (LAMP_X - 1, 85, 3, 1))
    return bg


bg = build_background()

stars = []
while len(stars) < 110:
    x, y = rnd.randrange(1, COLS - 1), rnd.randrange(1, 46)
    if (x - (COLS - 26)) ** 2 + (y - 17) ** 2 < 15 ** 2:
        continue
    stars.append((x, y, rnd.uniform(0, 6.28), rnd.random() < 0.12))

sparkles = [(rnd.randrange(COLS), rnd.randint(GROUND_Y + 3, ROWS - 1), rnd.uniform(0, 6.28)) for _ in range(70)]

# ====================== СТАТИЧНЫЕ МАССИВЫ ======================
XX = np.arange(COLS, dtype=np.float32)[:, None]
YY = np.arange(ROWS, dtype=np.float32)[None, :]
SKY_MASK = np.clip((54 - YY) / 12, 0, 1).astype(np.float32)
VIG = np.clip(1 - 0.5 * (((XX - COLS / 2) / (COLS * 0.62)) ** 2 + ((YY - ROWS / 2) / (ROWS * 0.75)) ** 2), 0.4, 1.0)
VIG = VIG[..., None].astype(np.float32)
TREE_WARM = (np.exp(-(((XX - CX) / 46) ** 2 + ((YY - (GROUND_Y + 6)) / 11) ** 2))[..., None] *
             np.array([80, 48, 16], np.float32)).astype(np.float32)
LAMP_GLOW = (np.exp(-(((XX - LAMP_X) / 14) ** 2 + ((YY - 86) / 4) ** 2))[..., None] * np.array([70, 52, 22], np.float32) +
             np.exp(-(((XX - LAMP_X) / 8) ** 2 + ((YY - 69) / 8) ** 2))[..., None] * np.array([50, 38, 14], np.float32)
             ).astype(np.float32)

# снег (numpy)
NS = 520
sx = nprng.uniform(0, COLS, NS).astype(np.float32)
sy = nprng.uniform(0, ROWS, NS).astype(np.float32)
sv = nprng.uniform(0.12, 0.8, NS).astype(np.float32)
sph = nprng.uniform(0, 6.28, NS).astype(np.float32)
sb = (90 + 165 * (sv - 0.12) / 0.68).astype(np.float32)
SNOW_TINT = np.array([0.92, 0.96, 1.0], np.float32)


def aurora(t):
    fade = min(1.0, t / 5.0)
    c = 20 + 6 * np.sin(XX * 0.045 + t * 0.35) + 3 * np.sin(XX * 0.13 - t * 0.55)
    band = np.exp(-((YY - c) / 5.0) ** 2)
    curtain = 0.55 + 0.45 * np.sin(XX * 0.22 + t * 0.9 + np.sin(XX * 0.05) * 2)
    a = band * curtain * 0.40 * fade * SKY_MASK
    b = np.exp(-((YY - (c + 7)) / 3.2) ** 2) * (0.5 + 0.5 * np.sin(XX * 0.17 - t * 0.7)) * 0.22 * fade * SKY_MASK
    hue = 0.5 + 0.5 * np.sin(XX * 0.03 + t * 0.2)
    ca = np.array([40, 255, 150], np.float32) * (1 - hue)[..., None] + np.array([60, 170, 255], np.float32) * hue[..., None]
    return a[..., None] * ca + b[..., None] * np.array([170, 70, 255], np.float32)


def mist(t):
    m = np.exp(-((YY - (GROUND_Y - 1)) / 4.5) ** 2) * \
        (0.5 + 0.5 * np.sin(XX * 0.06 + t * 0.25 + np.sin(XX * 0.02 + t * 0.1) * 3))
    return m[..., None] * np.array([16, 24, 44], np.float32)


# ====================== САЛЮТ ======================
iX, iY, iVX, iVY, iLIFE, iMAXL, iR, _g, _b, iPH, iTW, iDRAG, iGRAV = range(13)
NC = 13

_PAL = [((255, 70, 70), (255, 210, 90)), ((90, 170, 255), (255, 255, 255)),
        ((120, 255, 150), (255, 240, 120)), ((255, 110, 230), (130, 200, 255)),
        ((255, 190, 60), (255, 90, 60)), ((190, 120, 255), (90, 255, 230)),
        ((255, 255, 255), (255, 200, 90))]
PALETTES = [(np.array(a, np.float32), np.array(b, np.float32)) for a, b in _PAL]
KINDS = ['peony', 'peony', 'peony', 'ring', 'heart', 'star', 'willow', 'spiral', 'glitter']


def make_particles(x, y, vx, vy, col, life, drag, grav, tw=0.0):
    n = len(vx)
    A = np.zeros((n, NC), np.float32)
    A[:, iX] = x
    A[:, iY] = y
    A[:, iVX] = vx
    A[:, iVY] = vy
    A[:, iLIFE] = life
    A[:, iMAXL] = A[:, iLIFE]
    A[:, iR:iR + 3] = col
    A[:, iPH] = nprng.uniform(0, 6.283, n)
    A[:, iTW] = tw
    A[:, iDRAG] = drag
    A[:, iGRAV] = grav
    return A


class Fireworks:
    def __init__(self):
        self.reset()

    def reset(self):
        self.PA = np.zeros((0, NC), np.float32)
        self.buf = np.zeros((COLS, ROWS, 3), np.float32)   # накопитель со шлейфами
        self.new = []
        self.rockets = []
        self.flashes = []
        self.next_launch = T_FW
        self.next_finale = T_FW + 18
        self.finale = 0

    # --- рисование частиц в накопитель (билинейно, быстро через bincount) ---
    def splat(self, xs, ys, cols, k=0.6):
        x0 = np.floor(xs).astype(np.int64)
        y0 = np.floor(ys).astype(np.int64)
        ok = (x0 >= 0) & (x0 < COLS - 1) & (y0 >= 0) & (y0 < ROWS - 1)
        if not ok.any():
            return
        xs, ys, x0, y0, cols = xs[ok], ys[ok], x0[ok], y0[ok], cols[ok]
        fx = (xs - x0).astype(np.float32)
        fy = (ys - y0).astype(np.float32)
        flat = x0 * ROWS + y0
        idx = np.concatenate([flat, flat + ROWS, flat + 1, flat + ROWS + 1])
        ws = [(1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy]
        for c in range(3):
            w = np.concatenate([wk * cols[:, c] for wk in ws]) * k
            self.buf[:, :, c] += np.bincount(idx, weights=w, minlength=COLS * ROWS).reshape(COLS, ROWS)

    def sparks(self, x, y, n, speed=1.2, up=0.0, life=(0.8, 1.4)):
        th = nprng.uniform(0, 6.283, n)
        sp = nprng.uniform(0.2, speed, n)
        col = np.where(nprng.random((n, 1)) < 0.5, np.array([255, 225, 120]), np.array([255, 255, 255])).astype(np.float32)
        self.new.append(make_particles(x, y, np.cos(th) * sp, np.sin(th) * sp - up, col,
                                       nprng.uniform(life[0], life[1], n), 0.94, 0.02, tw=12.0))

    def launch(self, tx=None, ty=None, kind=None):
        tx = random.uniform(15, COLS - 15) if tx is None else tx
        ty = random.uniform(12, 42) if ty is None else ty
        y0 = GROUND_Y + 2
        dist = max(10.0, y0 - ty)
        v0 = math.sqrt(2 * 0.03 * dist)
        T = v0 / 0.03
        x0 = tx + random.uniform(-14, 14)
        self.rockets.append([x0, y0, (tx - x0) / T, -v0, kind, random.choice(PALETTES)])

    def explode(self, x, y, kind=None, pal=None):
        kind = kind or random.choice(KINDS)
        c1, c2 = pal or random.choice(PALETTES)
        r = nprng
        parts = []
        if kind == 'peony':
            n = 280
            th = r.uniform(0, 6.283, n)
            c = r.uniform(-1, 1, n)
            sp = 2.0 * np.sqrt(1 - c * c) * r.uniform(0.92, 1.05, n)
            col = np.where((sp < 1.25)[:, None], c2, c1) * r.uniform(0.8, 1.15, (n, 1))
            parts.append(make_particles(x, y, np.cos(th) * sp, np.sin(th) * sp, col,
                                        r.uniform(1.4, 2.1, n), 0.93, 0.018))
        elif kind == 'glitter':
            n = 240
            th = r.uniform(0, 6.283, n)
            sp = 1.9 * np.sqrt(r.uniform(0.05, 1, n))
            col = np.where(r.random((n, 1)) < 0.5, np.array([255, 235, 170]), np.array([255, 255, 255])).astype(np.float32)
            parts.append(make_particles(x, y, np.cos(th) * sp, np.sin(th) * sp, col,
                                        r.uniform(1.8, 2.8, n), 0.94, 0.02, tw=r.uniform(10, 22, n)))
        elif kind == 'ring':
            tilt = r.uniform(0.3, 1.0)
            rot = r.uniform(0, 3.14)
            cr, sr = math.cos(rot), math.sin(rot)
            for sp, col, n in ((1.8, c1, 100), (1.0, c2, 60)):
                a = np.linspace(0, 6.283, n, endpoint=False)
                vx, vy = np.cos(a) * sp, np.sin(a) * sp * tilt
                parts.append(make_particles(x, y, vx * cr - vy * sr, vx * sr + vy * cr, col, 1.8, 0.94, 0.012))
        elif kind == 'heart':
            for sc, col, n in ((0.085, c1, 110), (0.05, c2, 70)):
                a = np.linspace(0, 6.283, n, endpoint=False)
                hx = 16 * np.sin(a) ** 3
                hy = -(13 * np.cos(a) - 5 * np.cos(2 * a) - 2 * np.cos(3 * a) - np.cos(4 * a))
                parts.append(make_particles(x, y, hx * sc, hy * sc, col, 2.0, 0.94, 0.01))
        elif kind == 'star':
            rot = r.uniform(0, 6.283)
            for V, col, n in ((2.0, c1, 80), (1.45, c1, 60), (0.9, c2, 40)):
                a = np.linspace(0, 6.283, n, endpoint=False)
                rr = 0.4 + 0.6 * np.abs(np.cos(2.5 * a))
                th = a + rot
                parts.append(make_particles(x, y, np.cos(th) * rr * V, np.sin(th) * rr * V, col, 1.9, 0.935, 0.012))
        elif kind == 'willow':
            n = 190
            th = r.uniform(0, 6.283, n)
            sp = 1.35 * np.sqrt(r.uniform(0.04, 1, n))
            col = np.array([255, 185, 70], np.float32) * r.uniform(0.75, 1.1, (n, 1))
            parts.append(make_particles(x, y, np.cos(th) * sp, np.sin(th) * sp - 0.25, col,
                                        r.uniform(2.6, 3.8, n), 0.955, 0.016))
        elif kind == 'spiral':
            for arm, col in ((0.0, c1), (3.14159, c2)):
                n = 90
                u = np.linspace(0.05, 1, n)
                th = u * 12.5 + arm
                sp = 0.25 + 1.65 * u
                parts.append(make_particles(x, y, np.cos(th) * sp, np.sin(th) * sp, col, 2.0, 0.935, 0.012))
        # яркая вспышка в центре
        parts.append(make_particles(x, y, r.normal(0, 0.35, 14), r.normal(0, 0.35, 14),
                                    np.array([255, 255, 255], np.float32), 0.3, 0.9, 0.0))
        self.new.extend(parts)
        self.flashes.append([x, y, c1.copy(), 1.0])

    def schedule(self, t):
        if t < T_FW:
            return
        if t >= self.next_finale and self.finale == 0:
            self.finale = 16
            self.next_finale = t + 26
        if t >= self.next_launch:
            self.launch()
            if self.finale > 0:
                self.finale -= 1
                self.next_launch = t + random.uniform(0.1, 0.28)
            else:
                self.next_launch = t + random.uniform(0.55, 1.5)
                if random.random() < 0.3:
                    self.launch()

    def update(self, t, dt):
        f = dt * 30.0
        self.schedule(t)
        self.buf *= 0.80 ** f

        for fl in self.flashes:
            fl[3] -= dt * 2.6
        self.flashes = [fl for fl in self.flashes if fl[3] > 0]

        for rk in self.rockets[:]:
            rk[3] += 0.03 * f
            rk[0] += rk[2] * f
            rk[1] += rk[3] * f
            self.splat(np.array([rk[0]]), np.array([rk[1]]), np.array([[255, 220, 160]], np.float32), 0.9)
            ns = 2
            self.new.append(make_particles(rk[0] + nprng.normal(0, 0.3, ns), rk[1],
                                           nprng.normal(0, 0.12, ns), nprng.uniform(0.1, 0.5, ns),
                                           np.array([255, 170, 70], np.float32),
                                           nprng.uniform(0.3, 0.6, ns), 0.92, 0.02))
            if rk[3] > -0.12:
                self.rockets.remove(rk)
                self.explode(rk[0], rk[1], rk[4], rk[5])

        P = self.PA
        if len(P):
            P[:, iLIFE] -= dt
            P = P[P[:, iLIFE] > 0]
        if len(P):
            d = P[:, iDRAG] ** f
            P[:, iVX] *= d
            P[:, iVY] *= d
            P[:, iVY] += P[:, iGRAV] * f
            P[:, iX] += P[:, iVX] * f
            P[:, iY] += P[:, iVY] * f
            life = P[:, iLIFE] / P[:, iMAXL]
            b = np.clip(life * 2.2, 0, 1) ** 1.2
            tw = P[:, iTW]
            b = b * np.where(tw > 0, 0.3 + 0.7 * (0.5 + 0.5 * np.sin(t * tw + P[:, iPH])), 1.0)
            self.splat(P[:, iX], P[:, iY], P[:, iR:iR + 3] * b[:, None], 0.65 * f)
        if self.new:
            P = np.vstack([P] + self.new) if len(P) else np.vstack(self.new)
            self.new = []
        self.PA = P


FW = Fireworks()
emitted = set()
METEOR = [None]

# надпись
txt_base = None
if GREETING:
    f2 = pygame.font.SysFont("arial,dejavusans,verdana,consolas", 9, bold=True)
    txt_base = f2.render(GREETING, True, (255, 255, 255)).convert_alpha()


# ====================== РИСОВАНИЕ ОБЪЕКТОВ ======================
def draw_ball(x, y, c, big, t):
    if big:
        for ddx in (-1, 0, 1):
            for ddy in (-1, 0, 1):
                if abs(ddx) + abs(ddy) == 2:
                    continue
                put(x + ddx, y + ddy, mul(c, 1.0 - 0.18 * (ddx + ddy)))
        put(x, y - 1, mul(c, 1.6))
    else:
        for ddx in (0, 1):
            for ddy in (0, 1):
                put(x + ddx, y + ddy, mul(c, 0.8 if ddx + ddy else 1.0))
    if math.sin(t * 3 + x) > 0.93:
        put(x, y, (255, 255, 255))


def draw_gift(x, yb, w, h, c, r):
    y0 = yb - h
    pygame.draw.rect(scene, c, (x, y0, w, h))
    pygame.draw.rect(scene, mul(c, 0.65), (x + w * 2 // 3, y0, w - w * 2 // 3, h))
    pygame.draw.rect(scene, mul(c, 1.25), (x - 1, y0, w + 2, 3))
    cx_ = x + w // 2
    pygame.draw.rect(scene, r, (cx_ - 1, y0, 2, h))
    pygame.draw.rect(scene, r, (x, y0 + h // 2 + 1, w, 1))
    pygame.draw.line(scene, r, (cx_, y0 - 1), (cx_ - 3, y0 - 3))
    pygame.draw.line(scene, r, (cx_, y0 - 1), (cx_ + 3, y0 - 3))
    pygame.draw.line(scene, r, (cx_, y0 - 1), (cx_ - 3, y0 - 1))
    pygame.draw.line(scene, r, (cx_, y0 - 1), (cx_ + 3, y0 - 1))
    put(cx_, y0 - 2, mul(r, 1.1))


def draw_trunk(h):
    for yy in range(h):
        y = GROUND_Y + 4 - yy
        for xx in range(6):
            k = 1.0 - 0.5 * (xx / 5) + (0.08 if (yy + xx) % 3 == 0 else 0)
            put(CX - 3 + xx, y, mul((120, 78, 36), k))


def draw_scene(t, dt):
    scene.blit(bg, (0, 0))
    glow.fill((0, 0, 0))

    # звёзды
    for x, y, ph, big in stars:
        b = int(max(30, min(255, 130 + 125 * math.sin(t * 2.2 + ph))))
        scene.set_at((x, y), (b, b, min(255, b + 30)))
        if big and b > 190:
            c = (b // 2, b // 2, min(255, b // 2 + 30))
            for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                scene.set_at((x + ox, y + oy), c)

    # падающая звезда
    if METEOR[0] is None and t > 2 and random.random() < 0.18 * dt:
        METEOR[0] = [random.uniform(COLS * 0.45, COLS), random.uniform(2, 24),
                     -random.uniform(1.8, 2.6), random.uniform(0.6, 1.0)]
    m = METEOR[0]
    if m:
        m[0] += m[2] * dt * 30
        m[1] += m[3] * dt * 30
        for k in range(12):
            b = int(255 * (1 - k / 12))
            put(int(m[0] - m[2] * k * 0.9), int(m[1] - m[3] * k * 0.9), (b, b, b))
        if m[0] < -10 or m[1] > 44:
            METEOR[0] = None

    # блеск снега
    for x, y, ph in sparkles:
        if math.sin(t * 4 + ph) > 0.88:
            scene.set_at((x, y), (255, 255, 255))

    # дым из трубы
    for k in range(16):
        u = (t * 0.22 + k / 16) % 1
        px = HX + 14 + int(u * 14 + 2 * math.sin(u * 7 + k))
        py = HB - 25 - int(u * 20)
        put(px, py, mul((190, 200, 225), (1 - u) * 0.6))

    # окна домика и фонарь
    fl = 0.88 + 0.12 * math.sin(t * 7.0) * math.sin(t * 3.1)
    wc = mul((255, 190, 80), fl)
    for wx in (HX + 2, HX + 13):
        pygame.draw.rect(scene, wc, (wx, HB - 8, 4, 4))
        pygame.draw.rect(glow, mul((255, 170, 60), fl), (wx, HB - 8, 4, 4))
        pygame.draw.line(scene, (110, 70, 40), (wx + 2, HB - 8), (wx + 2, HB - 5))
        pygame.draw.line(scene, (110, 70, 40), (wx, HB - 6), (wx + 3, HB - 6))
    lf = 0.9 + 0.1 * math.sin(t * 11)
    pygame.draw.rect(scene, mul((255, 225, 150), lf), (LAMP_X - 1, 67, 3, 3))
    pygame.draw.rect(glow, mul((255, 200, 110), lf), (LAMP_X - 1, 66, 3, 4))

    # сугроб у ёлки, ствол
    pygame.draw.ellipse(scene, (120, 150, 212), (CX - 38, GROUND_Y + 1, 76, 11))
    pygame.draw.ellipse(scene, (150, 178, 232), (CX - 34, GROUND_Y + 2, 68, 5))
    draw_trunk(int(10 * clamp01((t - 0.3) / 0.9)))

    # ярусы
    for i in range(NT):
        p = (t - tier_start(i)) / TIER_DUR
        if p <= 0:
            continue
        surf, Wt, Ht = TIERS[i]
        if p >= 1:
            scene.blit(surf, (CX - Wt // 2, tier_top(i)))
            if i not in emitted:
                emitted.add(i)
                n = 26
                FW.sparks(CX + nprng.uniform(-1, 1, n) * tier_w(i) * 0.85, tier_yb(i) - 3, n, 1.0, up=0.5)
        else:
            s = ease_out_back(p)
            sw, sh = max(1, int(Wt * s)), max(1, int(Ht * s))
            scene.blit(pygame.transform.smoothscale(surf, (sw, sh)), (CX - sw // 2, tier_top(i) + Ht - sh))

    # гирлянда с бусинами
    for x, y, ap in garland:
        if t > ap:
            c = (220, 70, 80) if (x // 2) % 3 == 0 else (235, 190, 75)
            put(x, y, mul(c, 0.8 + 0.2 * math.sin(t * 4 + x * 0.5)))

    # шары
    for x, y, c, ap, big in ornaments:
        age = t - ap
        if age < 0:
            continue
        if age < 0.25:
            put(x, y, c)
        else:
            draw_ball(x, y, c, big, t)

    # огоньки (3 режима, меняются каждые 7 секунд)
    mode = int(max(0.0, t - T_STAR) / 7) % 3
    for x, y, c, ph, ap in lights:
        if t < ap:
            continue
        if mode == 0:
            lv = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * 3.2 + ph))
        elif mode == 1:
            lv = 0.15 + 0.85 * (0.5 + 0.5 * math.sin(t * 5.0 - (x + y) * 0.14)) ** 3
        else:
            lv = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(t * 2.4))
        col = mul(c, lv)
        scene.set_at((x, y), col)
        glow.set_at((x, y), col)

    # волшебный огонёк по спирали
    if t > T_STAR + 0.5:
        for k in range(16):
            tt = t - k * 0.025
            u = (tt * 0.18) % 1.0
            yy = tier_yb(0) - u * (tier_yb(0) - tier_top(NT - 1) - 2)
            ang = tt * 5
            if math.cos(ang) > 0:
                xx = CX + (tree_hw(yy) + 2) * math.sin(ang)
                put(int(xx), int(yy), mul((255, 240, 180), 1 - k / 16))
                if k < 3:
                    glow.set_at((max(0, min(COLS - 1, int(xx))), max(0, min(ROWS - 1, int(yy)))), (255, 230, 150))

    # звезда на макушке
    age = (t - T_STAR) / 0.8
    if age > 0:
        if "star" not in emitted:
            emitted.add("star")
            FW.sparks(CX, STAR_Y, 100, 2.4)
        Rr = 5.2 * ease_out_back(age)
        pts = []
        for k in range(10):
            ang = -math.pi / 2 + k * math.pi / 5 + 0.08 * math.sin(t * 2)
            rr = Rr if k % 2 == 0 else Rr * 0.45
            pts.append((CX + math.cos(ang) * rr, STAR_Y + math.sin(ang) * rr))
        pulse = 0.85 + 0.15 * math.sin(t * 5)
        pygame.draw.polygon(scene, mul((255, 225, 90), pulse), pts)
        put(CX, STAR_Y, (255, 255, 230))
        L = int(Rr * (1.3 + 0.4 * math.sin(t * 4)))
        pygame.draw.line(scene, (200, 190, 120), (CX, STAR_Y - L), (CX, STAR_Y + L))
        pygame.draw.line(scene, (200, 190, 120), (CX - L, STAR_Y), (CX + L, STAR_Y))
        pygame.draw.circle(glow, mul((255, 200, 80), pulse), (CX, STAR_Y), 4)

    # подарки (падают сверху)
    for x, yb, w, h, c, r, ap in gifts:
        if t < ap:
            continue
        p = clamp01((t - ap) / 0.8)
        draw_gift(x, int(yb - (1 - p) ** 2 * 70), w, h, c, r)

    # надпись
    if txt_base is not None and t > T_FW:
        a = clamp01((t - T_FW) / 2.0)
        r_ = int(200 + 55 * math.sin(t * 1.5))
        g_ = int(170 + 70 * math.sin(t * 1.5 + 2))
        b_ = int(120 + 100 * math.sin(t * 1.5 + 4))
        tmp = txt_base.copy()
        tmp.fill((r_, g_, b_, int(255 * a)), special_flags=pygame.BLEND_RGBA_MULT)
        scene.blit(tmp, (CX - tmp.get_width() // 2, 0))


# ====================== СИМВОЛЫ ======================
NCH = len(CHARS)


def make_masks():
    m = np.zeros((NCH, CW, CH), np.uint8)
    for k, ch in enumerate(CHARS):
        if ch == " ":
            continue
        g = font.render(ch, True, (255, 255, 255))
        s = pygame.Surface((CW, CH))
        s.blit(g, ((CW - g.get_width()) // 2, (CH - g.get_height()) // 2))
        a = pygame.surfarray.array3d(s)[:, :, 0].astype(np.float32)
        m[k] = np.clip(a * 1.6, 0, 255)
    return np.maximum(m, 55)       # 20 - слабая цветная подложка за символом


MASKS = make_masks()
LUMW = np.array([0.299, 0.587, 0.114], np.float32)
MASK3 = np.zeros((W, H, 3), np.uint8)
mask_surf = pygame.Surface((W, H))


def bloom(pix):
    b = np.clip(pix - 110, 0, 255).astype(np.uint8)
    s = pygame.surfarray.make_surface(b)
    out = 0
    for dv, k in ((3, 0.9), (8, 1.4)):
        small = pygame.transform.smoothscale(s, (COLS // dv, ROWS // dv))
        back = pygame.transform.smoothscale(small, (COLS, ROWS))
        out = out + pygame.surfarray.array3d(back).astype(np.float32) * k
    return out


def to_ascii(pix):
    lum = pix @ LUMW / 255.0
    v = np.clip((lum - 0.04) / 0.96, 0, 1)
    idx = np.minimum((v ** 1.0 * (NCH - 1) + 0.5).astype(np.intp), NCH - 1)
    mx = pix.max(axis=2, keepdims=True)
    col = pix / np.maximum(mx, 1.0) * 255 * (0.5 + 0.5 * mx / 255)   # чистый яркий цвет
    col = np.clip(col, 0, 255).astype(np.uint8)
    big = pygame.transform.scale(pygame.surfarray.make_surface(col), (W, H))
    m = MASKS[idx].transpose(0, 2, 1, 3).reshape(W, H)
    MASK3[:] = m[:, :, None]
    pygame.surfarray.blit_array(mask_surf, MASK3)
    big.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    screen.blit(big, (0, 0))

def tone(pix, sat=1.6):
    # если пиксель пересвечен, уменьшаем все каналы вместе (оттенок сохраняется)
    m = pix.max(axis=2, keepdims=True)
    pix = pix / np.maximum(1.0, m / 255.0)
    # усиливаем насыщенность вокруг яркости
    g = (pix @ LUMW)[..., None]
    pix = g + (pix - g) * sat
    return np.clip(pix, 0, 255)


def compose(t, dt):
    global sx, sy
    f = dt * 30
    pix = pygame.surfarray.array3d(scene).astype(np.float32)

    pix += aurora(t)
    pix += mist(t)
    pix += TREE_WARM * clamp01((t - 2.5) / 6)
    pix += LAMP_GLOW * (0.85 + 0.15 * math.sin(t * 9) * math.sin(t * 2.3))

    # мягкое свечение огоньков
    sm = pygame.transform.smoothscale(glow, (COLS // 5, ROWS // 5))
    pix += pygame.surfarray.array3d(pygame.transform.smoothscale(sm, (COLS, ROWS))).astype(np.float32) * 8.0

    # снег трёх "глубин" с порывами ветра
    wind = 0.05 + 0.10 * math.sin(t * 0.31) + 0.07 * math.sin(t * 0.83 + 1.0)
    sy = (sy + sv * f) % ROWS
    sx = (sx + (wind + np.sin(t * 0.9 + sph) * 0.08) * f * (0.5 + sv)) % COLS
    ix = sx.astype(np.int32) % COLS
    iy = np.clip(sy.astype(np.int32), 0, ROWS - 1)
    val = sb[:, None] * SNOW_TINT
    pix[ix, iy] = np.maximum(pix[ix, iy], val)
    bf = sv > 0.55
    pix[(ix[bf] + 1) % COLS, iy[bf]] = np.maximum(pix[(ix[bf] + 1) % COLS, iy[bf]], val[bf] * 0.5)
    pix[ix[bf], np.minimum(iy[bf] + 1, ROWS - 1)] = np.maximum(pix[ix[bf], np.minimum(iy[bf] + 1, ROWS - 1)], val[bf] * 0.5)

    # вспышки салюта: цветная подсветка всей сцены
    amb = np.zeros(3, np.float32)
    for fx_, fy_, c, k in FW.flashes:
        amb += c / 255.0 * k
    pix *= 1.0 + 0.5 * np.minimum(amb, 1.4)
    for fx_, fy_, c, k in FW.flashes:
        d2 = (XX - fx_) ** 2 + (YY - fy_) ** 2
        pix += (np.exp(-d2 / (2 * 16.0 ** 2)) * (k * 0.5))[..., None] * c

    pix += FW.buf                  # сам салют
    pix += bloom(pix) * 0.35       # bloom слабее
    pix *= VIG                     # виньетка
    pix = tone(pix)                # цвета вместо белого
    to_ascii(pix)


# ====================== ГЛАВНЫЙ ЦИКЛ ======================
def reset():
    global t
    t = 0.0
    emitted.clear()
    FW.reset()
    METEOR[0] = None


t = 0.0
running = True
frames = 0
while running:
    dt = min(clock.tick(FPS) / 1000.0, 0.05)
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        elif e.type == pygame.MOUSEBUTTONDOWN:
            FW.launch(e.pos[0] / CW, e.pos[1] / CH)          # клик = ракета в эту точку
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                running = False
            elif e.key == pygame.K_r:
                reset()
            elif e.key == pygame.K_s:
                pygame.image.save(screen, "tree.png")
            elif e.key == pygame.K_f:
                FW.launch()
            elif e.key == pygame.K_SPACE:                    # большой финал
                FW.finale = 16
                FW.next_launch = t
            elif e.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
    t += dt
    draw_scene(t, dt)
    FW.update(t, dt)
    compose(t, dt)
    pygame.display.flip()
    frames += 1
    if frames % 30 == 0:
        pygame.display.set_caption(f"Winter Night   {clock.get_fps():.0f} FPS")

pygame.quit()