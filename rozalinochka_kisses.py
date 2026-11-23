import math, random, sys
import numpy as np
import pygame

# ============ НАСТРОЙКИ ============
NAME = "Розалиночка"
COLS, ROWS = 170, 96          # сетка символов
CW, CH = 6, 8                 # размер одного символа в пикселях
FPS = 60
CHARS = " .,:;-~=+*xo#%&@"
MAX_LIPS = 70                 # максимум губ на экране
SPAWN = (0.07, 0.16)          # пауза между новыми губами (сек), меньше = больше губ
LIFE = (2.2, 3.6)             # сколько живёт один поцелуй (сек)
AVOID_NAME = 0.75             # 0 = губы везде, 1 = обходят имя
# ===================================

W, H = COLS * CW, ROWS * CH
NCH = len(CHARS)

pygame.init()
pygame.display.set_caption("Розалиночка")
screen = pygame.display.set_mode((W, H), pygame.SCALED)
clock = pygame.time.Clock()


# ---------- символы ----------
def build_atlas():
    font = pygame.font.SysFont(
        "consolas,couriernew,dejavusansmono,liberationmono,menlo,monospace", 10)
    items = []
    for ch in CHARS:
        surf = pygame.Surface((CW, CH))
        surf.fill((0, 0, 0))
        if ch != " ":
            g = font.render(ch, True, (255, 255, 255))
            surf.blit(g, ((CW - g.get_width()) // 2, (CH - g.get_height()) // 2))
        a = pygame.surfarray.array3d(surf)[:, :, 0].T.astype(np.float32)
        items.append((a.sum(), a))
    items.sort(key=lambda p: p[0])            # от пустого к плотному
    return np.stack([np.clip(a * 1.8, 0, 255) for _, a in items]).astype(np.uint8)


ATLAS = build_atlas()
small = pygame.Surface((COLS, ROWS))
mask_surf = pygame.Surface((W, H))


def to_ascii(pix):
    pix = np.clip(pix, 0, None)
    mx = pix.max(2)
    pix = pix * np.where(mx > 255, 255 / np.maximum(mx, 1), 1.0)[..., None]  # без «белой каши»
    mx = pix.max(2)
    v = mx / 255.0
    idx = (v * (NCH - 1) + 0.5).astype(np.int32)
    col = pix / np.maximum(mx, 1)[..., None] * 255 * (0.5 + 0.5 * v)[..., None]
    pygame.surfarray.blit_array(
        small, np.ascontiguousarray(col.astype(np.uint8).transpose(1, 0, 2)))
    big = pygame.transform.scale(small, (W, H))
    m = ATLAS[idx].transpose(1, 3, 0, 2).reshape(W, H)
    arr = pygame.surfarray.pixels3d(mask_surf)
    arr[:] = m[..., None]
    del arr
    big.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    return big


# ---------- имя ----------
def blur(a, n):
    for _ in range(n):
        a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0) +
             np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5
    return a


def build_name():
    font = pygame.font.SysFont(
        "arial,segoeui,calibri,dejavusans,liberationsans,freesans", 220, bold=True)
    t = font.render(NAME, True, (255, 255, 255))
    surf = pygame.Surface(t.get_size())
    surf.fill((0, 0, 0))
    surf.blit(t, (0, 0))
    tw, th = surf.get_size()
    nw = int(COLS * 0.82)
    nh = max(8, int(th * nw / tw * CW / CH))
    surf = pygame.transform.smoothscale(surf, (nw, nh))
    a = pygame.surfarray.array3d(surf)[:, :, 0].T.astype(np.float32) / 255
    x0, y0 = (COLS - nw) // 2, (ROWS - nh) // 2
    mask = np.zeros((ROWS, COLS), np.float32)
    mask[y0:y0 + nh, x0:x0 + nw] = a
    glow = np.clip(blur(mask, 12) * 1.8, 0, 1)
    return mask, glow, x0, y0, nw, nh


NMASK, NGLOW, NX0, NY0, NW, NH = build_name()
YY, XX = np.mgrid[0:ROWS, 0:COLS].astype(np.float32)
C1 = np.array((255, 35, 135), np.float32)
C2 = np.array((255, 125, 195), np.float32)
CSH = np.array((255, 205, 235), np.float32)
CGL = np.array((255, 30, 120), np.float32)


def name_layer(t):
    p = np.clip((t - 0.3) / 2.2, 0, 1)                 # проявление слева направо
    rev = np.clip((NX0 + p * (NW + 10) - XX) / 5, 0, 1)
    gx = np.clip((XX - NX0) / NW, 0, 1)
    gy = np.clip((YY - NY0) / NH, 0, 1)
    base = C1 + (C2 - C1) * gx[..., None]
    sx = NX0 - 20 + ((t * 38) % (NW + 60))             # бегущий блик
    sh = (np.exp(-((XX - sx) / 6.0) ** 2) * 0.55)[..., None]
    base = base * (1 - sh) + CSH * sh
    shade = (1.0 - 0.38 * gy) * (0.93 + 0.07 * math.sin(t * 3))
    letters = NMASK * shade * rev
    glow = NGLOW * rev * (0.8 + 0.2 * math.sin(t * 2.2))
    return (base * letters[..., None] + CGL * (glow * 0.6)[..., None]).astype(np.float32)


# ---------- губы ----------
LIP_PAL = [
    ((120, 5, 30), (215, 20, 60), (255, 85, 120), (255, 190, 205)),    # красные
    ((140, 0, 50), (235, 25, 95), (255, 100, 155), (255, 200, 225)),   # малиновые
    ((150, 10, 25), (240, 40, 45), (255, 110, 95), (255, 210, 190)),   # коралловые
    ((110, 0, 60), (200, 20, 120), (250, 90, 190), (255, 190, 240)),   # пурпурные
    ((130, 10, 40), (225, 45, 85), (255, 120, 140), (255, 205, 215)),  # розовые
]
TILTS = (-22, 0, 22)
SIZES = [int(round(7 * 1.18 ** i)) for i in range(14)]   # ширина губ в клетках
NL = len(SIZES)


def value_noise(h, w, ch, cw, rng):
    g = rng.random((ch + 1, cw + 1)).astype(np.float32)
    ys, xs = np.linspace(0, ch, h), np.linspace(0, cw, w)
    y0 = np.minimum(ys.astype(int), ch - 1)
    x0 = np.minimum(xs.astype(int), cw - 1)
    fy = (ys - y0)[:, None]
    fx = (xs - x0)[None, :]
    a, b = g[y0][:, x0], g[y0][:, x0 + 1]
    c, d = g[y0 + 1][:, x0], g[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def ramp(s, c0, c1, c2):
    s = np.clip(s, 0, 1)[..., None]
    lo = c0 + (c1 - c0) * np.clip(s * 2, 0, 1)
    hi = c1 + (c2 - c1) * np.clip(s * 2 - 1, 0, 1)
    return np.where(s < 0.5, lo, hi)


def make_lips(w, pal, tilt, seed):
    rng = np.random.default_rng(seed)
    dark, midc, light, gloss = [np.array(c, np.float32) for c in pal]
    ss = 2
    Wc, Hc = int(round(w * 1.3)), int(round(w * 0.86))
    L = w * CW / 2
    px = ((np.arange(Wc * ss) + 0.5) / ss - Wc / 2) * CW / L
    py = ((np.arange(Hc * ss) + 0.5) / ss - Hc / 2) * CH / L
    X, Y = np.meshgrid(px, py)
    a = math.radians(tilt)
    x = X * math.cos(a) + Y * math.sin(a)
    y = -X * math.sin(a) + Y * math.cos(a)
    ax = np.abs(x)

    # форма: «лук Амура», верхняя и нижняя губа, щель между ними
    q = np.clip(1 - ax ** 1.6, 0, 1)
    top = -0.58 * q ** 0.85 + 0.22 * np.exp(-(x / 0.2) ** 2) * q
    bot = 0.66 * np.clip(1 - ax ** 2.2, 0, 1) ** 0.75
    mid = 0.04 * (1 - np.clip(ax, 0, 1) ** 2)
    ins = (ax < 1) & (y > top) & (y < bot)
    up = y < mid

    # объём
    tu = np.clip((y - top) / (mid - top + 1e-4), 0, 1)
    tl = np.clip((y - mid) / (bot - mid + 1e-4), 0, 1)
    s_up = 0.12 + 0.50 * np.sin(np.pi * tu ** 0.9)
    s_lo = 0.18 + 0.72 * np.sin(np.pi * tl ** 0.85)
    s = np.where(up, s_up, s_lo) * (1 - 0.45 * np.clip(ax, 0, 1) ** 2)
    col = ramp(s, dark, midc, light)

    # тёмная щель и контур
    crease = np.exp(-((y - mid) / 0.04) ** 2)
    e = np.clip(np.minimum(y - top, bot - y), 0, None)
    rim = np.exp(-e / 0.04)
    col = col * np.clip(1 - 0.75 * crease - 0.30 * rim, 0.1, 1)[..., None]

    # глянцевые блики-штрихи
    def blob(cx, cy, rx, ry, k):
        return k * np.exp(-(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2))
    g = (blob(-0.15, 0.30, 0.34, 0.06, 0.95) + blob(0.38, 0.24, 0.12, 0.045, 0.7)
         + blob(0.05, 0.52, 0.20, 0.03, 0.4)
         + 0.6 * np.exp(-(((x + 0.30) / 0.2) ** 2 + ((y - top - 0.10) / 0.035) ** 2))
         + 0.35 * np.exp(-(((x - 0.30) / 0.14) ** 2 + ((y - top - 0.10) / 0.03) ** 2)))
    g = np.clip(g, 0, 0.9)[..., None]
    col = col * (1 - g) + gloss * g

    # акварельный шум
    n1 = value_noise(Hc * ss, Wc * ss, 4, 6, rng)
    n2 = value_noise(Hc * ss, Wc * ss, 12, 18, rng)
    col = np.clip(col * (0.80 + 0.40 * n1 + 0.12 * (n2 - 0.5))[..., None], 0, 255)

    # уменьшаем со сглаживанием краёв
    al = ins.astype(np.float32)
    prem = (col * al[..., None]).reshape(Hc, ss, Wc, ss, 3).mean((1, 3))
    al = al.reshape(Hc, ss, Wc, ss).mean((1, 3))
    rgb = prem / np.maximum(al, 1e-3)[..., None]
    return rgb.astype(np.float32), al.astype(np.float32)


print("Рисую губы...")
LIPS = {}
_seed = 0
for lv, w in enumerate(SIZES):
    for pi, pal in enumerate(LIP_PAL):
        for ti, tilt in enumerate(TILTS):
            _seed += 1
            LIPS[(lv, pi, ti)] = make_lips(w, pal, tilt, _seed)


# ---------- поцелуи и искры ----------
stamps, sparks, pending = [], [], []
SPARK_COL = [(255, 60, 150), (255, 120, 190), (255, 190, 80), (255, 80, 90)]
LEVEL_W = [3, 4, 5, 6, 6, 5, 4, 3, 2, 1, 1, 0, 0, 0]


class Stamp:
    def __init__(s, cx, cy, t, k=None):
        s.cx, s.cy, s.t0 = cx, cy, t
        s.k = k if k is not None else random.choices(range(NL), weights=[w + 0.001 for w in LEVEL_W])[0]
        s.pal = random.randrange(len(LIP_PAL))
        s.tilt = random.randrange(len(TILTS))
        s.life = random.uniform(*LIFE)
        s.wob = random.uniform(0, 6.28)


def add_sparks(cx, cy, size):
    for _ in range(10):
        ang = random.uniform(0, 6.283)
        sp = random.uniform(10, 26)
        r = size * 0.35
        sparks.append([cx + math.cos(ang) * r, cy + math.sin(ang) * r * 0.75,
                       math.cos(ang) * sp, math.sin(ang) * sp * 0.75,
                       0.0, random.uniform(0.4, 0.9), random.choice(SPARK_COL)])


def add_stamp(cx, cy, t, k=None):
    if len(stamps) >= MAX_LIPS:
        return
    s = Stamp(cx, cy, t, k)
    stamps.append(s)
    add_sparks(cx, cy, SIZES[s.k])


def rand_pos():
    for _ in range(8):
        x, y = random.uniform(4, COLS - 4), random.uniform(4, ROWS - 4)
        inside = NX0 - 6 < x < NX0 + NW + 6 and NY0 - 8 < y < NY0 + NH + 8
        if not inside or random.random() >= AVOID_NAME:
            break
    return x, y


def queue(n, t, gap=0.05):
    for i in range(n):
        pending.append(t + i * gap)


def blit(pix, rgb, alpha, cx, cy, gain):
    h, w = alpha.shape
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    xa, ya = max(x0, 0), max(y0, 0)
    xb, yb = min(x0 + w, COLS), min(y0 + h, ROWS)
    if xa >= xb or ya >= yb:
        return
    sa = (alpha[ya - y0:yb - y0, xa - x0:xb - x0] * gain)[..., None]
    sr = rgb[ya - y0:yb - y0, xa - x0:xb - x0]
    dst = pix[ya:yb, xa:xb]
    dst *= (1 - sa)
    dst += sr * sa


def draw_stamps(pix, t):
    for s in stamps:
        a = t - s.t0
        p = min(a / 0.45, 1.0)
        f = 1 + 3.2 * (p - 1) ** 3 + 2.2 * (p - 1) ** 2        # «отскок» при появлении
        f *= 1 + 0.025 * math.sin(a * 7 + s.wob)
        rem = s.life - a
        gain = min(1.0, rem / 0.6, a / 0.08 + 0.05)
        if rem < 0.6:
            f *= 0.85 + 0.15 * max(gain, 0)
        w = SIZES[s.k] * f
        if w < SIZES[0] * 0.8:
            continue
        lv = min(range(NL), key=lambda i: abs(SIZES[i] - w))
        rgb, al = LIPS[(lv, s.pal, s.tilt)]
        flash = 1 + 0.5 * max(0.0, 1 - a / 0.3)
        blit(pix, rgb * flash, al, s.cx, s.cy - a * 1.2, max(gain, 0))
    stamps[:] = [s for s in stamps if t - s.t0 < s.life]


def draw_sparks(pix, dt):
    keep = []
    for sp in sparks:
        sp[0] += sp[2] * dt
        sp[1] += sp[3] * dt
        sp[3] += 14 * dt
        sp[2] *= 0.98
        sp[4] += dt
        k = 1 - sp[4] / sp[5]
        if k <= 0:
            continue
        xi, yi = int(sp[0]), int(sp[1])
        if 0 <= xi < COLS and 0 <= yi < ROWS:
            pix[yi, xi] += np.array(sp[6], np.float32) * k
        keep.append(sp)
    sparks[:] = keep


# ---------- главный цикл ----------
def main():
    t = 0.0
    next_sp = 0.9
    next_wave = 2.4
    trail_t = 0.0
    while True:
        dt = min(clock.tick(FPS) / 1000, 0.05)
        t += dt
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return
                if e.key == pygame.K_SPACE:
                    queue(30, t, 0.03)
                if e.key == pygame.K_s:
                    pygame.image.save(screen, "rozalinochka.png")
                if e.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()

        if pygame.mouse.get_pressed()[0] and t >= trail_t:   # зажми ЛКМ — рисуй поцелуями
            mx, my = pygame.mouse.get_pos()
            add_stamp(mx / CW, my / CH, t, random.randint(5, 10))
            trail_t = t + 0.06

        if t >= next_sp:                                      # постоянный поток губ
            x, y = rand_pos()
            add_stamp(x, y, t)
            next_sp = t + random.uniform(*SPAWN)
        if t >= next_wave:                                    # волна поцелуев
            queue(18, t, 0.04)
            next_wave = t + 7
        due = [p for p in pending if p <= t]
        pending[:] = [p for p in pending if p > t]
        for _ in due:
            x, y = rand_pos()
            add_stamp(x, y, t)

        pix = name_layer(t)
        draw_stamps(pix, t)
        draw_sparks(pix, dt)
        screen.blit(to_ascii(pix), (0, 0))
        pygame.display.flip()


main()
pygame.quit()