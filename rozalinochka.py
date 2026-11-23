import math
import random
import numpy as np
import pygame

# ====================== НАСТРОЙКИ ======================
NAME = "РОЗАЛИНОЧКА"
SUBTITLE = ""                 # например "МОЯ ЛЮБИМАЯ" (пусто = без подписи)
COLS, ROWS = 180, 100         # разрешение "картинки" в символах
CW, CH = 6, 8                 # размер символа в пикселях окна
FPS = 60
CHARS = " .,:;-~=+*xo#%&@"    # от тёмного к яркому

rnd = random.Random(14)
nprng = np.random.default_rng(14)

pygame.init()
W, H = COLS * CW, ROWS * CH
try:
    screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
except Exception:
    screen = pygame.display.set_mode((W, H))
pygame.display.set_caption(NAME)
clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas,dejavusansmono,menlo,couriernew,monospace", CH + 1, bold=True)

scene = pygame.Surface((COLS, ROWS), 0, 32)   # маленький холст, на нём рисуем

# ====================== ГЕОМЕТРИЯ И ТАЙМИНГ ======================
CX = COLS // 2
HEART_CY = 38
NAME_CY = 46
GROUND_Y = 84
HS = 3.8                      # масштаб большого сердца

T_HEART = 0.3                 # начало рисования большого сердца
T_NAME = 1.6                  # имя начинает проявляться
NAME_DUR = 2.6
T_KISS = 3.0                  # начинаются поцелуйчики-штампы
T_FW = 5.0                    # начинается салют
STAMP_LIFE = 3.6


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


def make_surf(col, alpha):
    """col: (W,H,3), alpha: (W,H) 0..1  ->  Surface с прозрачностью"""
    wd, hd = alpha.shape
    s = pygame.Surface((wd, hd), pygame.SRCALPHA)
    a3 = pygame.surfarray.pixels3d(s)
    a3[:] = np.clip(col, 0, 255).astype(np.uint8)
    del a3
    aa = pygame.surfarray.pixels_alpha(s)
    aa[:] = (np.clip(alpha, 0, 1) * 255).astype(np.uint8)
    del aa
    return s


def beat(t):
    """двойной удар сердца"""
    p = (t % 1.1) / 1.1
    return max(math.exp(-((p - 0.08) / 0.05) ** 2), 0.65 * math.exp(-((p - 0.30) / 0.06) ** 2))


LUMW = np.array([0.299, 0.587, 0.114], np.float32)

# ====================== ПАЛИТРЫ ======================
HC = [(235, 30, 60), (255, 70, 130), (255, 125, 175), (210, 30, 140),
      (255, 175, 205), (170, 60, 220), (255, 205, 90), (255, 45, 90)]

LIP_PAL = [  # тёмный, средний, светлый
    ((110, 0, 12), (190, 18, 30), (235, 70, 80)),       # классика
    ((140, 5, 50), (225, 40, 110), (255, 120, 170)),    # розовая
    ((120, 0, 70), (200, 25, 130), (250, 110, 200)),    # малиновая
    ((90, 0, 20), (160, 10, 40), (215, 50, 70)),        # бордо
    ((150, 20, 30), (235, 70, 60), (255, 150, 130)),    # коралл
]
ROSE_COL = [(215, 25, 50), (245, 75, 135), (175, 10, 65), (245, 100, 95), (250, 185, 215)]
STREAKS = [(-0.66, 0), (-0.40, 1), (-0.22, 0), (0.12, 0), (0.40, 1), (0.58, 0), (0.74, 0), (-0.08, 1)]


# ====================== СПРАЙТЫ (рисуем формулами) ======================
def heart_sprite(wd, base):
    hd = max(3, int(round(wd * 0.75)))                 # 0.75 - поправка на "высокие" пиксели
    x = (-1.25 + (np.arange(wd) + 0.5) / wd * 2.5).astype(np.float32)[:, None]
    y = (1.35 - (np.arange(hd) + 0.5) / hd * 2.5).astype(np.float32)[None, :]
    f = (x * x + y * y - 1) ** 3 - x * x * y ** 3
    if wd <= 9:
        alpha = (f <= 0).astype(np.float32)
    else:
        alpha = np.clip(0.5 - f * wd / 4.0, 0, 1)
    d = np.clip(-f, 0, 1)
    k = 0.60 + 0.40 * np.sqrt(d) + 0.10 * y
    hl = np.exp(-(((x + 0.5) / 0.30) ** 2 + ((y - 0.65) / 0.22) ** 2)) * 0.85
    hl2 = np.exp(-(((x - 0.45) / 0.22) ** 2 + ((y - 0.55) / 0.14) ** 2)) * 0.35
    hl = np.clip(hl + hl2, 0, 1)
    col = np.array(base, np.float32)[None, None, :] * k[..., None]
    col = col + (255 - col) * hl[..., None]
    return make_surf(col, alpha)


def lips_sprite(wd, pal_i):
    hd = max(4, int(round(wd * 0.4219)))
    u = (-1.04 + (np.arange(wd) + 0.5) / wd * 2.08).astype(np.float32)[:, None]
    y = (0.52 - (np.arange(hd) + 0.5) / hd * 1.17).astype(np.float32)[None, :]
    au = np.abs(u)
    q = np.clip(1 - u * u, 0, 1)
    m = -0.02 + 0.10 * u * u + 0.05 * u                       # линия рта (чуть наклонена)
    gp = 0.045 * np.sqrt(q)                                   # щель между губами
    top = m + 0.40 * q ** 0.7 + 0.09 * np.exp(-((au - 0.33) / 0.18) ** 2) - 0.14 * np.exp(-(u / 0.10) ** 2)
    bot = m - 0.05 - 0.52 * q ** 0.65
    ub, lb = m + gp, m - gp
    e = 1.17 / hd

    up_a = np.clip((top - y) / e + 0.5, 0, 1) * np.clip((y - ub) / e + 0.5, 0, 1)
    lo_a = np.clip((lb - y) / e + 0.5, 0, 1) * np.clip((y - bot) / e + 0.5, 0, 1)
    alpha = np.maximum(up_a, lo_a)

    upper = y >= m
    tu = np.clip((y - ub) / (top - ub + 1e-6), 0, 1)
    tl = np.clip((y - bot) / (lb - bot + 1e-6), 0, 1)
    t = np.where(upper, tu, tl)

    sh = np.sin(np.pi * t) ** 0.6
    k = np.where(upper, 0.30 + 0.50 * sh, 0.42 + 0.68 * sh) * (1 - 0.30 * au ** 2)
    k = k + 0.07 * np.sin(u * 7 + y * 5) + 0.06 * np.sin(u * 13 - y * 11 + 2) + 0.05 * np.sin(u * 23 + y * 17 + 4)

    def blob(cu, cy_, su, sy_, st):
        return st * np.exp(-(((u - cu) / su) ** 2 + ((y - cy_) / sy_) ** 2))

    ymid_l = bot + 0.62 * (lb - bot)
    ymid_u = ub + 0.80 * (top - ub)
    hl = blob(-0.15, ymid_l, 0.38, 0.07, 0.55) + blob(0.50, ymid_l, 0.15, 0.06, 0.35)
    hl = hl + blob(-0.33, ymid_u, 0.13, 0.05, 0.45) + blob(0.33, ymid_u, 0.13, 0.05, 0.45)
    sig = max(0.014, 1.0 / wd)
    win = np.sin(np.pi * np.clip((t - 0.12) / 0.76, 0, 1))
    for su_, up_ in STREAKS:                                  # глянцевые штрихи
        shift = 0.12 * (t - 0.5)
        mw = upper if up_ else ~upper
        hl = hl + 0.55 * np.exp(-(((u - su_ - shift) / sig) ** 2)) * win * mw
    hl = hl + np.where(~upper, 0.30 * np.exp(-((1 - t) / 0.10) ** 2), 0)   # кромка у щели

    dk, md, lt = [np.array(c, np.float32) for c in LIP_PAL[pal_i]]
    f1 = np.clip(k / 0.7, 0, 1)[..., None]
    f2 = np.clip((k - 0.7) / 0.45, 0, 1)[..., None] * 0.85
    col = dk + (md - dk) * f1
    col = col + (lt - col) * f2
    col = col + (255 - col) * np.clip(hl, 0, 0.92)[..., None]
    return make_surf(col, alpha)


def rose_sprite(wd, base):
    hd = max(4, int(round(wd * 0.75)))
    x = ((np.arange(wd) + 0.5) / wd * 2 - 1).astype(np.float32)[:, None]
    y = ((np.arange(hd) + 0.5) / hd * 2 - 1).astype(np.float32)[None, :]
    r = np.sqrt(x * x + y * y)
    th = np.arctan2(y, x)
    pat = 0.5 + 0.5 * np.sin(3 * th + 11 * r)                 # спираль лепестков
    line = np.exp(-(pat / 0.16) ** 2)
    k = 0.60 + 0.55 * pat - 0.45 * line
    k = k * (1.0 - 0.30 * r) + 0.20 * np.exp(-(((x + 0.35) / 0.4) ** 2 + ((y + 0.4) / 0.35) ** 2))
    k = k * np.where(r > 0.82, 0.7, 1.0)
    col = np.array(base, np.float32)[None, None, :] * k[..., None]
    col = col + (255 - col) * (0.25 * pat ** 4)[..., None]
    alpha = np.clip((1 - r) / 0.14, 0, 1) if wd > 10 else (r <= 1).astype(np.float32)
    return make_surf(col, alpha)


_HS, _LS, _RS = {}, {}, {}


def get_heart(wd, ci):
    k = (wd, ci)
    if k not in _HS:
        _HS[k] = heart_sprite(wd, HC[ci])
    return _HS[k]


def get_lips(wd, pi, ang=0, flip=False):
    key = (wd, pi, ang, flip)
    if key not in _LS:
        s = lips_sprite(wd, pi)
        if flip:
            s = pygame.transform.flip(s, True, False)
        if ang:
            s = pygame.transform.rotozoom(s, ang, 1.0)
        _LS[key] = s
    return _LS[key]


def get_rose(wd, ci):
    k = (wd, ci)
    if k not in _RS:
        _RS[k] = rose_sprite(wd, ROSE_COL[ci])
    return _RS[k]


# ====================== РОЗЫ ======================
ROSES = []   # (cx, cy, ширина, цвет, время появления)


def plan_roses():
    x = 4
    while x < COLS:
        ROSES.append([x + rnd.randint(-2, 2), GROUND_Y + rnd.randint(2, 5), rnd.choice([12, 14, 16]), rnd.randrange(5)])
        x += rnd.randint(11, 15)
    x = 10
    while x < COLS:
        ROSES.append([x + rnd.randint(-3, 3), GROUND_Y + rnd.randint(9, 12), rnd.choice([18, 21, 24]), rnd.randrange(5)])
        x += rnd.randint(17, 24)
    ROSES.sort(key=lambda r: r[1])
    for r in ROSES:
        r.append(0.4 + r[0] / COLS * 3.0 + rnd.uniform(0, 0.5))


plan_roses()


def draw_leaf(surf, cx, cy, ang, L):
    ca, sa = math.cos(ang), math.sin(ang)
    tip = (cx + L * ca, cy + L * 0.75 * sa)
    mid = (cx + 0.5 * L * ca, cy + 0.5 * L * 0.75 * sa)
    w = 0.30 * L
    s1 = (mid[0] - sa * w, mid[1] + ca * w * 0.75)
    s2 = (mid[0] + sa * w, mid[1] - ca * w * 0.75)
    pygame.draw.polygon(surf, (22, 105, 52), [(cx, cy), s1, tip, s2])
    pygame.draw.line(surf, (70, 175, 95), (cx, cy), tip)


# ====================== ФОН ======================
def build_background():
    k = (np.minimum(np.arange(ROWS), GROUND_Y) / GROUND_Y).astype(np.float32)[None, :] ** 1.4
    c0 = np.array([18, 4, 42], np.float32)
    c1 = np.array([170, 36, 108], np.float32)
    arr = np.broadcast_to(c0 + (c1 - c0) * k[..., None], (COLS, ROWS, 3)).copy()

    xb = np.arange(COLS, dtype=np.float32)[:, None]
    yb = np.arange(ROWS, dtype=np.float32)[None, :]
    for _ in range(36):                                   # боке
        bx, by = rnd.uniform(0, COLS), rnd.uniform(0, GROUND_Y)
        r = rnd.uniform(3, 10)
        d = np.sqrt((xb - bx) ** 2 + ((yb - by) * 1.333) ** 2)
        c = np.array(rnd.choice([(255, 90, 160), (200, 90, 255), (255, 170, 90), (255, 120, 200)]), np.float32)
        arr += c * (0.05 * (d < r) + 0.10 * np.exp(-((d - r) / 1.1) ** 2))[..., None]

    for x in range(COLS):                                 # живая изгородь
        top = int(GROUND_Y + 1.5 * math.sin(x * 0.17) + 1.2 * math.sin(x * 0.41))
        for y in range(top, ROWS):
            n = rnd.uniform(-8, 8) + 8 * math.sin(x * 0.5 + y * 0.9)
            kk = (y - top) / max(1, ROWS - top)
            arr[x, y] = (14 + n * 0.3 - 6 * kk, 58 + n - 25 * kk, 36 + n * 0.5 - 12 * kk)
        arr[x, top] = (60, 150, 80)

    surf = pygame.surfarray.make_surface(np.clip(arr, 0, 255).astype(np.uint8))

    # огромные полупрозрачные сердца на заднем плане
    for bx, by, bw, ci in [(24, 28, 54, 3), (152, 24, 62, 1), (100, 12, 40, 7), (60, 60, 36, 5), (135, 62, 34, 2)]:
        spr = heart_sprite(bw, HC[ci]).copy()
        spr.set_alpha(38)
        surf.blit(spr, (bx - bw // 2, by - spr.get_height() // 2))

    # листья под розами
    for cx, cy, wd, ci, ts in ROSES:
        for _ in range(3):
            draw_leaf(surf, cx, cy, rnd.uniform(-3.0, -0.1), rnd.uniform(0.55, 0.85) * wd)
    return surf


bg = build_background()
stars = []
while len(stars) < 110:
    x, y = rnd.randrange(1, COLS - 1), rnd.randrange(1, 50)
    stars.append((x, y, rnd.uniform(0, 6.28), rnd.random() < 0.15, rnd.randrange(3)))
STAR_COLS = [(255, 255, 255), (255, 190, 225), (255, 225, 150)]

# ====================== ЛЕТАЮЩИЕ СЕРДЕЧКИ И ПОЦЕЛУЙЧИКИ ======================
HEART_SIZES = [5, 7, 9, 12, 16, 22, 30]
HEART_WGT = [4, 5, 5, 4, 3, 2, 1]
LIP_SIZES = [14, 18, 24, 30, 38]
floaters = []
stamps = []
pops = []


def make_floater(kind, t0):
    if kind == 'h':
        wd = rnd.choices(HEART_SIZES, HEART_WGT)[0]
        ci = rnd.randrange(len(HC))
        spr = get_heart(wd, ci)
        v = (0.10 + 0.013 * wd) * rnd.uniform(0.8, 1.25)
        amp = rnd.uniform(1.0, 3.5) * (0.5 + wd / 18)
    else:
        wd = rnd.choice(LIP_SIZES)
        ci = rnd.randrange(len(LIP_PAL))
        spr = get_lips(wd, ci, rnd.choice((-35, -20, -10, 0, 10, 20, 35)), rnd.random() < 0.5)
        v = (0.08 + 0.006 * wd) * rnd.uniform(0.8, 1.25)
        amp = rnd.uniform(1.5, 4.0)
    return dict(k=kind, x=rnd.uniform(0, COLS), y=ROWS + spr.get_height() + rnd.uniform(0, 25),
                v=v, ph=rnd.uniform(0, 6.28), amp=amp, fr=rnd.uniform(0.6, 1.6), spr=spr, t0=t0)


def init_floaters():
    floaters.clear()
    stamps.clear()
    pops.clear()
    for _ in range(72):
        floaters.append(make_floater('h', rnd.uniform(0.4, 9.0)))
    for _ in range(20):
        floaters.append(make_floater('k', rnd.uniform(2.0, 10.0)))


def pop_hearts(x, y, n):
    for _ in range(n):
        a = rnd.uniform(0, 6.283)
        sp = rnd.uniform(0.6, 2.0)
        pops.append(dict(x=x, y=y, vx=math.cos(a) * sp, vy=math.sin(a) * sp * 0.8 - 0.4,
                         life=rnd.uniform(1.0, 1.8), w=rnd.choice((7, 9, 12)), ci=rnd.randrange(len(HC))))


def add_stamp(t, x=None, y=None):
    x = rnd.uniform(24, COLS - 24) if x is None else x
    y = rnd.uniform(14, GROUND_Y - 10) if y is None else y
    stamps.append(dict(x=x, y=y, t0=t, w=rnd.choice((34, 42, 50, 58)), pi=rnd.randrange(len(LIP_PAL)),
                       ang=rnd.choice((-30, -20, -10, 10, 20, 30)), flip=rnd.random() < 0.5))
    FW.sparks(x, y, 26, 1.1)
    pop_hearts(x, y, 7)


# ====================== СТАТИЧНЫЕ МАССИВЫ ======================
XX = np.arange(COLS, dtype=np.float32)[:, None]
YY = np.arange(ROWS, dtype=np.float32)[None, :]
XI = np.arange(COLS)[:, None]
YI = np.arange(ROWS)[None, :]
SKY_MASK = np.clip((60 - YY) / 14, 0, 1).astype(np.float32)
VIG = np.clip(1 - 0.5 * (((XX - COLS / 2) / (COLS * 0.62)) ** 2 + ((YY - ROWS / 2) / (ROWS * 0.75)) ** 2), 0.45, 1.0)
VIG = VIG[..., None].astype(np.float32)
HEART_GLOW = (np.exp(-(((XX - CX) / 55) ** 2 + ((YY - 44) / 36) ** 2))[..., None] *
              np.array([95, 14, 70], np.float32)).astype(np.float32)

# лепестки
NPET = 300
px = nprng.uniform(0, COLS, NPET).astype(np.float32)
py = nprng.uniform(0, ROWS, NPET).astype(np.float32)
pv = nprng.uniform(0.10, 0.50, NPET).astype(np.float32)
pph = nprng.uniform(0, 6.28, NPET).astype(np.float32)
PET_COLS = np.array([(255, 60, 110), (255, 140, 185), (230, 30, 70), (255, 225, 235), (255, 110, 60)], np.float32)
pcol = PET_COLS[nprng.integers(0, 5, NPET)]
pbr = (0.55 + 0.45 * (pv - 0.1) / 0.4).astype(np.float32)

# большое сердце из точек
HA = np.linspace(0, 2 * np.pi, 300, endpoint=False)
HX_ = 16 * np.sin(HA) ** 3
HY_ = -(13 * np.cos(HA) - 5 * np.cos(2 * HA) - 2 * np.cos(3 * HA) - np.cos(4 * HA))
HEART_LAYERS = [(1.0, np.array([255, 50, 120], np.float32), 0.0),
                (0.9, np.array([255, 130, 185], np.float32), 1.3),
                (0.8, np.array([255, 215, 235], np.float32), 2.6)]


def waves(t):
    fade = min(1.0, t / 3.0)
    c = 24 + 7 * np.sin(XX * 0.05 + t * 0.4) + 3 * np.sin(XX * 0.14 - t * 0.6)
    band = np.exp(-((YY - c) / 6.0) ** 2)
    cur = 0.55 + 0.45 * np.sin(XX * 0.2 + t * 0.9 + np.sin(XX * 0.05) * 2)
    a = band * cur * 0.45 * fade * SKY_MASK
    b = np.exp(-((YY - (c + 9)) / 4.0) ** 2) * (0.5 + 0.5 * np.sin(XX * 0.15 - t * 0.7)) * 0.3 * fade * SKY_MASK
    hue = 0.5 + 0.5 * np.sin(XX * 0.03 + t * 0.2)
    ca = np.array([255, 60, 150], np.float32) * (1 - hue)[..., None] + np.array([150, 70, 255], np.float32) * hue[..., None]
    return a[..., None] * ca + b[..., None] * np.array([255, 150, 90], np.float32)


def splat(buf, xs, ys, cols, k=1.0):
    """билинейно рисуем точки в буфер (быстро, через bincount)"""
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
        buf[:, :, c] += np.bincount(idx, weights=w, minlength=COLS * ROWS).reshape(COLS, ROWS)


# ====================== ИМЯ (маски букв) ======================
def dilate(m, r):
    out = m.copy()
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r + 1:
                out = np.maximum(out, np.roll(np.roll(m, dx, 0), dy, 1))
    return out


def blur(m, r):
    out = np.zeros_like(m)
    n = 0
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            out += np.roll(np.roll(m, dx, 0), dy, 1)
            n += 1
    return out / n


def build_name_layers():
    fnt = pygame.font.SysFont("arial,segoeui,dejavusans,verdana,tahoma,freesans,liberationsans", 140, bold=True)
    M = np.zeros((COLS, ROWS), np.float32)
    blocks = [(NAME, 0.84, NAME_CY)]
    if SUBTITLE:
        blocks.append((SUBTITLE, 0.50, NAME_CY + 16))
    xmin, xmax, ymin, ymax = COLS, 0, ROWS, 0
    for text, frac, cy in blocks:
        surf = fnt.render(text, True, (255, 255, 255), (0, 0, 0)).convert()
        sw, sh = surf.get_size()
        tw = min(COLS - 4, int(COLS * frac))
        th = max(4, int(sh * tw / sw * 0.75))
        small = pygame.transform.smoothscale(surf, (tw, th))
        a = np.clip(pygame.surfarray.array3d(small)[:, :, 0].astype(np.float32) / 255 * 1.5, 0, 1)
        x0 = (COLS - tw) // 2
        y0 = int(cy - th / 2)
        M[x0:x0 + tw, y0:y0 + th] = np.maximum(M[x0:x0 + tw, y0:y0 + th], a)
        xmin, xmax = min(xmin, x0), max(xmax, x0 + tw)
        ymin, ymax = min(ymin, y0), max(ymax, y0 + th)
    cut = np.clip(dilate(M, 2), 0, 1)
    halo = np.clip(blur(dilate(M, 3), 3) * 1.4, 0, 1)
    rt = np.clip(M - np.roll(M, 1, 1), 0, 1)       # верхняя кромка букв (блик)
    rb = np.clip(M - np.roll(M, -1, 1), 0, 1)      # нижняя кромка (тень)
    L = np.stack([M, cut, halo, rt, rb]).astype(np.float32)
    return L, xmin, xmax - xmin, ymin, ymax - ymin


NAME_L, NAME_X0, NAME_TW, NAME_Y0, NAME_TH = build_name_layers()
WINE = np.array([50, 0, 30], np.float32)
NAME_TOP = np.array([255, 240, 250], np.float32)
NAME_BOT = np.array([255, 70, 150], np.float32)
GOLD = np.array([255, 200, 90], np.float32)


def draw_name(pix, t):
    if t < T_NAME:
        return pix
    off = np.round(0.9 * np.sin(t * 2.0 + XX[:, 0] * 0.12)).astype(np.intp)
    idx = np.clip(YI - off[:, None], 0, ROWS - 1)
    L = NAME_L[:, XI, idx]                                         # (5, COLS, ROWS) с волной
    rx = NAME_X0 - 3 + (t - T_NAME) / NAME_DUR * (NAME_TW + 8)
    L = L * np.clip((rx - XX) / 3.0, 0, 1)[None]                   # проявление слева направо
    body, cut, halo, rt, rb = L

    pix = pix * (1 - 0.55 * halo)[..., None]
    pix = pix * (1 - 0.85 * cut)[..., None] + (0.85 * cut)[..., None] * WINE

    yf = np.clip((YY - NAME_Y0) / max(1, NAME_TH), 0, 1)
    base = NAME_TOP * (1 - yf)[..., None] + NAME_BOT * yf[..., None]
    g = (0.5 + 0.5 * np.sin(XX * 0.09 - t * 2.0)) * 0.45
    col = base * (1 - g)[..., None] + GOLD * g[..., None]
    d = XX + YY * 0.8 - ((t * 50) % (COLS + 140) - 40)
    col = col + (np.exp(-(d / 7.0) ** 2) * 120)[..., None]         # бегущий блик
    col = col + rt[..., None] * 90
    col = col * (1 - 0.35 * rb)[..., None] * (0.93 + 0.10 * beat(t))
    sp = nprng.random((COLS, ROWS)) < 0.018                        # мерцающие искорки
    col = col + sp[..., None] * 190
    return pix * (1 - body)[..., None] + col * body[..., None]


# ====================== САЛЮТ ======================
iX, iY, iVX, iVY, iLIFE, iMAXL, iR, _g, _b, iPH, iTW, iDRAG, iGRAV = range(13)
NC = 13

_PAL = [((255, 60, 120), (255, 220, 230)), ((255, 50, 60), (255, 200, 120)),
        ((255, 100, 220), (140, 200, 255)), ((190, 100, 255), (255, 150, 200)),
        ((255, 200, 90), (255, 80, 120)), ((255, 255, 255), (255, 150, 190))]
PALETTES = [(np.array(a, np.float32), np.array(b, np.float32)) for a, b in _PAL]
KINDS = ['heart', 'heart', 'heart', 'peony', 'peony', 'ring', 'star', 'willow', 'spiral', 'glitter']
SPARK_COLS = np.array([(255, 120, 170), (255, 255, 255), (255, 210, 120), (255, 70, 120)], np.float32)


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
        self.buf = np.zeros((COLS, ROWS, 3), np.float32)
        self.new = []
        self.rockets = []
        self.flashes = []
        self.next_launch = T_FW
        self.next_finale = T_FW + 16
        self.finale = 0

    def sparks(self, x, y, n, speed=1.2, up=0.0, life=(0.8, 1.4)):
        th = nprng.uniform(0, 6.283, n)
        sp = nprng.uniform(0.2, speed, n)
        col = SPARK_COLS[nprng.integers(0, 4, n)]
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
                parts.append(make_particles(x, y, hx * sc, hy * sc * 0.8, col, 2.0, 0.94, 0.01))
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
            col = np.array([255, 185, 110], np.float32) * r.uniform(0.75, 1.1, (n, 1))
            parts.append(make_particles(x, y, np.cos(th) * sp, np.sin(th) * sp - 0.25, col,
                                        r.uniform(2.6, 3.8, n), 0.955, 0.016))
        elif kind == 'spiral':
            for arm, col in ((0.0, c1), (3.14159, c2)):
                n = 90
                u = np.linspace(0.05, 1, n)
                th = u * 12.5 + arm
                sp = 0.25 + 1.65 * u
                parts.append(make_particles(x, y, np.cos(th) * sp, np.sin(th) * sp, col, 2.0, 0.935, 0.012))
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
                self.next_launch = t + random.uniform(0.6, 1.6)
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
            splat(self.buf, np.array([rk[0]]), np.array([rk[1]]), np.array([[255, 220, 160]], np.float32), 0.9)
            ns = 2
            self.new.append(make_particles(rk[0] + nprng.normal(0, 0.3, ns), rk[1],
                                           nprng.normal(0, 0.12, ns), nprng.uniform(0.1, 0.5, ns),
                                           np.array([255, 170, 110], np.float32),
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
            splat(self.buf, P[:, iX], P[:, iY], P[:, iR:iR + 3] * b[:, None], 0.65 * f)
        if self.new:
            P = np.vstack([P] + self.new) if len(P) else np.vstack(self.new)
            self.new = []
        self.PA = P


FW = Fireworks()
init_floaters()


# ====================== РИСУЕМ СЦЕНУ ======================
def draw_scene(t, dt):
    f = dt * 30
    scene.blit(bg, (0, 0))

    # звёзды
    for x, y, ph, big, ci in stars:
        b = max(0.15, min(1.0, 0.55 + 0.45 * math.sin(t * 2.2 + ph)))
        c = mul(STAR_COLS[ci], b)
        scene.set_at((x, y), c)
        if big and b > 0.8:
            c2 = mul(c, 0.5)
            for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                scene.set_at((x + ox, y + oy), c2)

    # летящие сердечки и поцелуйчики (мелкие сзади, крупные спереди)
    for fl in floaters:
        if t < fl['t0']:
            continue
        fl['y'] -= fl['v'] * f
        if fl['y'] < -fl['spr'].get_height():
            fl.update(make_floater(fl['k'], 0.0))
    for fl in sorted(floaters, key=lambda q: q['spr'].get_width()):
        if t < fl['t0']:
            continue
        x = fl['x'] + fl['amp'] * math.sin(t * fl['fr'] + fl['ph'])
        spr = fl['spr']
        scene.blit(spr, (int(x - spr.get_width() / 2), int(fl['y'] - spr.get_height() / 2)))

    # поцелуйчики-штампы: выскакивают, держатся, тают
    for s in stamps[:]:
        age = t - s['t0']
        if age > STAMP_LIFE:
            stamps.remove(s)
            continue
        p = ease_out_back(age / 0.5)
        base = get_lips(s['w'], s['pi'], s['ang'], s['flip'])
        bw, bh = base.get_size()
        fade = clamp01((STAMP_LIFE - age) / 0.9)
        if age > 0.5 and fade >= 1:
            spr = base
        else:
            spr = pygame.transform.smoothscale(base, (max(2, int(bw * p)), max(2, int(bh * p))))
            if fade < 1:
                spr.set_alpha(int(255 * fade))
        scene.blit(spr, (int(s['x'] - spr.get_width() / 2), int(s['y'] - spr.get_height() / 2)))

    # розы
    for cx, cy, wd, ci, ts in ROSES:
        p = (t - ts) / 0.8
        if p <= 0:
            continue
        base = get_rose(wd, ci)
        bw, bh = base.get_size()
        if p >= 1:
            scene.blit(base, (cx - bw // 2, cy - bh // 2))
        else:
            s = ease_out_back(p)
            sw, sh = max(2, int(bw * s)), max(2, int(bh * s))
            scene.blit(pygame.transform.smoothscale(base, (sw, sh)), (cx - sw // 2, cy - sh // 2))

    # сердечки-брызги
    for p in pops[:]:
        p['life'] -= dt
        if p['life'] <= 0:
            pops.remove(p)
            continue
        p['vx'] *= 0.95 ** f
        p['vy'] = p['vy'] * 0.95 ** f - 0.012 * f
        p['x'] += p['vx'] * f
        p['y'] += p['vy'] * f
        spr = get_heart(p['w'] if p['life'] > 0.5 else 5, p['ci'])
        scene.blit(spr, (int(p['x'] - spr.get_width() / 2), int(p['y'] - spr.get_height() / 2)))


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
    return np.maximum(m, 55)       # 55 - цветная подложка за символом


MASKS = make_masks()
MASK3 = np.zeros((W, H, 3), np.uint8)
mask_surf = pygame.Surface((W, H))


def bloom(pix):
    b = np.clip(pix - 150, 0, 255).astype(np.uint8)
    s = pygame.surfarray.make_surface(b)
    out = 0
    for dv, k in ((3, 0.9), (8, 1.4)):
        small = pygame.transform.smoothscale(s, (COLS // dv, ROWS // dv))
        back = pygame.transform.smoothscale(small, (COLS, ROWS))
        out = out + pygame.surfarray.array3d(back).astype(np.float32) * k
    return out


def tone(pix, sat=1.6):
    m = pix.max(axis=2, keepdims=True)
    pix = pix / np.maximum(1.0, m / 255.0)          # пересвет не уводит в белый
    g = (pix @ LUMW)[..., None]
    pix = g + (pix - g) * sat                       # насыщенность
    return np.clip(pix, 0, 255)


def to_ascii(pix):
    lum = pix @ LUMW / 255.0
    v = np.clip((lum - 0.04) / 0.96, 0, 1)
    idx = np.minimum((v * (NCH - 1) + 0.5).astype(np.intp), NCH - 1)
    mx = pix.max(axis=2, keepdims=True)
    col = pix / np.maximum(mx, 1.0) * 255 * (0.5 + 0.5 * mx / 255)   # чистый яркий цвет
    col = np.clip(col, 0, 255).astype(np.uint8)
    big = pygame.transform.scale(pygame.surfarray.make_surface(col), (W, H))
    m = MASKS[idx].transpose(0, 2, 1, 3).reshape(W, H)
    MASK3[:] = m[:, :, None]
    pygame.surfarray.blit_array(mask_surf, MASK3)
    big.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    screen.blit(big, (0, 0))


def compose(t, dt):
    global px, py
    f = dt * 30
    pix = pygame.surfarray.array3d(scene).astype(np.float32)

    pix += waves(t)
    b = beat(t)
    pix += HEART_GLOW * (0.7 + 0.3 * b) * clamp01((t - T_HEART) / 2.0)

    # падающие лепестки
    py = (py + pv * f) % ROWS
    px = (px + (np.sin(t * 1.7 + pph) * 0.25 + 0.05) * f) % COLS
    ix = px.astype(np.int32) % COLS
    iy = np.clip(py.astype(np.int32), 0, ROWS - 1)
    val = pcol * pbr[:, None]
    pix[ix, iy] = np.maximum(pix[ix, iy], val)
    bf = pv > 0.3
    jx = (ix[bf] + 1) % COLS
    pix[jx, iy[bf]] = np.maximum(pix[jx, iy[bf]], val[bf] * 0.6)

    # большое бьющееся сердце из точек
    frac = clamp01((t - T_HEART) / 2.2)
    if frac > 0:
        ov = np.zeros((COLS, ROWS, 3), np.float32)
        vis = np.abs(HA - np.pi) <= frac * np.pi
        for sc_, col_, ph_ in HEART_LAYERS:
            s_ = HS * sc_ * (1 + 0.045 * b)
            xs = (CX + HX_[vis] * s_).astype(np.float32)
            ys = (HEART_CY + HY_[vis] * s_ * 0.75).astype(np.float32)
            tw_ = 0.6 + 0.4 * np.sin(t * 4 + HA[vis] * 6 + ph_)
            splat(ov, xs, ys, col_[None, :] * (tw_[:, None] * 1.5).astype(np.float32), 1.0)
        pix += ov

    # имя
    pix = draw_name(pix, t).astype(np.float32)

    # вспышки салюта: цветная подсветка
    amb = np.zeros(3, np.float32)
    for fx_, fy_, c, k in FW.flashes:
        amb += c / 255.0 * k
    pix *= 1.0 + 0.2 * np.minimum(amb, 1.4)
    for fx_, fy_, c, k in FW.flashes:
        d2 = (XX - fx_) ** 2 + (YY - fy_) ** 2
        pix += (np.exp(-d2 / (2 * 16.0 ** 2)) * (k * 0.3))[..., None] * c

    pix += FW.buf
    pix += bloom(pix) * 0.35
    pix *= VIG
    pix = tone(pix.astype(np.float32))
    to_ascii(pix)


# ====================== ГЛАВНЫЙ ЦИКЛ ======================
def reset():
    global t
    t = 0.0
    FW.reset()
    init_floaters()
    next_stamp[0] = T_KISS


t = 0.0
next_stamp = [T_KISS]
running = True
frames = 0
while running:
    dt = min(clock.tick(FPS) / 1000.0, 0.05)
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        elif e.type == pygame.MOUSEBUTTONDOWN:
            if e.button == 1:
                FW.launch(e.pos[0] / CW, e.pos[1] / CH)           # ЛКМ: ракета в эту точку
            elif e.button == 3:
                add_stamp(t, e.pos[0] / CW, e.pos[1] / CH)        # ПКМ: поцелуй в этой точке
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                running = False
            elif e.key == pygame.K_r:
                reset()
            elif e.key == pygame.K_s:
                pygame.image.save(screen, "rozalinochka.png")
            elif e.key == pygame.K_f:
                FW.launch()
            elif e.key == pygame.K_k:
                add_stamp(t)
            elif e.key == pygame.K_h:
                pop_hearts(CX, HEART_CY + 10, 30)
            elif e.key == pygame.K_SPACE:
                FW.finale = 16
                FW.next_launch = t
            elif e.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
    t += dt

    # искры по ходу проявления имени
    if T_NAME < t < T_NAME + NAME_DUR:
        rx = NAME_X0 - 3 + (t - T_NAME) / NAME_DUR * (NAME_TW + 8)
        FW.sparks(rx, NAME_Y0 + nprng.uniform(0, NAME_TH, 4), 4, 0.9)

    # автоматические поцелуйчики-штампы
    if t >= next_stamp[0]:
        if len(stamps) < 9:
            add_stamp(t)
        next_stamp[0] = t + rnd.uniform(0.6, 1.3)

    draw_scene(t, dt)
    FW.update(t, dt)
    compose(t, dt)
    pygame.display.flip()
    frames += 1
    if frames % 30 == 0:
        pygame.display.set_caption(f"{NAME}   {clock.get_fps():.0f} FPS")

pygame.quit()