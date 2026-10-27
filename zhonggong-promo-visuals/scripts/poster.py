# -*- coding: utf-8 -*-
"""
中公教育 方形推广海报生成器（纯代码，不调用 Photoshop）

用法：
    python3 poster.py                  # 生成 2 张 JPG
    python3 poster.py --psd            # 额外生成分层 PSD
    python3 poster.py --config c.json  # 用 JSON 覆盖 CONFIG

依赖见技能包根目录 requirements.txt；本脚本运行仅需 Pillow 与 NumPy，PSD 写入由同目录 psd_rle.py 完成。
"""
import os, sys, math, json, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# CONFIG —— 每个新任务只改这里
# ============================================================
CONFIG = {
    # ⚠️ 产物一律落在【当前工作空间】下，一个项目一个独立文件夹（2026-09-18 明确要求）
    #    不要写到工作空间之外（如桌面、下载等系统目录）
    #    文件夹名一律以「-海报」结尾（2026-10-21 明确）
    "out_dir": os.path.join(os.getcwd(), "2026地区项目产品-海报"),
    "base_name": "珠海基层服务岗笔试甄题冲刺包",
    "size": 2000,

    # 顶部
    "logo_path": os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "brand", "zhonggong-logo.png"),
    "project_tag": "事业单位",          # 项目类型：事业单位 / 教师招聘 / 省考 / 医疗 ...
    "notice": "2026年广州市海珠区事业单位公开招聘高校毕业生公告",  # 公告名词

    # 主标题（无 kicker，直接大标题）
    "title_main": "海珠事编",
    "title_sub": [["笔试", "w"], ["冲刺卷", "r"]],   # w=白 r=标红
    "title_main_size": 238,
    "title_sub_size": 198,
    "title_width": 1600,                              # 标题两端对齐到内容框宽度（字距自动放宽）

    # 标签组
    "subtitle": "全真模拟 · 三套",
    "badge": "电子课件",

    # 课件卡片：rows = [全称, 后缀说明]
    "content_title": "课件内容",
    "content_meta": "共 6 份电子文档",
    "content_rows": [
        ["2026海珠区事业单位招聘高校毕业生冲刺卷（一）", "· 参考答案及解析"],
        ["2026海珠区事业单位招聘高校毕业生冲刺卷（二）", "· 参考答案及解析"],
        ["2026海珠区事业单位招聘高校毕业生冲刺卷（三）", "· 参考答案及解析"],
    ],
    "content_note": "全部为电子版课件 · 每套均配参考答案及详细解析",

    # 价格
    "price_group": "2人拼团",
    "price_value": "5.99",
    "price_single": "单独购买 15.99 元",
    "only_price": "5.99",
    "only_sub": "限时优惠 · 电子课件",

    # 底部
    "claim": "购买后在中公教育 App 可下载电子文档",
    "footer": "2026广州市海珠区事业单位“高珠识粤”笔试冲刺卷三套（电子课件）",

    # 地域元素
    "motif": "canton_tower",   # canton_tower | waves | grid

    # 配色（活力撞色，可整套替换）
    "palette": {
        "bg_top": (18, 32, 96),
        "bg_bot": (34, 74, 178),
        "white":  (255, 255, 255),
        "light":  (198, 214, 255),
        "mute":   (156, 174, 226),
        "track":  (128, 148, 206),
        "ink":    (26, 36, 92),
        "red":    (250, 108, 74),
        "yellow": (255, 205, 61),
        "cyan":   (61, 214, 232),
        "stroke_w": (30, 60, 150),    # 白色标题的描边色
        "stroke_r": (150, 52, 24),    # 强调色标题的描边色
    },
}

# ============================================================
# 字体白名单（仅可用这些，且必须已安装）
# ============================================================
FONT_DIR = os.path.expanduser("~/Library/Fonts")
FONT_WHITELIST = {
    "方正兰亭特黑": "FZLTTHJW.TTF",
    "方正兰亭粗黑": "FZLTCHJW.TTF",
    "方正兰亭黑":  "FZLTHJW.TTF",
    "方正粗谭黑":  "FZCTHJW.TTF",
    "方正汉真广标": "FZHZGBJW.TTF",
    "方正特雅宋":  "FZTYSJW.ttf",
    "方正清刻本悦宋": "FZQKBYSJW.TTF",
    "方正书宋":    "方正书宋简体.ttf",
    "方正仿宋":    "方正仿宋简体.TTF",
    "方正楷体":    "方正楷体简体.ttf",
    "方正黑体":    "方正黑体简体.TTF",
    "站酷高端黑":  "站酷高端黑修订版1.13.ttf",
    "站酷酷黑":    "站酷酷黑.ttf",
    "庞门正道标题体": "庞门正道标题体2.0增强版.ttf",
    "锐字真言体":  "锐字真言体免费商用.ttf",
}
FT_TITLE = FONT_WHITELIST["方正兰亭粗黑"]
FT_HEAVY = FONT_WHITELIST["方正兰亭粗黑"]
FT_BOLD  = FONT_WHITELIST["方正兰亭粗黑"]
FT_REG   = FONT_WHITELIST["方正兰亭黑"]

# 违规广告词黑名单（命中即需替换）
BANNED_WORDS = ["资料", "真题", "押题", "上岸", "保过", "包过", "协议班", "绝密",
                "内部", "命题", "命中", "预测", "必过", "保分", "官方指定", "第一",
                "最好", "最佳", "最强", "100%", "百分百", "泄题", "原题", "保过班"]

# 配色（运行时由 CONFIG["palette"] 覆盖）
PAL = dict(CONFIG["palette"])
S = 2000

# 版式（随课件条目数自适应；默认版式 = 原设计，≤6 条时使用）
LAYOUT = {
    "logo_y": 74, "rule_y": 250, "notice_y": 296,
    "title_y1": 486, "title_y2": 730,
    "chip_y": 878, "badge_y": 888,
    "card0": 990, "card1": 1490,
    "ctitle_y": 44, "divider_y": 142,
    "rows_top": 216, "row_h": 90,
    "note_y": 452,
    "price_group_y": 1568, "price_num_y": 1690, "price_single_y": 1802,
    "qr_y": 1524, "qr_size": 268, "qr_label_y": 1838,
    "only_label_y": 1660, "only_price_y": 1660, "only_sub_y": 1798,
    "claim_y": 1906, "footer_y": 1956,
}

# 紧凑版式：课件条目 > 6 行时启用（顶部区块上移、卡片加高、行距收紧）
LAYOUT_COMPACT = {
    "logo_y": 54, "rule_y": 228, "notice_y": 266,
    "title_y1": 396, "title_y2": 600,
    "chip_y": 726, "badge_y": 736,
    "card0": 860, "card1": 1580,
    "ctitle_y": 34, "divider_y": 118,
    "rows_top": 166, "row_h": 56,
    "note_y": 668,
    "price_group_y": 1634, "price_num_y": 1734, "price_single_y": 1836,
    "qr_y": 1572, "qr_size": 232, "qr_label_y": 1846,
    "only_label_y": 1706, "only_price_y": 1706, "only_sub_y": 1840,
    "claim_y": 1902, "footer_y": 1965,
}


def C(k):
    return tuple(PAL[k])   # JSON 覆盖时颜色是 list，统一转 tuple（list + tuple 会报错）


def F(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def new_canvas():
    return Image.new("RGBA", (S, S), (0, 0, 0, 0))


def vgrad(c1, c2, c3=None, t2=0.5):
    """竖向渐变。给了 c3 就走三段（顶部 c1 → t2 处 c2 最亮 → 底部 c3），
    用来做「顶部深、中部发亮、底部压回来」的暖阳式背景，比两段更透气。"""
    ramp = np.linspace(0, 1, S)
    a = np.zeros((S, 3))
    c1 = np.array(c1, float); c2 = np.array(c2, float)
    if c3 is None:
        a = c1[None, :] * (1 - ramp[:, None]) + c2[None, :] * ramp[:, None]
    else:
        c3 = np.array(c3, float)
        lo = ramp <= t2
        u = (ramp[lo] / t2)[:, None]
        a[lo] = c1[None, :] * (1 - u) + c2[None, :] * u
        u = ((ramp[~lo] - t2) / (1 - t2))[:, None]
        a[~lo] = c2[None, :] * (1 - u) + c3[None, :] * u
    a = a.astype(np.uint8)
    return Image.fromarray(np.repeat(a[:, None, :], S, axis=1), "RGB").convert("RGBA")


def glow(cx, cy, r, color, strength):
    yy, xx = np.mgrid[0:S, 0:S]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    m = np.clip(1 - d, 0, 1) ** 2 * strength
    layer = np.zeros((S, S, 4), np.uint8)
    for i in range(3):
        layer[..., i] = color[i]
    layer[..., 3] = (m * 255).astype(np.uint8)
    return Image.fromarray(layer, "RGBA")


def text_img(text, font, fill, sw=0, sfill=None):
    d = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    b = d.textbbox((0, 0), text, font=font, stroke_width=sw)
    pad = 6
    out = Image.new("RGBA", (b[2] - b[0] + pad * 2 + sw * 2,
                             b[3] - b[1] + pad * 2 + sw * 2), (0, 0, 0, 0))
    ImageDraw.Draw(out).text((pad - b[0], pad - b[1]), text, font=font, fill=fill,
                             stroke_width=sw, stroke_fill=sfill)
    return out


def put(layer, im, cx, cy):
    layer.alpha_composite(im, (int(cx - im.size[0] / 2), int(cy - im.size[1] / 2)))


def tracked_segs(layer, segs, font, cx, cy, track):
    """segs: [(text, fill, stroke_fill)] 带字距，整行居中，返回总宽"""
    chars = [(ch, fill, sf) for (t, fill, sf) in segs for ch in t]
    ws = [font.getlength(ch) for ch, _, _ in chars]
    total = sum(ws) + track * (len(chars) - 1)
    x = cx - total / 2
    for (ch, fill, sf), w in zip(chars, ws):
        im = text_img(ch, font, fill, 3, sf)
        layer.alpha_composite(im, (int(x), int(cy - im.size[1] / 2)))
        x += w + track
    return total


def fit_track(text, font, target):
    """按目标宽度反算字距，使该行两端对齐到 target 宽度"""
    ws = [font.getlength(ch) for ch in text]
    if len(ws) < 2:
        return 0
    return (target - sum(ws)) / (len(ws) - 1)


# ---------------- 背景与地域元素（全原创矢量绘制） ----------------
def dim_bottom(color, y0=1500, strength=0.78, gamma=0.6):
    """底部压暗层：从 y0 起把背景往 color 压（gamma<1 让它在价格区快速落下）。
    底色整体提亮后，靠这一层保住价格区红字与二维码标签的对比度。"""
    u = np.clip((np.arange(S) - y0) / max(1, S - y0), 0, 1) ** gamma
    a = (u * strength * 255).astype(np.uint8)
    layer = np.zeros((S, S, 4), np.uint8)
    for i in range(3):
        layer[..., i] = color[i]
    layer[..., 3] = np.repeat(a[:, None], S, axis=1)
    return Image.fromarray(layer, "RGBA")


def L_bg():
    # 三段底色（palette 给 bg_mid 时启用）：顶部深 → bg_mid_t 处最亮 → 底部压回来，
    # 画面中段透出一层暖光，比两段渐变"有生气"，同时保住顶部标题与底部价格的可读性。
    if PAL.get("bg_mid"):
        bg = vgrad(C("bg_top"), C("bg_mid"), C("bg_bot"), PAL.get("bg_mid_t", 0.5))
    else:
        bg = vgrad(C("bg_top"), C("bg_bot"))
    # 光晕颜色与强度都可配（不传时保持原有默认值，向后兼容）
    bg.alpha_composite(glow(400, 360, PAL.get("glow1_r", 1150),
                            PAL.get("glow1", C("cyan")), PAL.get("glow1_s", 0.24)))
    bg.alpha_composite(glow(1760, 1720, PAL.get("glow2_r", 1300),
                            PAL.get("glow2", C("red")), PAL.get("glow2_s", 0.16)))
    bg.alpha_composite(glow(1500, 700, PAL.get("glow3_r", 800),
                            PAL.get("glow3", (90, 140, 255)), PAL.get("glow3_s", 0.20)))
    if PAL.get("glow4"):        # 中段大暖光：把卡片上沿与左右两侧照亮，画面更透
        bg.alpha_composite(glow(PAL.get("glow4_x", 1000), PAL.get("glow4_y", 900),
                                PAL.get("glow4_r", 1200), PAL["glow4"],
                                PAL.get("glow4_s", 0.28)))
    if PAL.get("dim_c"):        # 底部压暗（最后叠，保证价格区文字对比）
        bg.alpha_composite(dim_bottom(PAL["dim_c"], PAL.get("dim_y", 1500),
                                      PAL.get("dim_s", 0.78), PAL.get("dim_g", 0.6)))
    return bg


def L_motif(motif):
    l = new_canvas()
    dr = ImageDraw.Draw(l)
    line_c = C("cyan")
    if motif == "canton_tower":
        cx, top, bot = 1660, 300, 1580
        wmin, tw, ka, kb = 30, 0.60, 2.15, 1.55

        def half(t):
            return (1.95 * wmin * math.cosh(ka * (tw - t)) if t <= tw
                    else 1.55 * wmin * math.cosh(kb * (t - tw)))
        n = 90
        left, right = [], []
        for i in range(n + 1):
            t = i / n
            y = top + (bot - top) * t
            w = half(t)
            left.append((cx - w, y)); right.append((cx + w, y))
        dr.line(left, fill=line_c + (95,), width=3)
        dr.line(right, fill=line_c + (95,), width=3)
        for i in range(0, n, 5):
            t = i / n
            y = top + (bot - top) * t
            w = half(t)
            dr.line([(cx - w, y), (cx + w, y)], fill=line_c + (48,), width=2)
        dr.line([(cx, top), (cx, 158)], fill=line_c + (95,), width=4)
        for t in (0.30, 0.45, 0.62, 0.80):
            y = top + (bot - top) * t
            w = half(t)
            dr.line([(cx - w - 5, y), (cx + w + 5, y)], fill=C("yellow") + (80,), width=5)
    elif motif == "zhuhai":
        # ① 日月贝（珠海大剧院）：双壳外壳弧线 + 放射肋，全代码原创矢量
        def shell(ax, ay, r, a0, a1, ribs=36, al=132):
            pts = [(ax + r * math.cos(math.radians(a)), ay + r * math.sin(math.radians(a)))
                   for a in [a0 + (a1 - a0) * i / 72 for i in range(73)]]
            dr.line(pts, fill=line_c + (al,), width=5, joint="curve")
            for i in range(ribs + 1):
                a = a0 + (a1 - a0) * i / ribs
                dr.line([(ax, ay),
                         (ax + r * math.cos(math.radians(a)), ay + r * math.sin(math.radians(a)))],
                        fill=line_c + (48,), width=3)

        shell(1656, 962, 388, 190, 350)
        shell(1884, 912, 228, 196, 344, ribs=28)
        # ② 港珠澳大桥斜拉索：塔柱 + 扇形缆索 + 桥面（桥面上移，避免被卡片遮住）
        pxx, pyy, ptop = 148, 806, 300
        dr.line([(pxx, ptop), (pxx, pyy)], fill=line_c + (112,), width=6)
        for i in range(8):
            dr.line([(pxx, ptop + 44 + i * 30), (240 + i * 48, pyy)],
                    fill=C("yellow") + (42,), width=2)
        dr.line([(pxx - 62, pyy), (472, pyy)], fill=line_c + (72,), width=4)
    elif motif == "zhuhai_coast":
        # 港珠澳大桥横跨画面 + 桥塔扇形斜拉索 + 远处海岛轮廓 + 星点（全代码原创矢量）
        # 与 zhuhai（日月贝）构图完全不同，用于珠海系列第二个产品时做区分
        deck = 812
        dr.line([(-60, deck), (S + 60, deck)], fill=line_c + (86,), width=9)
        dr.line([(-60, deck + 18), (S + 60, deck + 18)], fill=line_c + (38,), width=3)
        for tx in (112, 1888):                    # 桥塔贴边，避开主标题墨迹
            dr.line([(tx, 470), (tx, deck)], fill=line_c + (74,), width=9)
            dr.line([(tx - 30, 502), (tx + 30, 502)], fill=line_c + (58,), width=6)
            for i in range(8):
                off = 66 + i * 38
                dr.line([(tx, 528 + i * 17), (tx - off, deck)], fill=C("yellow") + (38,), width=2)
                dr.line([(tx, 528 + i * 17), (tx + off, deck)], fill=C("yellow") + (38,), width=2)
        for px_ in range(200, S, 240):            # 桥墩
            dr.line([(px_, deck + 18), (px_, deck + 42)], fill=line_c + (48,), width=5)
        pts = [(500, deck - 4)]                   # 远处海岛轮廓
        for x_, h_ in [(590, 32), (668, 16), (752, 44), (836, 20), (922, 38), (1010, 12), (1104, 4)]:
            pts.append((x_, deck - 4 - h_))
        dr.line(pts, fill=line_c + (42,), width=4, joint="curve")
        for sx_, sy_, r_ in [(196, 606, 5), (430, 552, 4), (1566, 592, 5),
                             (1846, 690, 4), (318, 748, 4), (1742, 508, 4)]:
            dr.ellipse([sx_ - r_, sy_ - r_, sx_ + r_, sy_ + r_], fill=C("cyan") + (68,))
    elif motif == "gd_science":
        # 广东省级「科学素质」主题：原子轨道 + 木棉花（省花）+ 科技节点网络（全代码原创矢量）
        # 与 canton_tower / zhuhai / zhuhai_coast 构图完全不同，用于省级科学科普类产品

        def petal(px_, py_, ang, R, W, al, wd):
            """柳叶形花瓣：沿 ang 方向从中心到尖端，两侧对称收窄"""
            dx, dy = math.cos(ang), math.sin(ang)
            nx, ny = -dy, dx
            left, right = [], []
            for i in range(31):
                t = i / 30
                d, w = t * R, W * math.sin(math.pi * t) ** 0.62
                left.append((px_ + dx * d + nx * w, py_ + dy * d + ny * w))
                right.append((px_ + dx * d - nx * w, py_ + dy * d - ny * w))
            dr.line(left + list(reversed(right)) + [left[0]],
                    fill=line_c + (al,), width=wd, joint="curve")

        # ① 左侧窄带：原子轨道（三条交叉椭圆）+ 原子核 + 电子
        ax, ay = 104, 646
        for rot in (0, 60, 120):
            a = math.radians(rot)
            pts = []
            for i in range(97):
                t = 2 * math.pi * i / 96
                ex, ey = 92 * math.cos(t), 30 * math.sin(t)
                pts.append((ax + ex * math.cos(a) - ey * math.sin(a),
                            ay + ex * math.sin(a) + ey * math.cos(a)))
            dr.line(pts, fill=line_c + (104,), width=3)
        dr.ellipse([ax - 14, ay - 14, ax + 14, ay + 14], fill=C("yellow") + (122,))
        for ex_, ey_ in [(ax + 86, ay + 30), (ax - 52, ay - 74), (ax - 34, ay + 86)]:
            dr.ellipse([ex_ - 9, ey_ - 9, ex_ + 9, ey_ + 9], fill=C("cyan") + (136,))

        # ② 右侧窄带：木棉花（广东省花）五瓣 + 花蕊
        mx, my = 1894, 636
        for k in range(5):
            petal(mx, my, math.radians(-90 + k * 72), 74, 30, 116, 4)
        for k in range(9):
            a = math.radians(-90 + k * 40)
            dr.line([(mx, my), (mx + 44 * math.cos(a), my + 44 * math.sin(a))],
                    fill=C("yellow") + (92,), width=2)
        dr.ellipse([mx - 15, my - 15, mx + 15, my + 15], fill=C("red") + (150,))

        # ③ 科技节点网络底纹（低透明度，卡片外的部分才可见）
        nodes = [(150, 400), (356, 330), (700, 372), (1120, 322), (1466, 366),
                 (1700, 318), (1876, 430), (108, 838), (1888, 856),
                 (96, 1046), (1904, 1078), (128, 1320), (1886, 1350),
                 (240, 1560), (1780, 1524), (472, 1652), (1524, 1672),
                 (760, 1786), (1246, 1806), (330, 1918), (1690, 1908)]
        edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8),
                 (8, 9), (9, 10), (10, 11), (11, 12), (12, 13), (13, 14),
                 (14, 15), (15, 16), (16, 17), (17, 18), (18, 19), (19, 20)]
        for a_, b_ in edges:
            dr.line([nodes[a_], nodes[b_]], fill=line_c + (30,), width=2)
        for nx, ny in nodes:
            dr.ellipse([nx - 7, ny - 7, nx + 7, ny + 7], fill=C("cyan") + (50,))
    elif motif == "maoming":
        # 茂名「荔乡」主题：荔枝果枝（果实鳞斑纹理）+ 荔枝叶 + 散点果（全代码原创矢量）
        # 元素落在左右窄带与 card0 以上空档，避开主标题墨迹（x 200–1800）
        fruit_c = C("red")

        def leaf(x0, y0, ang, ln, wd, al=92):
            a = math.radians(ang)
            dx, dy = math.cos(a), math.sin(a)
            nx, ny = -dy, dx
            up, dn = [], []
            for i in range(25):
                t = i / 24
                w = wd * math.sin(math.pi * t)
                up.append((x0 + dx * ln * t + nx * w, y0 + dy * ln * t + ny * w))
                dn.append((x0 + dx * ln * t - nx * w, y0 + dy * ln * t - ny * w))
            dr.line(up + list(reversed(dn)) + [up[0]],
                    fill=line_c + (al,), width=3, joint="curve")
            dr.line([(x0, y0), (x0 + dx * ln * 0.95, y0 + dy * ln * 0.95)],
                    fill=line_c + (al,), width=2)

        def lychee(cx_, cy_, r_, al=118):
            """荔枝果实：外圈 + 三环交错鳞斑短弧"""
            dr.ellipse([cx_ - r_, cy_ - r_, cx_ + r_, cy_ + r_],
                       outline=fruit_c + (al,), width=4)
            for ring in range(3):
                rr = r_ * (0.36 + 0.27 * ring)
                n = 6 + ring * 3
                off = 0.35 if ring % 2 else 0.0
                for k in range(n):
                    a = 2 * math.pi * k / n + off
                    px_, py_ = cx_ + rr * math.cos(a), cy_ + rr * math.sin(a)
                    s = r_ * 0.13
                    dr.arc([px_ - s, py_ - s, px_ + s, py_ + s], 220, 90,
                           fill=fruit_c + (70,), width=2)

        # ① 右侧窄带：一枝双果（枝条自上而下）+ 双叶
        #    全部元素保持 x >= 1810，避开主标题墨迹（x 200–1800）
        dr.line([(1958, 320), (1896, 458), (1872, 552)],
                fill=line_c + (86,), width=5, joint="curve")
        lychee(1872, 612, 58)
        lychee(1912, 500, 40, al=98)
        dr.line([(1930, 432), (1912, 460)], fill=fruit_c + (98,), width=3)
        leaf(1908, 392, -58, 130, 32)
        leaf(1884, 462, -35, 118, 28)

        # ② 左侧窄带：单果 + 双叶（全部元素保持 x <= 195）
        dr.line([(58, 548), (140, 642)], fill=line_c + (86,), width=5)
        lychee(144, 700, 50)
        leaf(112, 552, -62, 125, 32)
        leaf(120, 560, -45, 100, 26)

        # ③ 散点果（低透明度，卡片两侧窄带内，避开价格与二维码区）
        for sx_, sy_, r_, al_ in [(120, 912, 26, 46), (1876, 952, 24, 42),
                                  (150, 1318, 22, 40), (1868, 1372, 22, 38)]:
            dr.ellipse([sx_ - r_, sy_ - r_, sx_ + r_, sy_ + r_],
                       outline=fruit_c + (al_,), width=3)
    elif motif == "gd_science2":
        # 广东省级「科学素质」第二支画法：火箭发射线稿（左窄带）+ 卫星（右窄带）
        # + 大轨道弧 + 星点（全代码原创矢量）。与 gd_science（原子轨道+木棉花）构图区分，
        # 用于同主题的第二个产品（2027 粤正登科）。
        # ① 左侧窄带（x≤195，避开主标题墨迹 x 200–1800）：火箭线稿，斜向右上
        bx, by = 116, 806
        a = math.radians(-78)
        ux, uy = math.cos(a), math.sin(a)
        nx_, ny_ = -uy, ux
        L = 250
        tipx, tipy = bx + ux * L, by + uy * L
        hw = 34
        pL1 = (bx + nx_ * hw, by + ny_ * hw)
        pR1 = (bx - nx_ * hw, by - ny_ * hw)
        shL = (tipx - ux * 58 + nx_ * 13, tipy - uy * 58 + ny_ * 13)
        shR = (tipx - ux * 58 - nx_ * 13, tipy - uy * 58 - ny_ * 13)
        dr.line([pL1, shL], fill=line_c + (110,), width=4)
        dr.line([pR1, shR], fill=line_c + (110,), width=4)
        dr.line([shL, (tipx, tipy)], fill=line_c + (110,), width=4)
        dr.line([shR, (tipx, tipy)], fill=line_c + (110,), width=4)
        for s in (1, -1):                      # 尾翼
            fx, fy = bx + ux * 26 + nx_ * s * hw, by + uy * 26 + ny_ * s * hw
            ex, ey = bx - ux * 46 + nx_ * s * 88, by - uy * 46 + ny_ * s * 88
            dr.line([(fx, fy), (ex, ey), (bx + ux * 54 + nx_ * s * 30, by + uy * 54 + ny_ * s * 30)],
                    fill=line_c + (96,), width=3, joint="curve")
        wx, wy = bx + ux * 96, by + uy * 96    # 舷窗
        dr.ellipse([wx - 15, wy - 15, wx + 15, wy + 15], fill=C("cyan") + (120,))
        for k, (dl, wd_) in enumerate([(34, 3), (62, 2), (88, 2)]):   # 尾焰
            fx, fy = bx - ux * (16 + k * 4), by - uy * (16 + k * 4)
            ex, ey = bx - ux * (16 + k * 4 + dl), by - uy * (16 + k * 4 + dl)
            dr.line([(fx, fy), (ex, ey)], fill=C("yellow") + (108 - k * 30,), width=wd_)

        # ② 右侧窄带（x≥1810）：卫星（本体 + 双太阳能板 + 天线弧）
        sx, sy = 1892, 640
        dr.rectangle([sx - 26, sy - 26, sx + 26, sy + 26], outline=line_c + (110,), width=4)
        dr.ellipse([sx - 9, sy - 9, sx + 9, sy + 9], fill=C("yellow") + (110,))
        for px0, px1 in [(1816, 1862), (1922, 1968)]:
            dr.rectangle([px0, sy - 16, px1, sy + 16], outline=line_c + (96,), width=3)
            for i in range(1, 4):
                xx = px0 + (px1 - px0) * i / 4
                dr.line([(xx, sy - 16), (xx, sy + 16)], fill=line_c + (60,), width=2)
        dr.line([(sx - 26, sy), (1816, sy)], fill=line_c + (96,), width=3)
        dr.line([(sx + 26, sy), (1968, sy)], fill=line_c + (96,), width=3)
        dr.arc([sx - 22, sy - 66, sx + 22, sy - 22], 200, 340,
               fill=C("yellow") + (96,), width=3)

        # ③ 大轨道弧（低透明度虚线，横贯上部空档，垫在标题层之下）
        for i in range(0, 80, 2):
            t0, t1 = 2 * math.pi * i / 80, 2 * math.pi * (i + 1) / 80
            pts = []
            for t in (t0, t1):
                ex, ey = 880 * math.cos(t), 210 * math.sin(t)
                pts.append((1000 + ex * 0.98 - ey * 0.18,
                            560 + ex * 0.18 + ey * 0.98))
            dr.line(pts, fill=line_c + (26,), width=2)

        # ④ 星点散布（避开公告名带、主标题两行墨迹带与标签组，落在
        #    标题下方空档两侧 x 210–600 / 1400–1790、y 730–850，及左右窄带）
        for sx_, sy_, r_, al_ in [(300, 792, 4, 64), (470, 828, 3, 52), (1530, 796, 4, 60),
                                  (1700, 838, 3, 52), (90, 420, 3, 56), (1908, 424, 3, 56),
                                  (100, 980, 3, 48), (1896, 990, 3, 48)]:
            dr.ellipse([sx_ - r_, sy_ - r_, sx_ + r_, sy_ + r_], fill=C("cyan") + (al_,))
    elif motif == "gd_xuandiao":
        # 广东「选调生」主题：岭南镬耳山墙剪影（左窄带）+ 珠江新城双塔天际线（右窄带）
        # 全代码原创矢量。构图与已用的六支（广州塔 / 日月贝+桥 / 港珠澳大桥 /
        # 原子轨道+木棉 / 荔枝果枝 / 火箭+卫星）完全不同。
        # 元素严格落在左右窄带（x≤194 / x≥1830），避开主标题墨迹带
        # （两端对齐后墨迹约 x 200–1800、y 360–830）与白卡片（y≥990）。

        def huo_ear(cx_, ridge_y_, half_w_, ear_r_, rise_, al_):
            """镬耳山墙正面剪影：两端圆头镬耳（高出正脊）+ 中间正脊 + 山墙脚，
            画成一条连续轮廓并做半透明填充，才像「屋」而不像几根独立的柱子。
            ⚠️ 镬耳必须由「竖边 + 上半圆」组成；若以正脊端点作圆心画半圆，
            正脊线会把圆切开，看起来像拱桥。"""
            xl, xr = cx_ - half_w_, cx_ + half_w_
            et = ridge_y_ - rise_                        # 镬耳圆头中心 y
            pts = [(xl, ridge_y_ + 30), (xl, et)]
            for k, cxx in enumerate((xl + ear_r_, xr - ear_r_)):
                for i in range(25):                      # 上半圆：180° → 360°
                    a = math.radians(180 + 180 * i / 24)
                    pts.append((cxx + ear_r_ * math.cos(a), et + ear_r_ * math.sin(a)))
                if k == 0:
                    pts.append((xl + 2 * ear_r_, ridge_y_))   # 下到正脊
                    pts.append((xr - 2 * ear_r_, ridge_y_))   # 正脊
                else:
                    pts.append((xr, ridge_y_ + 30))
            dr.polygon(pts, fill=line_c + (al_ // 2,))
            dr.line(pts + [pts[0]], fill=line_c + (al_,), width=4, joint="curve")

        # ① 左侧窄带：两进错落的镬耳山墙（岭南广府民居，前排实、后排淡）
        #    ⚠️ 镬耳以「大圆弧」为主体、竖边极短（rise_ 取 8–14），否则会像两根方柱
        huo_ear(96, 866, 84, 30, 12, 112)
        huo_ear(132, 762, 54, 19, 8, 72)

        # ② 右侧窄带：珠江新城双塔天际线（西塔圆筒 + 东塔方塔）+ 地平线
        #    标题两端对齐后墨迹实测右边界约 x=1802（含描边），故楼体从 1842 起
        dr.line([(1838, 942), (S, 942)], fill=line_c + (52,), width=3)
        xl0, xr0, yt0, yb0 = 1842, 1896, 590, 942
        dr.rounded_rectangle([xl0, yt0, xr0, yb0], radius=14,
                             outline=line_c + (108,), width=4)
        dr.line([((xl0 + xr0) / 2, yt0 - 40), ((xl0 + xr0) / 2, yt0)],
                fill=line_c + (86,), width=3)
        for i in (1, 2, 3):
            xx = xl0 + (xr0 - xl0) * i / 4
            dr.line([(xx, yt0 + 24), (xx, yb0 - 24)], fill=line_c + (34,), width=2)
        for i in range(1, 7):
            yy = yt0 + (yb0 - yt0) * i / 7
            dr.line([(xl0 + 6, yy), (xr0 - 6, yy)], fill=line_c + (34,), width=2)

        xl1, xr1, yt1, yb1 = 1908, 1962, 470, 942
        dr.rectangle([xl1, yt1, xr1, yb1], outline=line_c + (116,), width=4)
        dr.line([(xl1, yt1 + 56), (xr1, yt1)], fill=line_c + (116,), width=4)
        dr.line([((xl1 + xr1) / 2, yt1 - 46), ((xl1 + xr1) / 2, yt1 + 26)],
                fill=C("yellow") + (98,), width=3)
        for i in (1, 2, 3):
            xx = xl1 + (xr1 - xl1) * i / 4
            dr.line([(xx, yt1 + 66), (xx, yb1 - 6)], fill=line_c + (34,), width=2)
        for i in range(1, 8):
            yy = yt1 + 66 + (yb1 - yt1 - 66) * i / 8
            dr.line([(xl1 + 6, yy), (xr1 - 6, yy)], fill=line_c + (32,), width=2)

        # ③ 塔顶航空障碍灯 + 低透明光点（点缀，仍避开标题墨迹）
        for sx_, sy_, r_, al_ in [(1869, 542, 5, 92), (1935, 416, 5, 96),
                                  (52, 700, 4, 62), (180, 668, 4, 58)]:
            dr.ellipse([sx_ - r_, sy_ - r_, sx_ + r_, sy_ + r_], fill=C("yellow") + (al_,))
    elif motif == "yangjiang":
        # 阳江「中国风筝之乡」主题：菱形纸鸢（骨架 + 半透明纸面）+ 尾部蝴蝶结
        # + 引线弧 + 风势弧线（全代码原创矢量）。与已用的各支构图完全不同。
        # 元素严格落在左右窄带（x≤193 / x≥1816）与标题下空档（y 730–850 两侧），
        # 避开主标题墨迹（x 200–1800）与白卡片（card0 起）。
        def bow(x_, y_, r_, col, al_):
            """蝴蝶结：两枚对顶小三角"""
            dr.polygon([(x_ - r_, y_ - r_ * 0.62), (x_, y_), (x_ - r_, y_ + r_ * 0.62)],
                       fill=col + (al_,))
            dr.polygon([(x_ + r_, y_ - r_ * 0.62), (x_, y_), (x_ + r_, y_ + r_ * 0.62)],
                       fill=col + (al_,))

        def kite(cx_, cy_, w_, h_, ang_, al_=112):
            a = math.radians(ang_)
            ca, sa = math.cos(a), math.sin(a)

            def P(dx, dy):
                return (cx_ + dx * ca - dy * sa, cy_ + dx * sa + dy * ca)
            top, bot = P(0, -h_), P(0, h_ * 0.62)
            lf, rt = P(-w_, -h_ * 0.30), P(w_, -h_ * 0.30)
            dr.polygon([top, rt, bot, lf], fill=line_c + (al_ // 3,))
            dr.line([top, rt, bot, lf, top], fill=line_c + (al_,), width=4, joint="curve")
            dr.line([top, bot], fill=C("yellow") + (al_ - 20,), width=3)   # 竖骨
            dr.line([lf, rt], fill=C("yellow") + (al_ - 20,), width=3)     # 横骨
            tx, ty = bot                                                    # 尾：摆动曲线 + 蝴蝶结
            pts = [(tx + 14 * math.sin(i * 1.25), ty + i * 16) for i in range(1, 7)]
            dr.line([bot] + pts, fill=line_c + (al_ - 26,), width=2)
            for i, r_ in enumerate((10, 8, 7)):
                px_, py_ = pts[1 + i * 2]
                bow(px_, py_, r_, C("yellow") if i % 2 else C("cyan"), 120)
            return bot

        def string(p0, x_end, y_end, al_=40):
            pts = []
            for i in range(25):
                t = i / 24
                pts.append((p0[0] + (x_end - p0[0]) * t,
                            p0[1] + (y_end - p0[1]) * (t ** 0.85)))
            dr.line(pts, fill=line_c + (al_,), width=2)

        # ① 左窄带：大风筝（含描边最右不超过 x=193）
        b1 = kite(112, 560, 82, 104, -12)
        string(b1, 66, 1520)

        # ② 右窄带：一中一小两支 + 引线
        b2 = kite(1888, 496, 72, 88, 10)
        string(b2, 1938, 1460)
        b3 = kite(1944, 776, 44, 54, -8)
        string(b3, 1974, 1460, 34)

        # ③ 主标题下空档两侧的小远鸢（避开标签组与白卡片）
        kite(300, 800, 30, 38, 6, 84)
        kite(1656, 812, 26, 32, -7, 76)

        # ④ 风势弧线（低透明，点出风向）
        for x_, y_, r_ in [(430, 470, 90), (1520, 420, 110), (620, 760, 70)]:
            dr.arc([x_ - r_, y_ - r_ * 0.5, x_ + r_, y_ + r_ * 0.5], 190, 330,
                   fill=C("yellow") + (40,), width=3)
    elif motif == "yangjiang":
        # 阳江「滨海风筝之乡」主题：菱形风筝 + 飘带 + 灯塔（海陵岛）+ 海浪线
        # 全代码原创矢量。元素落在左右窄带（x≤195 / x≥1800）与 card0 以上空档，
        # 避开主标题墨迹带（两端对齐后墨迹约 x 200–1800、y 360–830）与白卡片（y≥990）。

        # ① 左侧窄带：大风筝（菱形，斜 -18°）+ 十字骨架 + 波浪尾带 + 放线弧
        kx, ky = 104, 606
        rot = math.radians(-18)
        hw, hh = 74, 104          # 半宽 / 半高

        def kp(dx_, dy_):
            """风筝局部坐标（右为 +x，下为 +y）→ 画布坐标（绕中心转 rot）"""
            rx = dx_ * math.cos(rot) - dy_ * math.sin(rot)
            ry = dx_ * math.sin(rot) + dy_ * math.cos(rot)
            return (kx + rx, ky + ry)

        nose, tail = kp(0, -hh), kp(0, hh)
        wing_l, wing_r = kp(-hw, 0), kp(hw, 0)
        dr.polygon([nose, wing_r, tail, wing_l],
                   fill=line_c + (34,), outline=line_c + (126,), width=4)
        dr.line([nose, tail], fill=line_c + (104,), width=3)
        dr.line([wing_l, wing_r], fill=line_c + (104,), width=3)
        for s_ in (-1, 1):        # 两侧小装饰点
            px_, py_ = kp(s_ * hw * 0.5, -hh * 0.28)
            dr.ellipse([px_ - 6, py_ - 6, px_ + 6, py_ + 6], fill=C("yellow") + (110,))
        # 尾带：三段交替弧 + 两只小蝴蝶结
        tx, ty = tail
        for i, (ax_, ay_, a0, a1) in enumerate([
                (-34, 34, 0, 180), (34, 34, 180, 360), (-30, 30, 0, 180)]):
            bx0 = tx - 34 + i * 34 - ax_ / 2
            by0 = ty + i * 64
            dr.arc([bx0, by0, bx0 + ax_, by0 + ay_], a0, a1,
                   fill=C("yellow") + (88,), width=3)
        for by_ in (ty + 150, ty + 214):
            dr.polygon([(tx - 12, by_), (tx + 12, by_ - 9), (tx + 12, by_ + 9)],
                       fill=C("yellow") + (76,))
        # 放线弧：从风筝中心向左下弯出画面
        pts = []
        for i in range(25):
            t = i / 24
            qx = kx - 26 - 128 * t
            qy = ky + 36 + 268 * t + 34 * math.sin(math.pi * t)
            pts.append((qx, qy))
        dr.line(pts, fill=line_c + (58,), width=2)

        # ② 右侧窄带：海陵岛灯塔（锥台塔身 + 条纹 + 灯室 + 光束）+ 塔基波浪
        lx, top_y, bot_y = 1868, 560, 916
        half_top, half_bot = 26, 44
        dr.polygon([(lx - half_top, top_y), (lx + half_top, top_y),
                    (lx + half_bot, bot_y), (lx - half_bot, bot_y)],
                   fill=line_c + (32,), outline=line_c + (118,), width=4)
        for fy in (0.38, 0.68):   # 塔身条纹
            fy_ = top_y + (bot_y - top_y) * fy
            fw = half_top + (half_bot - half_top) * fy
            dr.line([(lx - fw, fy_), (lx + fw, fy_)], fill=C("red") + (88,), width=5)
        dr.rectangle([lx - 20, top_y - 34, lx + 20, top_y],          # 灯室
                     outline=line_c + (118,), width=3)
        dr.arc([lx - 20, top_y - 56, lx + 20, top_y - 20], 180, 360,
               fill=line_c + (118,), width=3)
        dr.ellipse([lx - 8, top_y - 42, lx + 8, top_y - 26], fill=C("yellow") + (150,))
        for a_ in (208, 232):     # 光束
            r_ = math.radians(a_)
            dr.line([(lx, top_y - 34),
                     (lx + 150 * math.cos(r_), top_y - 34 + 150 * math.sin(r_))],
                    fill=C("yellow") + (40,), width=3)
        for wy_, ww_ in [(944, 70), (972, 52)]:   # 塔基两道波浪短弧
            dr.arc([lx - ww_, wy_ - 14, lx + ww_, wy_ + 14], 190, 350,
                   fill=line_c + (72,), width=3)

        # ③ 海浪线（横贯 card0 以上空档 y≈950，重复半圆波峰，低透明度）
        wy0 = 950
        seg = 118
        xx = 64
        while xx + seg < 1940:
            dr.arc([xx, wy0 - 22, xx + seg, wy0 + 22], 180, 360,
                   fill=line_c + (30,), width=3)
            xx += seg
        for sx_, sy_, r_, al_ in [(320, 906, 4, 56), (1688, 902, 4, 56),
                                  (90, 906, 3, 48), (1908, 900, 3, 48)]:
            dr.ellipse([sx_ - r_, sy_ - r_, sx_ + r_, sy_ + r_], fill=C("cyan") + (al_,))
    elif motif == "gz_tcm":
        # 广州中医药主题：悬壶药葫芦 + 药草枝叶（左窄带）+ 针灸银针（右窄带）
        # + 低透明脉诊脉波（公告名与主标题之间的空档）。全代码原创矢量。
        # 与已用的各支（广州塔 / 日月贝+桥 / 港珠澳大桥 / 原子轨道+木棉 /
        # 荔枝果枝 / 火箭+卫星 / 镬耳山墙+双塔 / 风筝群 / 风筝+灯塔+海浪）构图完全不同。
        # 元素严格落在左右窄带（x≤196 / x≥1806），避开主标题墨迹带（x 200–1800）
        # 与白卡片（x 200–1800，y≥card0）。

        def leaf(x0, y0, ang, ln, wd, al=96):
            """柳叶形药草叶：沿 ang 方向生长，两侧对称收窄"""
            a = math.radians(ang)
            dx, dy = math.cos(a), math.sin(a)
            nx, ny = -dy, dx
            up, dn = [], []
            for i in range(25):
                t = i / 24
                w = wd * math.sin(math.pi * t)
                up.append((x0 + dx * ln * t + nx * w, y0 + dy * ln * t + ny * w))
                dn.append((x0 + dx * ln * t - nx * w, y0 + dy * ln * t - ny * w))
            dr.line(up + list(reversed(dn)) + [up[0]],
                    fill=line_c + (al,), width=3, joint="curve")
            dr.line([(x0, y0), (x0 + dx * ln * 0.9, y0 + dy * ln * 0.9)],
                    fill=line_c + (al,), width=2)

        # ① 左窄带：悬壶（药葫芦）——上小腹 + 下大腹 + 束腰 + 壶嘴 + 系带
        gx, gy = 104, 596
        dr.ellipse([gx - 62, gy - 24, gx + 62, gy + 104],
                   fill=line_c + (34,), outline=line_c + (116,), width=4)
        dr.ellipse([gx - 36, gy - 86, gx + 36, gy - 10],
                   fill=line_c + (34,), outline=line_c + (116,), width=4)
        dr.line([(gx - 30, gy - 8), (gx + 30, gy - 8)], fill=line_c + (108,), width=4)
        dr.rectangle([gx - 13, gy - 116, gx + 13, gy - 86], outline=line_c + (116,), width=4)
        dr.ellipse([gx - 20, gy - 130, gx + 20, gy - 110], fill=C("yellow") + (104,))
        dr.arc([gx - 22, gy - 24, gx + 22, gy + 20], 200, 340,
               fill=C("cyan") + (108,), width=3)

        # ② 左窄带下部：药草枝叶（主枝 + 三片叶，叶片朝向错开避免缠成一团）
        dr.line([(34, 946), (118, 812), (150, 758)],
                fill=line_c + (86,), width=4, joint="curve")
        leaf(84, 880, -120, 100, 26)
        leaf(112, 830, -48, 104, 28)
        leaf(138, 782, -22, 50, 18)

        # ③ 右窄带：针灸银针 ×3（针柄缠绕 + 针身 + 针尖光点）
        def needle(hx, hy, tx, ty):
            vx, vy = tx - hx, ty - hy
            ln = math.hypot(vx, vy)
            ux_, uy_ = vx / ln, vy / ln
            hx2, hy2 = hx + ux_ * 74, hy + uy_ * 74
            dr.line([(hx, hy), (hx2, hy2)], fill=line_c + (124,), width=9)
            for i in range(1, 5):
                t = i / 5
                px_, py_ = hx + ux_ * 74 * t, hy + uy_ * 74 * t
                dr.line([(px_ - uy_ * 8, py_ + ux_ * 8), (px_ + uy_ * 8, py_ - ux_ * 8)],
                        fill=C("yellow") + (104,), width=2)
            dr.line([(hx2, hy2), (tx, ty)], fill=line_c + (116,), width=3)
            dr.ellipse([tx - 5, ty - 5, tx + 5, ty + 5], fill=C("cyan") + (130,))

        needle(1952, 462, 1858, 726)
        needle(1906, 508, 1832, 750)
        needle(1988, 596, 1876, 802)

        # ④ 公告名与主标题之间的空档（y≈356）：低透明脉诊脉波线（三处搏动）
        pulse = [(240, 356), (330, 356), (352, 338), (374, 374), (396, 356), (520, 356),
                 (700, 356), (790, 356), (812, 338), (834, 374), (856, 356), (1080, 356),
                 (1420, 356), (1510, 356), (1532, 338), (1554, 374), (1576, 356), (1760, 356)]
        dr.line(pulse, fill=C("cyan") + (44,), width=3, joint="curve")

        # ⑤ 左右窄带下部散点（药丸/药叶点，低透明度，避开价格与二维码区）
        for sx_, sy_, r_, al_ in [(120, 1128, 7, 54), (1878, 1166, 6, 48),
                                  (146, 1442, 6, 44), (1872, 1408, 5, 42)]:
            dr.ellipse([sx_ - r_, sy_ - r_, sx_ + r_, sy_ + r_], fill=C("cyan") + (al_,))
    elif motif == "gk_zhuanye":
        # 国考（中央机关及其直属机构招录）主题：左窄带「简牍卷轴」（竖竹条 + 双道编绳
        # + 上端卷轴横轴）+ 右窄带「方印」（印面 + 印钮 + 田字印文）+ 低透明云纹点缀。
        # 全代码原创矢量。与已用的各支（广州塔 / 日月贝+桥 / 港珠澳大桥 / 原子轨道+木棉 /
        # 荔枝果枝 / 火箭+卫星 / 镬耳山墙+双塔 / 风筝群 / 风筝+灯塔+海浪 / 药葫芦+银针）
        # 构图完全不同。元素严格落在左右窄带（x≤180 / x≥1822），
        # 避开主标题墨迹带（两端对齐后约 x 197–1803）与白卡片（y≥card0）。

        # ① 左窄带：简牍（5 根竖竹条 + 两道编绳 + 上端卷轴横轴）
        sx0, sw_, gp_, n_str = 44, 18, 4, 5
        sy0, sy1 = 492, 890
        xr_ = sx0 + (n_str - 1) * (sw_ + gp_) + sw_
        for i in range(n_str):
            x_ = sx0 + i * (sw_ + gp_)
            dr.rounded_rectangle([x_, sy0, x_ + sw_, sy1], radius=6,
                                 fill=line_c + (24,), outline=line_c + (104,), width=3)
        for yy in (sy0 + 106, sy1 - 106):
            dr.line([(sx0 - 10, yy), (xr_ + 10, yy)], fill=C("yellow") + (84,), width=4)
        dr.rounded_rectangle([sx0 - 14, sy0 - 48, xr_ + 14, sy0 - 12], radius=18,
                             outline=line_c + (110,), width=4)
        for xx in (sx0 - 14, xr_ + 14):
            dr.ellipse([xx - 9, sy0 - 47, xx + 9, sy0 - 13], fill=line_c + (72,))

        # ② 右窄带：方印（印面 + 印钮 + 田字印文，抽象处理，不做真实文字）
        ix0, iy0, ix1, iy1 = 1840, 648, 1946, 782
        dr.rounded_rectangle([ix0, iy0, ix1, iy1], radius=10,
                             fill=line_c + (26,), outline=line_c + (116,), width=5)
        dr.rounded_rectangle([ix0 + 26, iy0 - 46, ix1 - 26, iy0 + 2], radius=8,
                             outline=line_c + (98,), width=4)
        mxx, myy = (ix0 + ix1) / 2, (iy0 + iy1) / 2
        dr.line([(mxx, iy0 + 14), (mxx, iy1 - 14)], fill=C("yellow") + (76,), width=3)
        dr.line([(ix0 + 14, myy), (ix1 - 14, myy)], fill=C("yellow") + (76,), width=3)
        for qx_, qy_ in ((ix0 + 20, iy0 + 22), (mxx + 12, iy0 + 22),
                         (ix0 + 20, myy + 16), (mxx + 12, myy + 16)):
            dr.line([(qx_ + 15, qy_), (qx_, qy_), (qx_, qy_ + 24)],
                    fill=line_c + (88,), width=3)

        # ③ 低透明云纹（回纹）点缀：公告名与主标题之间的两侧空档
        for cx_, cy_, r_, al_ in [(118, 380, 46, 56), (1888, 392, 40, 52)]:
            dr.arc([cx_ - r_, cy_ - r_ * 0.6, cx_ + r_, cy_ + r_ * 0.6], 190, 350,
                   fill=C("cyan") + (al_,), width=3)
            dr.arc([cx_ - r_ * 0.55, cy_ - r_ * 0.34, cx_ + r_ * 0.55, cy_ + r_ * 0.34],
                   190, 350, fill=C("cyan") + (al_,), width=3)
    elif motif == "gd_jiceng":
        # 广东基层服务岗主题（第 12 支画法）：左窄带「稻穗两株」（基层乡土 + 就业丰收意象）
        # + 右窄带「阶梯上升通道 + 顶部向上箭头」（岗位向上发展）+ 低透明谷粒散点。
        # 全代码原创矢量。与已用各支（广州塔 / 日月贝+桥 / 港珠澳大桥 / 原子轨道+木棉 /
        # 荔枝果枝 / 火箭+卫星 / 镬耳山墙+双塔 / 风筝群 / 风筝+灯塔+海浪 / 药葫芦+银针 /
        # 简牍+方印）构图完全不同。元素严格落在左右窄带（x≤150 / x≥1840），
        # 避开主标题墨迹带（两端对齐后约 x 197–1803）与白卡片（y≥968）。

        def grain(cx, cy, ang, ln, wd, al, aw=True):
            """稻谷粒：沿 ang 方向的水滴形（两端收窄）+ 顶端芒须"""
            a = math.radians(ang)
            dx, dy = math.cos(a), math.sin(a)
            nx, ny = -dy, dx
            up, dn = [], []
            for i in range(17):
                t = i / 16
                w = wd * math.sin(math.pi * t)
                up.append((cx + dx * ln * t + nx * w, cy + dy * ln * t + ny * w))
                dn.append((cx + dx * ln * t - nx * w, cy + dy * ln * t - ny * w))
            dr.polygon(up + list(reversed(dn)), fill=line_c + (al,))
            if aw:
                dr.line([(cx + dx * ln * 0.85, cy + dy * ln * 0.85),
                         (cx + dx * (ln + 18), cy + dy * (ln + 18) - 8)],
                        fill=C("yellow") + (70,), width=2)

        # ① 左窄带：稻穗（下部三片稻叶向外垂落 + 上部穗轴两侧交错着粒）
        #    ⚠️ 谷粒必须「下疏上密」且叶片只放在穗轴下段，否则叶片会横穿谷粒缠成一团
        #    （2026-10-14 首版两株并排实测：谷粒宽 14 / 间距 44 → 连成一条珠链，必须收窄）
        sx0_, sy0_, sx1_, sy1_ = 52, 966, 104, 466
        for t, ang, ln in [(0.06, 122, 92), (0.20, 145, 78), (0.32, 62, 60)]:
            px_ = sx0_ + (sx1_ - sx0_) * t
            py_ = sy0_ + (sy1_ - sy0_) * t
            a_ = math.radians(ang)
            dr.line([(px_, py_), (px_ + math.cos(a_) * ln, py_ + math.sin(a_) * ln)],
                    fill=line_c + (70,), width=4)
        dr.line([(sx0_, sy0_), (sx1_, sy1_)], fill=line_c + (88,), width=5)
        for i in range(9):
            t = 0.32 + 0.68 * i / 8
            px_ = sx0_ + (sx1_ - sx0_) * t
            py_ = sy0_ + (sy1_ - sy0_) * t
            for s in (-1, 1):
                # 靠下偏横、靠上渐竖，谷粒沿穗轴两侧交错斜出
                ang = (-180 + 40 + 18 * i / 8) if s < 0 else (-40 - 18 * i / 8)
                grain(px_ + s * 6, py_, ang, 27, 9.5, 110)

        # ② 右窄带：阶梯上升通道（4 级）+ 顶部向上箭头 + 光点
        stair = [(1840, 906), (1872, 906), (1872, 842), (1904, 842), (1904, 778),
                 (1936, 778), (1936, 714), (1968, 714), (1968, 650)]
        dr.line(stair, fill=line_c + (112,), width=8, joint="curve")
        dr.polygon([(1968, 622), (1948, 660), (1988, 660)], fill=C("yellow") + (128,))
        for sx_, sy_ in [(1872, 874), (1904, 810), (1936, 746)]:
            dr.ellipse([sx_ - 6, sy_ - 6, sx_ + 6, sy_ + 6], fill=C("yellow") + (104,))
        dr.ellipse([1946, 592, 1962, 608], fill=C("cyan") + (118,))

        # ③ 公告名与主标题之间的空档（y≈360）：两侧低透明谷粒小簇
        for cx_, cy_, ang_ in [(70, 362, -60), (96, 352, -118), (122, 368, -66),
                               (1878, 356, -56), (1904, 368, -124), (1930, 352, -62)]:
            grain(cx_, cy_, ang_, 26, 11, 62, aw=False)

        # ④ 左右窄带下部散点（谷粒，低透明，避开价格与二维码区）
        for sx_, sy_, r_, al_ in [(96, 1112, 8, 52), (1866, 1150, 7, 46),
                                  (68, 1330, 7, 42), (1912, 1324, 6, 40),
                                  (140, 1452, 6, 38), (1846, 1436, 6, 36)]:
            dr.ellipse([sx_ - r_, sy_ - r_, sx_ + r_, sy_ + r_], fill=C("cyan") + (al_,))
    elif motif == "jt_haiyun":
        # 交通运输部属事业单位（港航/打捞）主题（第 13 支画法）：
        # 左窄带「岸桥门机」（塔柱 + 悬臂桁架 + 吊钩垂索 + 吊箱）
        # + 右窄带「航标灯塔」（锥形塔身 + 灯室 + 短光束）
        # + 两侧窄带下部「浮标 + 缆绳盘」+ 公告名与主标题之间的航道信号点。
        # 全代码原创矢量，与已用各支（广州塔 / 日月贝+桥 / 港珠澳大桥 / 原子轨道+木棉 /
        # 荔枝果枝 / 火箭+卫星 / 镬耳山墙+双塔 / 风筝群 / 药葫芦+银针 / 简牍+方印 /
        # 稻穗+阶梯）构图完全不同。
        # ⚠️ 元素严格落在左右窄带（x≤150 / x≥1846），避开主标题墨迹带
        #    （两端对齐后约 x 197–1803）与白卡片（y≥968）。

        # ① 左窄带：岸桥门机（塔柱 + 横撑 + 桁架悬臂 + 吊钩垂索 + 吊箱）
        #    ⚠️ 悬臂整体收在 x≤150 内，斜腹杆不得越过标题墨迹左边界（约 197）
        leg_l, leg_r = 62, 112
        top_y, boom_y = 470, 548
        for x_ in (leg_l, leg_r):                       # 两条塔柱
            dr.line([(x_, top_y), (x_, 880)], fill=line_c + (96,), width=8)
        for yy in range(top_y + 86, 880, 86):           # 塔柱横撑
            dr.line([(leg_l, yy), (leg_r, yy)], fill=line_c + (56,), width=3)
        # 悬臂桁架：上弦 + 下弦 + 交错斜腹杆（全段 ≤150）
        bl, br = 46, 150
        dr.polygon([(bl, top_y), (br, top_y), (br, boom_y), (bl, boom_y)], fill=line_c + (16,))
        dr.line([(bl, top_y), (br, top_y)], fill=C("yellow") + (86,), width=5)
        dr.line([(bl, boom_y), (br, boom_y)], fill=line_c + (88,), width=4)
        seg = (br - bl) / 7
        for i in range(7):
            x_a, x_b = bl + i * seg, bl + (i + 1) * seg
            dr.line([(x_a, top_y if i % 2 == 0 else boom_y),
                     (x_b, boom_y if i % 2 == 0 else top_y)],
                    fill=line_c + (72,), width=3)
        # 吊钩垂索 + 吊箱
        dr.line([(130, boom_y), (130, 690)], fill=C("yellow") + (96,), width=3)
        dr.rectangle([112, 690, 148, 736], outline=line_c + (96,), width=4)
        dr.line([(112, 713), (148, 713)], fill=line_c + (70,), width=3)

        # ② 右窄带：航标灯塔（上窄下宽的锥形塔身 + 灯室 + 顶部尖）
        bx0, bx1, by0, by1 = 1868, 1940, 556, 900      # by0=塔顶(窄)，by1=塔底(宽)
        tx0, tx1 = bx0 + 22, bx1 - 22                    # 塔顶窄边
        dr.polygon([(tx0, by0), (tx1, by0), (bx1, by1), (bx0, by1)], fill=line_c + (20,))
        dr.line([(tx0, by0), (bx0, by1)], fill=line_c + (104,), width=4)
        dr.line([(tx1, by0), (bx1, by1)], fill=line_c + (104,), width=4)
        for i in range(1, 4):                            # 塔身分层横线
            t_ = i / 4                                   # t_=0 在塔底
            y_ = by1 - (by1 - by0) * t_
            xl_ = bx0 + (tx0 - bx0) * t_
            xr_ = bx1 + (tx1 - bx1) * t_
            dr.line([(xl_, y_), (xr_, y_)], fill=C("yellow") + (76,), width=4)
        # 灯室（塔顶之上的一层方舱）+ 尖顶 + 舱内灯罩
        dr.rectangle([tx0 - 6, by0 - 52, tx1 + 6, by0 + 2], fill=line_c + (34,),
                     outline=line_c + (112,), width=4)
        dr.polygon([(tx0 - 12, by0 - 52), (tx1 + 12, by0 - 52), (1904, by0 - 92)],
                   fill=line_c + (46,), outline=line_c + (96,))
        dr.ellipse([1891, by0 - 44, 1917, by0 - 18], fill=C("yellow") + (160,))
        # 短光束：自灯罩向左下方斜出，止于 x≥1846（标题墨迹右边界约 1803，安全）
        for k, dy in enumerate((-30, 0, 30)):
            dr.line([(1892, by0 - 30), (1848, by0 - 30 + dy)],
                    fill=C("yellow") + (74 - k * 14,), width=3)

        # ③ 公告名与主标题之间的空档（y≈356）：航道信号灯点
        for sx_, sy_, r_, al_ in [(64, 358, 7, 78), (90, 366, 5, 58), (116, 354, 6, 66),
                                  (1874, 360, 6, 70), (1900, 352, 5, 54), (1926, 366, 7, 64)]:
            dr.ellipse([sx_ - r_, sy_ - r_, sx_ + r_, sy_ + r_], fill=C("yellow") + (al_,))
            dr.ellipse([sx_ - r_ - 4, sy_ - r_ - 4, sx_ + r_ + 4, sy_ + r_ + 4],
                       outline=C("cyan") + (al_ // 3,), width=2)

        # ④ 窄带下部：航道浮标（左）与缆绳盘（右），低透明
        for bx_, by_ in ((78, 1180), (116, 1404)):    # 浮标：锥体 + 灯
            dr.polygon([(bx_ - 22, by_), (bx_ + 22, by_), (bx_ + 9, by_ - 74),
                        (bx_ - 9, by_ - 74)], fill=line_c + (26,),
                       outline=line_c + (92,))
            dr.line([(bx_ - 9, by_ - 74), (bx_ + 9, by_ - 74)], fill=line_c + (86,), width=3)
            dr.ellipse([bx_ - 7, by_ - 94, bx_ + 7, by_ - 80], fill=C("yellow") + (104,))
        for i in range(4):                            # 缆绳盘（同心椭圆）
            rr_ = 28 + i * 12
            dr.ellipse([1906 - rr_, 1268 - rr_ * 0.52, 1906 + rr_, 1268 + rr_ * 0.52],
                       outline=line_c + (58 - i * 8,), width=3)
        for sx_, sy_, r_, al_ in [(1866, 1080, 6, 46), (1920, 1146, 5, 40),
                                  (1862, 1480, 6, 38), (1926, 1444, 5, 34)]:
            dr.ellipse([sx_ - r_, sy_ - r_, sx_ + r_, sy_ + r_], fill=C("cyan") + (al_,))
    elif motif == "zhuhai_edu":
        # 珠海香洲教师招聘：左窄带「三本并立教材 + 顶部横压一本 + 斜置粉笔」，
        # 右窄带「直角三角板 + 圆规」，下部窄带海浪细弧 + 粉笔灰点。
        # 与 zhuhai（日月贝）/ zhuhai_coast（桥面）构图完全不同，全代码原创矢量。
        # ⚠️ 窄带元素一律 x≤150 / x≥1846：标题两端对齐后墨迹实测 197–1803。
        # ① 左窄带：一摞横放的书（自下而上四本、左右错位）+ 书页纹理 + 斜置粉笔
        book_w = 104
        for bx_, bh, y1_ in ((52, 30, 880), (44, 28, 846), (58, 32, 812), (48, 26, 774)):
            y0_ = y1_ - bh
            dr.rectangle([bx_, y0_, bx_ + book_w, y1_], fill=line_c + (20,),
                         outline=line_c + (92,), width=3)
            for k in range(3):
                xx_ = bx_ + book_w - 14 + k * 5
                dr.line([(xx_, y0_ + 6), (xx_, y1_ - 6)], fill=line_c + (56,), width=2)
        # 斜置粉笔（笔身 + 亮黄笔头）
        dr.line([(58, 726), (104, 676)], fill=line_c + (84,), width=16)
        dr.line([(58, 726), (74, 708)], fill=C("yellow") + (92,), width=16)

        # ② 右窄带：直角三角板（外框 + 内框 + 底边刻度）
        ax, ay, bx_, cy_ = 1846, 812, 1958, 588
        dr.polygon([(ax, ay), (bx_, ay), (bx_, cy_)], fill=line_c + (18,),
                   outline=line_c + (94,))
        dr.polygon([(ax + 40, ay - 12), (bx_ - 14, ay - 12), (bx_ - 14, cy_ + 48)],
                   outline=line_c + (76,))
        for k in range(5):
            xs_ = ax + 26 + k * 22
            dr.line([(xs_, ay - 14), (xs_, ay - (26 if k % 2 == 0 else 20))],
                    fill=C("yellow") + (58,), width=3)

        # ③ 右窄带：圆规（顶部铰接 + 双腿 + 调节杆 + 笔尖 / 针尖）
        px_, py_ = 1904, 924
        dr.ellipse([px_ - 17, py_ - 17, px_ + 17, py_ + 17], fill=line_c + (30,),
                   outline=line_c + (100,), width=3)
        dr.line([(px_, py_), (1866, 1160)], fill=line_c + (94,), width=5)
        dr.line([(px_, py_), (1942, 1160)], fill=line_c + (94,), width=5)
        dr.line([(1885, 1032), (1923, 1032)], fill=C("yellow") + (74,), width=4)
        dr.ellipse([1900, 1028, 1908, 1036], fill=C("yellow") + (96,))
        dr.polygon([(1942, 1160), (1932, 1198), (1952, 1198)], fill=line_c + (78,))
        dr.line([(1866, 1160), (1866, 1202)], fill=C("yellow") + (82,), width=4)

        # ④ 下部窄带：海浪细弧（呼应香炉湾）+ 粉笔灰点
        for cy0, w_ in ((1320, 150), (1412, 128)):
            for k in range(3):
                yy = cy0 + k * 12
                pts = [(46 + w_ * t / 30, yy - 6 * math.sin(math.pi * 2 * t / 30))
                       for t in range(31)]
                dr.line(pts, fill=line_c + (max(22, 60 - k * 14),), width=3)
        for sx_, sy_, r_, al_ in ((78, 1244, 5, 52), (124, 1516, 4, 40),
                                  (1886, 1298, 5, 46), (1928, 1420, 4, 38)):
            dr.ellipse([sx_ - r_, sy_ - r_, sx_ + r_, sy_ + r_], fill=C("yellow") + (al_,))
    elif motif == "jw_airshow":
        # 珠海金湾（中国航展举办地 / 航空新城）：左窄带「客机爬升剪影 + 双尾迹弧」，
        # 右窄带「机场管制塔台（塔身 + 玻璃塔帽 + 天线 + 顶部红灯）」+ 星点。
        # 与 zhuhai（日月贝）/ zhuhai_coast（桥面）/ zhuhai_edu（书堆）构图完全不同，全代码原创矢量。
        # ⚠️ 窄带元素一律收在 x≤152 / x≥1846：标题两端对齐后墨迹实测 197–1803。
        def _rot(pts, ang, ox, oy):
            ca, sa = math.cos(ang), math.sin(ang)
            return [(ox + x * ca - y * sa, oy + x * sa + y * ca) for x, y in pts]

        # ① 客机剪影：机头朝右上、机身朝左拖出（局部坐标 x 取负 = 尾在左、头在右）
        k, ang = 0.86, math.radians(-9)
        ox, oy = 146, 606
        body = [(0, 0), (14, -7), (80, -7), (98, -5), (108, 0), (98, 5), (80, 7), (14, 7)]
        wings = ([(38, -6), (10, -40), (24, -40), (56, -6)],
                 [(38, 6), (10, 40), (24, 40), (56, 6)],
                 [(84, -5), (70, -20), (78, -20), (94, -5)],
                 [(84, 5), (70, 20), (78, 20), (94, 5)])
        for poly in wings:
            dr.polygon(_rot([(-x * k, y * k) for x, y in poly], ang, ox, oy),
                       fill=line_c + (34,), outline=line_c + (104,))
        dr.polygon(_rot([(-x * k, y * k) for x, y in body], ang, ox, oy),
                   fill=line_c + (52,), outline=line_c + (124,))
        for t in range(5):                      # 舷窗点
            d_ = (28 + t * 12) * k
            dr.ellipse([ox - d_ * math.cos(ang) - 2, oy - d_ * math.sin(ang) - 2,
                        ox - d_ * math.cos(ang) + 2, oy - d_ * math.sin(ang) + 2],
                       fill=C("yellow") + (135,))

        # ② 双尾迹弧：从机尾向左拖出画外（细、低透明，不穿过机身）
        for dy, al_ in ((9, 56), (-7, 40)):
            pts = [(56 - i * 5.6, oy + 4 + dy + 7 * math.sin(i * 0.16)) for i in range(30)]
            dr.line(pts, fill=line_c + (al_,), width=3)

        # ③ 管制塔台（右窄带）：塔身下宽上窄 + 玻璃塔帽 + 天线 + 顶部红灯
        dr.polygon([(1898, 722), (1918, 722), (1932, 944), (1884, 944)],
                   fill=line_c + (34,), outline=line_c + (120,))
        dr.polygon([(1876, 722), (1942, 722), (1934, 678), (1884, 678)],
                   fill=line_c + (54,), outline=line_c + (132,))
        dr.line([(1870, 722), (1948, 722)], fill=C("yellow") + (128,), width=6)
        for xx in (1898, 1912, 1926):
            dr.line([(xx, 684), (xx, 718)], fill=line_c + (70,), width=2)
        dr.line([(1908, 678), (1908, 606)], fill=line_c + (104,), width=4)
        dr.ellipse([1902, 597, 1914, 609], fill=C("red") + (190,))
        for yy in (786, 852, 918):
            dr.line([(1892, yy), (1924, yy)], fill=line_c + (54,), width=3)

        # ④ 星点（跑道灯 / 夜空）
        for sx_, sy_, r_, al_ in ((72, 436, 5, 62), (152, 540, 4, 46), (1864, 468, 5, 56),
                                  (1930, 838, 4, 44), (98, 936, 4, 40), (1892, 950, 3, 36)):
            dr.ellipse([sx_ - r_, sy_ - r_, sx_ + r_, sy_ + r_], fill=C("yellow") + (al_,))
    elif motif == "grid":
        for i in range(6):
            x = 180 + i * 300
            dr.line([(x, 300), (x, 1500)], fill=line_c + (44,), width=3)
        for j in range(6):
            y = 340 + j * 220
            dr.line([(180, y), (1820, y)], fill=line_c + (44,), width=3)
    return l


def L_water():
    l = new_canvas()
    dr = ImageDraw.Draw(l)
    for y0, amp, per, ph, wd, al in [(1560, 30, 1500, 0.4, 3, 52), (1652, 44, 1150, 1.3, 3, 58),
                                     (1748, 26, 900, 2.4, 2, 44), (1852, 46, 1300, 0.9, 4, 62)]:
        pts = [(S * i / 400, y0 + amp * math.sin(2 * math.pi * (S * i / 400) / per + ph))
               for i in range(401)]
        dr.line(pts, fill=C("cyan") + (al,), width=wd, joint="curve")
    return l


# ---------------- 顶部 ----------------
def L_logo(cfg):
    l = new_canvas()
    logo = Image.open(cfg["logo_path"]).convert("RGBA")
    h = 118
    logo = logo.resize((int(logo.width * h / logo.height), h), Image.LANCZOS)
    px, py, padx, pady = 96, LAYOUT["logo_y"], 30, 20
    pw, ph = logo.width + padx * 2, logo.height + pady * 2
    chip = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    ImageDraw.Draw(chip).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=16, fill=C("white"))
    l.alpha_composite(chip, (px, py))
    l.alpha_composite(logo, (px + padx, py + pady))
    return l


def L_project(cfg):
    l = new_canvas()
    f = F(FT_BOLD, 44)
    tag = cfg["project_tag"]
    w, h = int(f.getlength(tag)) + 92, 78
    box = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(box)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=C("red"))
    d.ellipse([26, h // 2 - 7, 40, h // 2 + 7], fill=C("yellow"))
    d.text((62, h // 2), tag, font=f, fill=C("white"), anchor="lm")
    l.alpha_composite(box, (S - w - 96, 90))
    return l


def L_rule():
    l = new_canvas()
    ImageDraw.Draw(l).line([(96, LAYOUT["rule_y"]), (S - 96, LAYOUT["rule_y"])],
                           fill=C("white") + (58,), width=2)
    return l


def L_notice(cfg):
    """公告名词：字号自适应（长公告名自动缩到不溢出）+ 两侧对称细装饰线。

    公告名长短差异很大（「XX招聘公告」13 字 vs 省市级文件 40+ 字），
    单行居中时短名字会显得单薄、与下方主标题和内容卡片的宽度对不上。
    这里在文字两侧补一对随剩余空间伸缩的细线 + 端点圆点，
    让长短不一的公告名都能撑成一条饱满的「信息条」。
    """
    l = new_canvas()
    text = cfg["notice"]
    y = LAYOUT["notice_y"]
    margin, gap, deco_max = 96, 46, 400
    size = cfg.get("notice_size", 52)
    f = F(FT_REG, size)
    while size > 26 and f.getlength(text) > S - margin * 2 - 2 * (60 + gap):
        size -= 1
        f = F(FT_REG, size)
    tw = f.getlength(text)
    put(l, text_img(text, f, C("light")), S / 2, y)

    seg = min(deco_max, (S - margin * 2 - tw) / 2 - gap)
    if seg >= 40:                       # 名字太长时留不下装饰线就跳过
        dr = ImageDraw.Draw(l)
        for s in (-1, 1):
            x0 = S / 2 + s * (tw / 2 + gap)
            x1 = x0 + s * seg
            dr.line([(x0, y), (x1, y)], fill=C("light") + (96,), width=3)
            dr.ellipse([x1 - 6, y - 6, x1 + 6, y + 6], fill=C("cyan") + (150,))
    return l


# ---------------- 主标题（无 kicker，字距放宽） ----------------
def L_title(cfg):
    l = new_canvas()
    cx = S / 2
    target = cfg.get("title_width", 1600)
    f1 = F(FT_TITLE, cfg.get("title_main_size", 238))
    tracked_segs(l, [(cfg["title_main"], C("white"), C("stroke_w"))], f1, cx, LAYOUT["title_y1"],
                 fit_track(cfg["title_main"], f1, target))
    f2 = F(FT_TITLE, cfg.get("title_sub_size", 198))
    segs = [(t, C("red") if k == "r" else C("white"),
             C("stroke_r") if k == "r" else C("stroke_w"))
            for t, k in cfg["title_sub"]]
    sub_text = "".join(t for t, _ in cfg["title_sub"])
    tracked_segs(l, segs, f2, cx, LAYOUT["title_y2"], fit_track(sub_text, f2, target))
    return l


def _sub_positions(cfg):
    fs, ft = F(FT_HEAVY, 64), F(FT_BOLD, 46)
    ws = int(fs.getlength(cfg["subtitle"])) + 118
    wt = int(ft.getlength(cfg["badge"])) + 60
    gap = 44
    sx = int(S / 2 - (ws + gap + wt) / 2)
    return sx, ws, sx + ws + gap, wt


def L_subtitle2(cfg):
    l = new_canvas()
    fs = F(FT_HEAVY, 64)
    sx, ws, _, _ = _sub_positions(cfg)
    box = Image.new("RGBA", (ws, 102), (0, 0, 0, 0))
    d = ImageDraw.Draw(box)
    d.rounded_rectangle([0, 0, ws - 1, 101], radius=18, fill=C("yellow"))
    d.text((ws / 2, 51), cfg["subtitle"], font=fs, fill=C("ink"), anchor="mm")
    l.alpha_composite(box, (sx, LAYOUT["chip_y"]))
    return l


def L_badge(cfg):
    l = new_canvas()
    ft = F(FT_BOLD, 46)
    _, _, tx, wt = _sub_positions(cfg)
    box = Image.new("RGBA", (wt, 82), (0, 0, 0, 0))
    d = ImageDraw.Draw(box)
    d.rounded_rectangle([2, 2, wt - 3, 79], radius=14, outline=C("cyan"), width=4)
    d.text((wt / 2, 41), cfg["badge"], font=ft, fill=C("cyan"), anchor="mm")
    l.alpha_composite(box, (tx, LAYOUT["badge_y"]))
    return l


# ---------------- 课件卡片（放大撑满，条目数自适应） ----------------
def L_content(cfg):
    l = new_canvas()
    rows = cfg["content_rows"]
    L = LAYOUT
    x0, y0, x1, y1 = 200, L["card0"], 1800, L["card1"]
    box = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    d = ImageDraw.Draw(box)
    d.rounded_rectangle([0, 0, x1 - x0 - 1, y1 - y0 - 1], radius=26, fill=C("white"))
    d.rounded_rectangle([2, 2, x1 - x0 - 3, y1 - y0 - 3], radius=24, outline=C("yellow"), width=5)
    d.text((48, L["ctitle_y"]), cfg["content_title"], font=F(FT_HEAVY, 58), fill=C("red"), anchor="lt")
    d.text((x1 - x0 - 48, L["ctitle_y"] + 32), cfg["content_meta"], font=F(FT_REG, 40),
           fill=C("mute"), anchor="rm")
    d.line([(48, L["divider_y"]), (x1 - x0 - 48, L["divider_y"])], fill=(224, 230, 240), width=2)

    inner_r = x1 - x0 - 48       # 卡片内容右边界
    text_x = 112                 # 名称起始
    size = 48                    # 自适应缩小，保证名称+后缀撑满且不溢出
    while size > 28:
        f = F(FT_BOLD, size)
        wsum = max((f.getlength(r[0]) + (f.getlength(r[1]) if len(r) > 1 else 0) for r in rows
                    if isinstance(r, (list, tuple))), default=0)
        if text_x + wsum + 70 <= inner_r:
            break
        size -= 1
    fn = F(FT_BOLD, size)
    ck = max(11, min(17, int(size * 0.36)))          # 勾选框半高随字号缩放
    for i, row in enumerate(rows):
        name, suffix = (row if isinstance(row, (list, tuple)) else (row, ""))
        cy = L["rows_top"] + i * L["row_h"]
        d.rounded_rectangle([48, cy - ck, 48 + ck * 2, cy + ck], radius=9, fill=C("red"))
        d.line([(48 + ck * 0.6, cy), (48 + ck * 1.25, cy + ck * 0.55),
                (48 + ck * 1.9, cy - ck * 0.62)],
               fill=C("white"), width=max(4, int(size * 0.13)))
        d.text((text_x, cy), name, font=fn, fill=C("ink"), anchor="lm")
        if suffix:
            d.text((inner_r, cy), suffix, font=fn, fill=C("mute"), anchor="rm")
    d.text((48, L["note_y"]), cfg["content_note"], font=F(FT_REG, 38), fill=C("mute"), anchor="lm")
    l.alpha_composite(box, (x0, y0))
    return l


# ---------------- 价格区 ----------------
def dash_rect(d, box, radius, color, width, dash, gap):
    x0, y0, x1, y1 = box
    for a, b in [((x0 + radius, y0), (x1 - radius, y0)), ((x0 + radius, y1), (x1 - radius, y1)),
                 ((x0, y0 + radius), (x0, y1 - radius)), ((x1, y0 + radius), (x1, y1 - radius))]:
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
        t = 0
        while t < length:
            e = min(t + dash, length)
            d.line([(a[0] + ux * t, a[1] + uy * t), (a[0] + ux * e, a[1] + uy * e)],
                   fill=color, width=width)
            t = e + gap
    for cxx, cyy, s in [(x0 + radius, y0 + radius, 90), (x1 - radius, y0 + radius, 0),
                        (x0 + radius, y1 - radius, 180), (x1 - radius, y1 - radius, 270)]:
        d.arc([cxx - radius, cyy - radius, cxx + radius, cyy + radius], s, s + 90,
              fill=color, width=width)


def big_price(layer, value, unit_size, num_size, cx, cy):
    fn = text_img(value, F(FT_TITLE, num_size), C("red"))
    fu = text_img("元", F(FT_TITLE, unit_size), C("yellow"))
    total = fn.size[0] + 14 + fu.size[0]
    x = cx - total / 2
    layer.alpha_composite(fn, (int(x), int(cy - fn.size[1] / 2)))
    layer.alpha_composite(fu, (int(x + fn.size[0] + 14), int(cy - fu.size[1] / 2)))


def L_price(cfg, with_qr):
    l = new_canvas()
    L = LAYOUT
    if with_qr:
        x = 300
        lb = text_img(cfg["price_group"], F(FT_HEAVY, 60), C(cfg.get("price_group_color", "light")))
        l.alpha_composite(lb, (x, int(L["price_group_y"] - lb.size[1] / 2)))
        num = text_img(cfg["price_value"], F(FT_TITLE, 176), C("red"))
        unit = text_img("元", F(FT_TITLE, 92), C("yellow"))
        cy = L["price_num_y"]
        l.alpha_composite(num, (x, int(cy - num.size[1] / 2)))
        l.alpha_composite(unit, (x + num.size[0] + 14, int(cy - unit.size[1] / 2)))
        if cfg["price_single"]:
            add = text_img(cfg["price_single"], F(FT_BOLD, 44), C("mute"))
            sy = L["price_single_y"]
            l.alpha_composite(add, (x, int(sy - add.size[1] / 2)))
            # price_strike=False 时不画删除线（免费/0 元场景用）
            if cfg.get("price_strike", True):
                ImageDraw.Draw(l).line([(x, sy), (x + add.size[0], sy)],
                                       fill=C("mute") + (170,), width=3)
        qs = L["qr_size"]
        qx, qy = 1716 - qs, L["qr_y"]
        qb = Image.new("RGBA", (qs, qs), (0, 0, 0, 0))
        dq = ImageDraw.Draw(qb)
        dq.rounded_rectangle([0, 0, qs - 1, qs - 1], radius=20, fill=C("white"))
        dash_rect(dq, (7, 7, qs - 8, qs - 8), 16, C("mute"), 4, 16, 12)
        l.alpha_composite(qb, (qx, qy))
        put(l, text_img("码上获取", F(FT_HEAVY, 48), C("yellow")), qx + qs / 2, L["qr_label_y"])
    else:
        put(l, text_img("仅售", F(FT_HEAVY, 72), C("white")), 640, L["only_label_y"])
        big_price(l, cfg["only_price"], 112, 218, 1130, L["only_price_y"])
        if cfg["only_sub"]:
            put(l, text_img(cfg["only_sub"], F(FT_BOLD, 46), C("light")), S / 2, L["only_sub_y"])
    return l


def L_claim(cfg):
    l = new_canvas()
    put(l, text_img(cfg["claim"], F(FT_BOLD, 44), C("light")), S / 2, LAYOUT["claim_y"])
    return l


def L_footer(cfg):
    l = new_canvas()
    put(l, text_img(cfg["footer"], F(FT_REG, 32), C("track")), S / 2, LAYOUT["footer_y"])
    return l


def check_copy(cfg):
    texts = []
    def walk(v):
        if isinstance(v, str):
            texts.append(v)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
    walk(cfg)
    hits = {}
    for w in BANNED_WORDS:
        for t in texts:
            # 「第一批 / 第二批 …」是招考批次用词，「第一套 / 第二套 …」是课件套数编号，
            # 都不是广告法的绝对化用语。扫「第一」前先剔除「第N批」「第N套」，避免误报。
            probe = re.sub(r"第[一二三四五六七八九十](批|套)", "", t) if w == "第一" else t
            if w in probe:
                hits.setdefault(w, []).append(t)
    return hits


def build(cfg, with_qr):
    return [
        ("背景-渐变", L_bg()),
        ("背景-地域元素", L_motif(cfg["motif"])),
        ("背景-水纹", L_water()),
        ("顶部细线", L_rule()),
        ("中公教育logo", L_logo(cfg)),
        ("项目标签", L_project(cfg)),
        ("公告名词", L_notice(cfg)),
        ("主标题", L_title(cfg)),
        ("电子课件标签", L_badge(cfg)),
        ("副标题", L_subtitle2(cfg)),
        ("课件内容卡片", L_content(cfg)),
        ("价格区", L_price(cfg, with_qr)),
        ("领取说明", L_claim(cfg)),
        ("底部课件全称", L_footer(cfg)),
    ]


def flatten(layers):
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    for _, im in layers:
        out.alpha_composite(im)
    return out


def save_psd(layers, path):
    """写分层 PSD（RLE 压缩，Photoshop 可直接打开）。

    ⚠️ 不要换回 pytoshop：它用 ZIP 压缩写 PSD，而 PSD(version 1) 的压缩只允许
    Raw/RLE，ZIP 属 PSB(version 2) 特性 —— Photoshop 会报「文件与这个版本的
    Photoshop 不兼容」。它写图层名 Pascal 字符串时还会把 padding 计入长度。
    详见 psd_rle.py 顶部说明。
    """
    import psd_rle
    psd_rle.save_psd(layers, path, S)


def main():
    global S, PAL
    cfg = dict(CONFIG)
    args = sys.argv[1:]
    if "--config" in args:
        with open(args[args.index("--config") + 1], encoding="utf-8") as fh:
            cfg.update(json.load(fh))
    PAL.update(cfg.get("palette", {}))
    S = cfg.get("size", 2000)
    # 版式随课件条目数自适应：>6 条走紧凑版式（否则卡片会溢出到价格区）
    LAYOUT.update(LAYOUT_COMPACT if len(cfg["content_rows"]) > 6 else {})
    LAYOUT.update(cfg.get("layout", {}))   # 单项目微调（如 3 条时收紧 rows_top 留出 note 间距）
    os.makedirs(cfg["out_dir"], exist_ok=True)

    hits = check_copy({k: v for k, v in cfg.items() if k != "palette"})
    if hits:
        print("!! 违规广告词命中：")
        for k, v in hits.items():
            print("   ", k, "->", v)
    else:
        print("OK 文案自检通过（无违规词，无“资料”）")

    for with_qr, suffix in [(True, "有二维码"), (False, "无二维码")]:
        layers = build(cfg, with_qr)
        flat = flatten(layers).convert("RGB")
        p = os.path.join(cfg["out_dir"], f"{cfg['base_name']}_{suffix}.jpg")
        flat.save(p, quality=95, subsampling=0)
        flat.resize((1000, 1000), Image.LANCZOS).save(f"/tmp/preview_{suffix}.jpg", quality=88)
        print("JPG", p)
        if "--psd" in args and with_qr:
            psd = os.path.join(cfg["out_dir"], f"{cfg['base_name']}.psd")
            save_psd(layers, psd)
            print("PSD", psd)


if __name__ == "__main__":
    main()
