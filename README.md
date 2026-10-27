# zhonggong-promo-visuals · 中公推广图视觉产线（完整资源包）

一个**纯代码**的中公教育推广视觉生成技能包：不调用 Photoshop，全部在 Python / HTML+CSS 层完成，
输出高清 JPG 与分层可编辑 PSD。合并「方形产品推广海报」与「通用推广图产线」两套规范，
内置执行脚本、中公 Logo、小鹿 Lulu 形象素材与字体参考图。

> 适合需要**批量、可复现、带合规检查**地产出课程推广海报、小红书封面、直播间装饰、
> 考情一页纸的运营 / 设计团队。

---

## 目录

- [两条产线总览](#两条产线总览)
- [包内资源](#包内资源)
- [环境准备](#环境准备)
- [产线一：方形课程产品推广海报](#产线一方形课程产品推广海报)
  - [四要素输入](#四要素输入)
  - [交付物](#交付物)
  - [设计系统](#设计系统)
  - [地域主题图形（motif）](#地域主题图形motif)
  - [配色（palette）](#配色palette)
  - [版式自适应](#版式自适应)
  - [合规词库与自动检查](#合规词库与自动检查)
- [产线二：通用推广图（HTML → 分层 PSD）](#产线二通用推广图html--分层-psd)
  - [尺寸规范](#尺寸规范)
  - [三条业务路径](#三条业务路径)
  - [渲染管线命令](#渲染管线命令)
- [PSD 技术说明](#psd-技术说明)
- [目录结构](#目录结构)
- [常见问题（FAQ）](#常见问题faq)
- [已知约束](#已知约束)
- [License](#license)

---

## 两条产线总览

| | 产线一：方形推广海报 | 产线二：通用推广图 |
|---|---|---|
| 适用产物 | 方形课程产品海报（默认 2000×2000） | 小红书封面、公众号首图、直播封面 / 贴图、考情一页纸 |
| 实现方式 | Python + Pillow + NumPy，配置驱动 | 每单新写 HTML/CSS → Chromium 截图 → 分层 PSD |
| 核心脚本 | `scripts/poster.py` | `scripts/render_layers.py` + `scripts/psd_from_layers.py` |
| PSD 写入器 | `scripts/psd_rle.py`（RLE 压缩，自研） | `psd_from_layers.py`（pytoshop + 内置补丁） |
| 风格差异 | 每单换 motif 图形 + palette 配色 | 每单新写 HTML，参考往期只提取重点 |

两类产物的尺寸、元素和 PSD 实现分别适用，**不要混用**。

---

## 包内资源

```
scripts/
  poster.py           # 方形海报主脚本（含 CONFIG、合规检查、14 图层 PSD 输出）
  psd_rle.py          # RLE(PackBits) 分层 PSD 写入器（方形海报用）
  render_layers.py    # HTML → 合成 JPG + 分层 PNG（.layer 元素自动识别）
  psd_from_layers.py  # 分层 PNG → PSD（带 pytoshop 全黑 / packbits 修复）
assets/
  brand/zhonggong-logo.png   # 中公教育 Logo
  lulu/                      # 小鹿 Lulu 形象 15 个造型（带透明通道）
  font-reference.jpg         # 字体白名单参考图
requirements.txt              # Python 依赖清单
```

**字体不随包分发**：字体授权 / 再分发范围无法从文件本身验证。运行前需在本机安装
参考图清单内且已获授权的字体（macOS 通常在 `~/Library/Fonts/`），
禁止因缺字体而静默换用未授权字体。Playwright 所需 Chromium 需按运行环境单独安装。

---

## 环境准备

```bash
# 1) Python 依赖（Python ≥ 3.10）
python -m pip install -r requirements.txt

# 2) 产线二首次运行需安装 Chromium
python -m playwright install chromium
```

依赖明细见 `requirements.txt`：Pillow、numpy（共用）；playwright、pytoshop、six（产线二）；
psd-tools（可选，PSD 回读验证）。

---

## 产线一：方形课程产品推广海报

### 四要素输入

提交以下四要素即可生成：

1. **公告名词**（写成「地区 + 年度 + 事项 + 公告」的规范表述，不得带发文机关全称）
2. **课件名称**（含全称，用于底部小字与详情卡片）
3. **内容清单**（课件条目文字或截图）
4. **定价**（拼团价 + 单独购买价，或免费 / 0 元场景）

### 交付物

固定 3 个产物，放进**新建的独立文件夹**：

1. 方形高清 JPG —— 有二维码版（右下虚线空框 +「码上获取」，拼团 / 单独双价）
2. 方形高清 JPG —— 无二维码版（「仅售 …元」单价，无拼团表述）
3. 分层可编辑 **PSD**（14 图层，每个元素独立图层）

产物文件名以「活动图」结尾，输出目录应位于当前工作空间内，
一单一文件夹（建议以「-海报」结尾命名以区分产物类型），完成后清掉脚本临时件与虚拟环境。

### 设计系统

- **版式层级**：Logo → 项目标签 → 公告名词 → 主标题（两端对齐）→ 标签组 →
  课件内容卡片 → 价格区 → 领取说明 → 底部全称小字
- **美术规范**：扁平化，禁止阴影 / 浮雕 / 发光堆叠；活力撞色（宝蓝底 + 珊瑚橙 + 亮黄 + 电光青）；
  强调色用珊瑚橙 `#FA6C4A`，不用纯正红（蓝底上刺眼）
- **字体**：大标题首选方正兰亭粗黑（稳重），不要用特黑档（笔画粘连发糊）；
  白名单详见 SKILL.md 第三节
- **图形元素**：全部代码绘制原创矢量，透明度 0.1–0.25 作背景纹理，落在卡片上沿以上的空档

### 地域主题图形（motif）

`poster.py` 内置 12+ 支原创矢量画法，按项目所在地选用：

`canton_tower`（广州塔）/ `zhuhai`、`zhuhai_coast`（珠海）/ `gd_science`、`gd_science2`
（省级科普）/ `gd_xuandiao`（选调生）/ `yangjiang`（阳江风筝）/ `gz_tcm`（广州中医药）/
`gk_zhuanye`（国考卷轴方印）/ `gd_jiceng`（基层稻穗阶梯）/ `jt_haiyun`（港航岸桥灯塔）/
`jw_airshow`（航空航展）/ `waves` / `grid`

新地区 / 新项目在 motif 函数里新增一支画法即可。同一地区出第二个产品时
**必须换画法 + 换底色**，避免两张海报长得一样。

### 配色（palette）

整套撞色可整体替换，SKILL.md 内含多套实测参数：
墨绿松石（科普）、玫紫（体制类）、紫气东来（民生就业）、深海钢青（港航交通）、
夜航靛紫（航空）、暖阳蜜橘（示例）等。换底色必须同步换主标题描边色与浅色文案，
否则会显脏。配色连续被否时，换「冷暖方向」比换「深浅」有效得多。

另有「背景提亮三件套」（三段渐变 + 光晕强度可配 + 底部压暗层），
专治「底色一暗就闷、单纯提亮又糊掉价格区」的问题，全部可选、向后兼容。

### 版式自适应

- 课件条目 **≤6** 条走默认版式，**>6** 条自动切换紧凑版式（实测 8–9 条可正常排下）
- **5 / 6 条**是「两不靠」边界，必须手写 `layout` 覆盖——SKILL.md 附有实测可用的完整参数
- 二维码框 y 坐标必须 ≥ 卡片下沿，否则会压掉卡片边框
- 估完间距一律出图目检，别信 `textbbox` 算术（中文 bbox 含 ascent/descent 留白，会高估净距）

### 合规词库与自动检查

脚本输出时自动跑 `check_copy()` 文案合规检查，命中即改：

| 禁用 | 替代 |
|---|---|
| 资料 | 课件 |
| 真题 / 押题 | 历年试题 / 冲刺卷 / 模拟卷 |
| 上岸 | 成功入围 / 考入 / 成公 |
| 保过 / 包过 / 必过 / 保分 / 协议班 / 绝密 / 内部 / 命中 / 预测 / 官方指定 / 100% 等 | 删除或改写 |

「第一批 / 第二批」（批次）与「第一套 / 第二套」（套数编号）会自动排除，不误报。

---

## 产线二：通用推广图（HTML → 分层 PSD）

### 尺寸规范

| 类型 | 比例 | 设计坐标 | 出图 |
|---|---|---|---|
| 小红书封面（推广海报） | 3:4 | 540×720 | dsf=2 → 1080×1440，四周 ≥60px 安全边距 |
| 公众号图文首图 | 2.35:1 | 900×383 | dsf=2 → 1800×766，横版分栏 |
| 直播封面 | 3:4 | 540×720 | dsf=2 → 1080×1440 |
| 竖屏直播贴图 | 9:16 | 540×960 | dsf=2 → 1080×1920，中间整块透明 |
| 横屏直播贴图 | 16:9 | 960×540 | dsf=2 → 1920×1080，中间透明 |
| 考情一页纸 | 长图 | 宽 1280 | dsf=2 → 2560 宽，高度自适应 |

### 三条业务路径

- **A. 产品推广海报**（小红书 3:4）：每单新建 build 文件写 HTML/CSS，
  `.layer` 元素 + `data-layer` 名定义图层顺序与中文名
- **B. 直播间装饰三件套**：封面 + 竖贴 + 横贴；中公蓝 + 黄放射光芒视觉体系，
  同系列靠强调色 + 背景纹理 + 主题图形区分场次；竖 / 横贴透明区用
  `omit_background` 区分合成 JPG（白底）与分层 PNG（保透明）
- **C. 考情一页纸**：HTML `<table>` 排版，深墨绿标题栏 + 三列表格 + 底部说明条；
  给 body 加 `no-text` / `no-bg` class 分别整页截图，得到背景层 + 文字层

### 渲染管线命令

```bash
# 1) HTML → 合成 JPG + 分层 PNG（自动等 fonts.ready，逐层隔离截图）
python scripts/render_layers.py <page.html> --out <out_dir> \
  --width 540 --height 720 --dsf 2 [--full-page] [--jpg "成品名.jpg"]

# 2) 分层 PNG → PSD（--layer 按从下到上的顺序重复传入；--flat 必传）
python scripts/psd_from_layers.py --out <成品.psd> --flat <合成图.png> \
  --layer "01-背景:out/page_layers/bg.png" --layer "02-文字:out/page_layers/text.png"
```

`render_layers.py` 输出末尾打印各层覆盖率 %，出现重复层会告警（说明某层截图没隔离干净）。

---

## PSD 技术说明

包内两条 PSD 路径都绕开了常见兼容性坑：

- **方形海报**：自研 `psd_rle.py` 只做「同尺寸 RGBA 图层 → 分层 PSD」一件事。
  压缩统一 RLE (PackBits)，行字节数表按通道优先排列；图层自动裁剪到非透明包围盒；
  图层名同时写 Pascal(UTF-8) 与 `'luni'` Unicode 块。
  实测 2000×2000 / 14 图层：2.8 MB、1.8 秒生成，Photoshop 与 psd-tools 均可正常打开。
  > 为什么不用 pytoshop 写方形海报 PSD：pytoshop 用 ZIP 压缩写 PSD version 1 的图层通道，
  > 而 PSD version 1 只允许 Raw / RLE，Photoshop 会直接判「文件不兼容」；
  > 另有图层名 Pascal 长度把 padding 计入导致尾部带 `\x00` 的问题。
- **分层 PNG → PSD**：`psd_from_layers.py` 内置两个修复——合成图必须以
  `(3,H,W)` 形状写入 `image_data`（否则 PS / 访达缩略图全黑）；
  自带纯 Python PackBits 顶替未编译的 pytoshop Cython packbits。

自检方法（无法调用 Photoshop 时的替代验证）：

```python
from psd_tools import PSDImage
psd = PSDImage.open(path); psd.composite()
```

合成结果与交付 JPG 的差异应恰好是「同图 JPG 往返噪声」量级（quality=95 时约 0.59 平均差）；
注意 PSD 存的是「有二维码版」分层，与无码版的差异只会落在价格区 + 二维码框行带。

---

## 目录结构

```
tyhbzzjn-hwq-gd/
├── README.md
├── LICENSE
├── .gitignore
├── CHANGELOG.md
├── requirements.txt
└── zhonggong-promo-visuals/
    ├── SKILL.md            # 完整技能文档（两套产线的全部规范与踩坑记录）
    ├── scripts/            # 4 个执行脚本
    └── assets/             # Logo / 小鹿 Lulu ×15 / 字体参考图
```

---

## 常见问题（FAQ）

**Q：生成的 PSD 在 Photoshop 里打不开？**
确认不是 pytoshop ZIP 压缩写的旧文件。本包脚本全部走 RLE 压缩，Photoshop 可正常打开。

**Q：PIL 读小鹿素材报 `Too much memory used in text chunks`？**
这是素材 PNG 内置超大 XMP 元数据块导致。随包素材已清理该元数据；
若你替换了新素材，可先用 `sips -Z 1400`（macOS）过一遍再用。

**Q：Chromium 渲染中文出现乱码（如 `ÆÓØÜÝâåäæìíîô÷üýÿ`）？**
正文不要用宋体（Songti SC），改用 PingFang SC；方正系字体走 fc 字体名正常。

**Q：`Path.mkdir(exist_ok=True)` 报错？**
沙箱环境下对已存在目录可能抛错，改用 `if not p.is_dir(): p.mkdir(parents=True)`。

**Q：6 条课件内容排版溢出？**
6 条走的是默认版式（卡片 500px 高），必溢出。不改代码，用 `--config` 传整套
`layout` 覆盖，实测参数见 SKILL.md「已知可用版式」。

---

## 已知约束

- 字体二进制不随包分发（授权原因），需运行设备自装白名单内已授权字体
- Chromium 需按运行环境单独安装（`python -m playwright install chromium`）
- `poster.py` 运行时会在系统临时目录写 1000×1000 预览图，确认交付后清理
- 全图禁止出现「资料」二字（合规口径），一律用「课件」替代
- 公告名不得出现党政机关全称，一律写成「地区 + 年度 + 事项 + 公告」

## License

[MIT](LICENSE) © 2026 黄文钦 (hwq)
