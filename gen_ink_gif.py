"""
gen_ink_gif.py — 墨滴落入宣纸，晕出山水画
输出: ink_splash.gif
依赖: Pillow, numpy
"""

import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ── 配置 ──────────────────────────────────────────────
W, H      = 600, 400
FPS       = 24
DURATION  = int(1000 / FPS)
PAPER     = (237, 232, 224)   # 米白暖灰 #EDE8E0
INK       = (20, 60, 110)     # 石青·深 #143c6e（更深）
INK_LIGHT = (60, 120, 175)   # 石青·中

# 石青（azurite）：极远→近
QING_FAR   = (58,  102, 138)  # 远天石青，偏灰
QING_MID   = (38,  88,  124)  # 中景石青
QING_NEAR  = (25,  65,  105)  # 近山石青深沉

# 石绿（malachite）：远→近
LV_FAR     = (72,  120,  82)  # 远山石绿，偏淡
LV_MID     = (52,  102,  62)  # 中景石绿
LV_NEAR    = (35,   78,  45)  # 近山石绿浓厚

# 赭石（ochre）：坡脚/山腰暖色过渡
OCHRE      = (168, 118,  55)

OUTPUT    = "ink_splash.gif"

# 墨滴落点：画面稍偏上方中央
DROP_CX = W // 2
DROP_CY = int(H * 0.67)

# 墨团最大半径（小）
BLOB_MAX_R = 28
# ─────────────────────────────────────────────────────


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(v, lo=0.0, hi=1.0):
    if isinstance(v, np.ndarray):
        return np.clip(v, lo, hi)
    return max(lo, min(hi, float(v)))


def ease_out(t, exp=2.2):
    return 1.0 - (1.0 - t) ** exp


def ease_in(t, exp=2.0):
    return t ** exp


def blend(base: np.ndarray, color, alpha_map: np.ndarray):
    """将单色以 alpha_map 叠加到 base（H×W×3 uint8）"""
    a = np.clip(alpha_map, 0, 1)
    for c in range(3):
        base[:, :, c] = np.clip(
            base[:, :, c] * (1 - a) + color[c] * a, 0, 255
        ).astype(np.uint8)


# ═══════════════════════════════════════════════════════
#  山水画元素（全部手工参数化，大量留白）
# ═══════════════════════════════════════════════════════

def mountain_silhouette(canvas_w, canvas_h, peaks, ink_color, alpha_base,
                         blur=3.5, flatten=1.0):
    """
    peaks: list of (cx_frac, cy_frac, width_frac, height_frac)
    返回 H×W×3 uint8 图层（在白底上）+ alpha mask
    """
    arr   = np.zeros((canvas_h, canvas_w), dtype=float)
    xs    = np.arange(canvas_w, dtype=float)
    ys    = np.arange(canvas_h, dtype=float)

    for (cx_f, cy_f, w_f, h_f) in peaks:
        cx = cx_f * canvas_w
        cy = cy_f * canvas_h
        pw = w_f  * canvas_w
        ph = h_f  * canvas_h * flatten

        XX, YY = np.meshgrid(xs - cx, ys - cy)
        # 椭圆山体
        ellipse = np.clip(1.0 - (XX / pw) ** 2 - (YY / ph) ** 2, 0, None)
        ellipse = ellipse ** 0.55
        arr = np.maximum(arr, ellipse)

    if blur > 0:
        from PIL import Image as _I, ImageFilter as _IF
        tmp = _I.fromarray((arr * 255).astype(np.uint8), mode='L')
        tmp = tmp.filter(_IF.GaussianBlur(radius=blur))
        arr = np.array(tmp).astype(float) / 255.0

    arr = np.clip(arr * alpha_base, 0, 1)

    # 只保留山体中上部（水墨留白：山脚消融）
    fade_y = np.linspace(0, 1, canvas_h).reshape(-1, 1)
    # 愈靠下愈fade（模拟云雾）
    foot_fade = np.clip(1.0 - (fade_y - 0.55) * 4, 0, 1)
    arr = arr * foot_fade

    layer = np.full((canvas_h, canvas_w, 3), PAPER, dtype=np.uint8)
    blend(layer, ink_color, arr)
    return layer, arr


def water_strokes(canvas_w, canvas_h, y_frac, num=4, alpha=0.18):
    """几条水平淡墨线代表水面，返回 alpha map"""
    arr = np.zeros((canvas_h, canvas_w), dtype=float)
    rng = np.random.default_rng(3)
    base_y = y_frac * canvas_h
    for i in range(num):
        wy  = base_y + i * rng.uniform(4, 10)
        x0  = rng.uniform(0.05, 0.2) * canvas_w
        x1  = rng.uniform(0.75, 0.95) * canvas_w
        iy  = int(clamp(wy, 0, canvas_h - 1))
        # 画一条极细线（±1 pixel）
        for dy in range(-1, 2):
            row = iy + dy
            if 0 <= row < canvas_h:
                seg_alpha = alpha * (1.0 - abs(dy) * 0.4)
                # 两端fade
                xs = np.arange(canvas_w, dtype=float)
                fade = np.clip(np.minimum(
                    (xs - x0) / (canvas_w * 0.06 + 1),
                    (x1 - xs) / (canvas_w * 0.06 + 1)
                ), 0, 1)
                mask = np.where((xs >= x0) & (xs <= x1), seg_alpha * fade, 0.0)
                arr[row] = np.maximum(arr[row], mask)
    return arr


def pine_tree(canvas_w, canvas_h, x_frac, y_frac, scale=1.0, alpha=0.72):
    """一棵简笔松树，返回 alpha map"""
    arr = np.zeros((canvas_h, canvas_w), dtype=float)
    cx  = x_frac * canvas_w
    by  = y_frac * canvas_h  # 树底

    # 树干：细长矩形
    trunk_w = max(1, int(2 * scale))
    trunk_h = int(30 * scale)
    tx0 = int(cx - trunk_w)
    tx1 = int(cx + trunk_w)
    ty0 = int(by - trunk_h)
    ty1 = int(by)
    ty0 = max(0, ty0); ty1 = min(canvas_h, ty1)
    tx0 = max(0, tx0); tx1 = min(canvas_w, tx1)
    arr[ty0:ty1, tx0:tx1] = alpha * 0.9

    # 三层三角形枝叶（从下到上缩小）
    for layer_i, (lw, lh, ly_off) in enumerate([
        (22 * scale, 18 * scale, 0),
        (16 * scale, 14 * scale, -14 * scale),
        (10 * scale, 11 * scale, -25 * scale),
    ]):
        tip_y  = by - trunk_h + ly_off
        base_y = tip_y + lh
        for row in range(int(tip_y), int(base_y)):
            if row < 0 or row >= canvas_h:
                continue
            frac_r = (row - tip_y) / (lh + 1e-6)
            hw = lw * frac_r
            c0 = max(0, int(cx - hw))
            c1 = min(canvas_w, int(cx + hw))
            # 笔触感：中央浓边缘淡
            if c1 > c0:
                xs = np.arange(c0, c1, dtype=float)
                dist_norm = np.abs(xs - cx) / (hw + 1e-6)
                stroke_a  = alpha * (1.0 - dist_norm ** 1.4) * 0.9
                arr[row, c0:c1] = np.maximum(arr[row, c0:c1], stroke_a)

    return arr


def reveal_mask(progress, canvas_w, canvas_h, cx, cy, max_r):
    """
    从 (cx,cy) 向外辐射的圆形揭示遮罩（0=隐藏，1=显示）。
    progress 0→1
    """
    r = max_r * ease_out(progress, 2.5)
    xs = np.arange(canvas_w, dtype=float) - cx
    ys = np.arange(canvas_h, dtype=float) - cy
    XX, YY = np.meshgrid(xs, ys)
    dist = np.sqrt(XX**2 + YY**2)
    # soft edge
    edge = r * 0.12
    mask = np.clip((r - dist) / (edge + 1e-6), 0, 1)
    return mask


# ═══════════════════════════════════════════════════════
#  组合山水画（最终静止帧）
# ═══════════════════════════════════════════════════════

def fishing_boat(canvas_w, canvas_h, x_frac, y_frac, scale=1.0, alpha=0.82):
    """
    古风木船：宽底弧 + 高翘船头 + 平船艉 + 圆顶船篷 + 桅杆
    返回 alpha map
    """
    arr      = np.zeros((canvas_h, canvas_w), dtype=float)
    cx       = x_frac * canvas_w
    by       = y_frac * canvas_h

    draw_img = Image.fromarray((arr * 255).astype(np.uint8), mode='L')
    draw     = ImageDraw.Draw(draw_img)

    bw = int(48 * scale)   # 船半宽
    bh = int(10 * scale)   # 船底弧高

    # ── 船底弧 ──
    hull_pts = []
    for deg in range(0, 181, 6):
        rad = math.radians(deg)
        px  = int(cx + bw * math.cos(rad))
        py  = int(by + bh * math.sin(rad))
        hull_pts.append((px, py))
    draw.line(hull_pts, fill=int(alpha * 255), width=max(2, int(2 * scale)))

    # ── 船舷上沿（平直，两端略高） ──
    deck_y = int(by - int(6 * scale))
    draw.line([
        (int(cx - bw),  deck_y + int(2 * scale)),
        (int(cx - bw),  deck_y),
        (int(cx + bw),  deck_y),
        (int(cx + bw),  deck_y + int(2 * scale)),
    ], fill=int(alpha * 255), width=max(2, int(2 * scale)))

    # ── 船头（右侧）高翘曲线 ──
    bow_x = int(cx + bw)
    draw.line([
        (bow_x, deck_y),
        (bow_x + int(8 * scale),  deck_y - int(8  * scale)),
        (bow_x + int(12 * scale), deck_y - int(18 * scale)),
        (bow_x + int(10 * scale), deck_y - int(26 * scale)),
    ], fill=int(alpha * 230), width=max(2, int(2 * scale)))

    # ── 船艉（左侧）平板艉 ──
    stern_x = int(cx - bw)
    draw.line([
        (stern_x, deck_y),
        (stern_x - int(4 * scale), deck_y - int(14 * scale)),
    ], fill=int(alpha * 220), width=max(2, int(2 * scale)))
    # 艉板横线
    draw.line([
        (stern_x - int(4 * scale), deck_y - int(14 * scale)),
        (stern_x + int(8 * scale), deck_y - int(14 * scale)),
    ], fill=int(alpha * 200), width=max(1, int(1 * scale)))

    # ── 船篷（半圆拱，居中偏右） ──
    canopy_cx = int(cx + int(6 * scale))
    canopy_rx = int(22 * scale)
    canopy_ry = int(16 * scale)
    canopy_y  = deck_y
    canopy_pts = []
    for deg in range(0, 181, 10):
        rad = math.radians(deg)
        px  = canopy_cx + int(canopy_rx * math.cos(math.pi - rad))
        py  = canopy_y  - int(canopy_ry * math.sin(rad))
        canopy_pts.append((px, py))
    if len(canopy_pts) >= 2:
        draw.line(canopy_pts, fill=int(alpha * 215), width=max(2, int(2 * scale)))
    # 篷底两端封口
    draw.line([
        (canopy_cx - canopy_rx, canopy_y),
        (canopy_cx - canopy_rx, canopy_y - int(4 * scale)),
    ], fill=int(alpha * 200), width=max(1, int(1 * scale)))
    draw.line([
        (canopy_cx + canopy_rx, canopy_y),
        (canopy_cx + canopy_rx, canopy_y - int(4 * scale)),
    ], fill=int(alpha * 200), width=max(1, int(1 * scale)))

    # ── 桅杆（篷前，细而高） ──
    mast_x  = int(cx - int(18 * scale))
    mast_by = deck_y
    mast_ty = int(by - int(52 * scale))
    draw.line([(mast_x, mast_by), (mast_x, mast_ty)],
              fill=int(alpha * 245), width=max(1, int(2 * scale)))

    # ── 帆（折叠状，两条斜线） ──
    draw.line([
        (mast_x, mast_ty + int(4 * scale)),
        (mast_x + int(18 * scale), mast_ty + int(24 * scale)),
    ], fill=int(alpha * 180), width=max(1, int(1 * scale)))
    draw.line([
        (mast_x, mast_ty + int(16 * scale)),
        (mast_x + int(16 * scale), mast_ty + int(32 * scale)),
    ], fill=int(alpha * 160), width=max(1, int(1 * scale)))

    arr = np.array(draw_img).astype(float) / 255.0
    return arr


def mountain_outline(canvas_w, canvas_h, peaks, ink_color, alpha=0.72, line_w=2):
    """
    用折线勾勒山脊轮廓，不填充，只有一条细线。
    peaks: list of (x_frac, y_frac) 山脊关键点，从左到右
    """
    arr     = np.zeros((canvas_h, canvas_w), dtype=float)
    draw_img = Image.fromarray((arr * 255).astype(np.uint8), mode='L')
    draw    = ImageDraw.Draw(draw_img)
    pts = [(int(x * canvas_w), int(y * canvas_h)) for x, y in peaks]
    if len(pts) >= 2:
        draw.line(pts, fill=int(alpha * 255), width=line_w)
    arr = np.array(draw_img).astype(float) / 255.0
    return arr


def misty_mountain(canvas_w, canvas_h, peaks, alpha_peak=0.38, blur=14, foot_fade_start=0.52):
    """
    若隐若现的墨山：填充椭圆山体，极度模糊，山脚渐隐。
    peaks: list of (cx_f, cy_f, w_f, h_f)
    返回 alpha map
    """
    arr = np.zeros((canvas_h, canvas_w), dtype=float)
    xs  = np.arange(canvas_w, dtype=float)
    ys  = np.arange(canvas_h, dtype=float)

    for (cx_f, cy_f, w_f, h_f) in peaks:
        cx = cx_f * canvas_w
        cy = cy_f * canvas_h
        pw = w_f  * canvas_w
        ph = h_f  * canvas_h
        XX, YY = np.meshgrid(xs - cx, ys - cy)
        e = np.clip(1.0 - (XX / pw)**2 - (YY / ph)**2, 0, None) ** 0.5
        arr = np.maximum(arr, e)

    # 强模糊 → 烟雾感
    tmp = Image.fromarray((arr * 255).astype(np.uint8), mode='L')
    tmp = tmp.filter(ImageFilter.GaussianBlur(radius=blur))
    arr = np.array(tmp).astype(float) / 255.0

    # 山脚向下渐隐（云雾吃掉山脚）
    fy = np.linspace(0, 1, canvas_h).reshape(-1, 1)
    foot = np.clip(1.0 - (fy - foot_fade_start) / 0.18, 0, 1)
    arr  = arr * foot * alpha_peak

    return np.clip(arr, 0, 1)


def make_landscape():
    """加载 pic/boat2.jpg，cover 裁剪到画布尺寸"""
    import os
    img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pic", "boat2.jpg")
    img = Image.open(img_path).convert("RGB")
    src_w, src_h = img.size
    scale = max(W / src_w, H / src_h)
    new_w, new_h = int(src_w * scale), int(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - W) // 2
    top  = (new_h - H) // 2
    img  = img.crop((left, top, left + W, top + H))
    return np.array(img, dtype=np.uint8)

# LANDSCAPE = make_landscape()  # 仅在需要山水背景时启用


# ═══════════════════════════════════════════════════════
#  墨滴形状
# ═══════════════════════════════════════════════════════

def make_teardrop(r, cx, cy):
    """水滴形：用极坐标 cardioid 变体，尖朝上，无独立尾巴笔触"""
    arr = np.zeros((H, W), dtype=float)
    if r < 1:
        return arr
    xs = np.arange(W, dtype=float) - cx
    ys = np.arange(H, dtype=float) - cy   # 正 Y = 下方
    XX, YY = np.meshgrid(xs, ys)

    # 极坐标：角度从正上方（尖尾方向）计量
    # theta=0 → 正上方（尾），theta=π → 正下方（圆腹）
    dist  = np.sqrt(XX**2 + YY**2)
    theta = np.arctan2(-YY, XX)            # π/2 = 上, -π/2 = 下  →  重映射
    # 改为：theta=0 对准正上方
    theta = np.arctan2(-YY, XX) - math.pi / 2  # 0 = 正上方
    # 水滴极径公式：r(θ) = R·(1 - 0.35·cos(θ))  — 上方缩小，下方膨胀
    drop_r = r * (1.0 - 0.38 * np.cos(theta))
    mask = np.clip(1.0 - (dist - drop_r) / max(r * 0.15, 1), 0, 1)
    return mask


def make_blob(r, cx, cy, flatten=0.85):
    arr = np.zeros((H, W), dtype=float)
    if r < 1:
        return arr
    xs = np.arange(W, dtype=float) - cx
    ys = (np.arange(H, dtype=float) - cy) / flatten
    XX, YY = np.meshgrid(xs, ys)
    dist  = np.sqrt(XX**2 + YY**2)
    inner = r * 0.5
    outer = r
    alpha = np.where(dist < inner, 1.0,
            np.where(dist < outer,
                     1.0 - (dist - inner) / (outer - inner + 1e-6),
                     0.0))
    rng2 = np.random.default_rng(17)
    noise = rng2.uniform(-0.05, 0.05, alpha.shape)
    return np.clip(alpha + noise * (alpha > 0.05), 0, 1)


# ═══════════════════════════════════════════════════════
#  序列帧构建
# ═══════════════════════════════════════════════════════

def build_frames():
    frames = []

    # Phase 1 — 落下 (22帧)
    fall_start = -14        # 从画面上方刚好露出水滴尖尾处入场
    fall_end   = DROP_CY
    fall_steps = 22
    for i in range(fall_steps):
        t   = ease_in((i + 1) / fall_steps, 2.0)
        fy  = lerp(fall_start, fall_end, t)
        base = np.full((H, W, 3), PAPER, dtype=np.uint8)
        td   = make_teardrop(10, DROP_CX, fy)
        blend(base, INK, td * 0.92)
        frames.append(Image.fromarray(base))

    # Phase 2 — 撞击扩散成小墨团 (18帧)
    spread_steps = 18
    blob_r = 0.0
    for i in range(spread_steps):
        t      = ease_out((i + 1) / spread_steps, 1.8)
        blob_r = BLOB_MAX_R * t
        blob_a = 1.0 - t * 0.12   # 稍微淡化边缘
        base   = np.full((H, W, 3), PAPER, dtype=np.uint8)
        bm     = make_blob(blob_r, DROP_CX, DROP_CY)
        blend(base, INK, bm * blob_a)
        # 几个小飞溅
        rng3 = np.random.default_rng(5)
        for _ in range(6):
            ang = rng3.uniform(0, math.pi * 2)
            dd  = rng3.uniform(6, 22) * t
            sx  = DROP_CX + math.cos(ang) * dd
            sy  = DROP_CY + math.sin(ang) * dd
            sr  = rng3.uniform(1, 3) * t
            xs  = np.arange(W, dtype=float) - sx
            ys  = np.arange(H, dtype=float) - sy
            XX2, YY2 = np.meshgrid(xs, ys)
            d2  = np.sqrt(XX2**2 + YY2**2)
            dot = np.clip(1.0 - d2 / (sr + 0.5), 0, 1) * 0.75
            blend(base, INK, dot)
        frames.append(Image.fromarray(base))

    # Phase 3 — 墨团轻微晕染停留 (10帧)
    held_steps = 10
    for i in range(held_steps):
        base  = np.full((H, W, 3), PAPER, dtype=np.uint8)
        bm    = make_blob(BLOB_MAX_R + i * 0.6, DROP_CX, DROP_CY)
        blend(base, INK, bm * (0.88 - i * 0.015))
        img   = Image.fromarray(base)
        if i > 3:
            img = img.filter(ImageFilter.GaussianBlur(radius=(i - 3) * 0.4))
        frames.append(img)

    return frames


print("生成帧中...")
frames = build_frames()
print(f"共 {len(frames)} 帧，保存 GIF...")

frames[0].save(
    OUTPUT,
    save_all=True,
    append_images=frames[1:],
    loop=0,
    duration=DURATION,
    optimize=False,
)
print(f"完成！-> {OUTPUT}")
