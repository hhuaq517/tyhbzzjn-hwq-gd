# -*- coding: utf-8 -*-
"""render_layers.py —— HTML → 合成 JPG + 分层 PNG

图层约定：HTML 中带 class="layer" data-layer="键名" 的元素，每个是一层；
body 上设 data-only="<键名>" 时只显示该层（页面 CSS 需包含配套规则，见下）。

页面需包含的配套 CSS（可直接复制）：
  body[data-only] .layer:not([data-layer=...]) 隐藏逻辑通常这样写：
  .layer { position:absolute; inset:0; }
  body[data-only="A"] .layer { display:none; }
  body[data-only="A"] .layer[data-layer="A"] { display:block; }
  /* 无 body[data-only] 时所有层正常显示，即合成态 */

用法：
  python3 render_layers.py page.html --out out \
      --width 540 --height 720 --dsf 2 [--full-page] [--jpg "成品名.jpg"]

输出：<out>/<页名>.jpg（合成，白底）、<out>/<页名>_layers/<键名>.png（透明分层）。
末尾打印各层 alpha 覆盖率%，出现重复层会告警（该层没隔离干净）。
"""
import argparse, pathlib, sys
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html", help="HTML 文件路径")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--width", type=int, default=540)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--dsf", type=int, default=2, help="device_scale_factor，出高清图用 2")
    ap.add_argument("--full-page", action="store_true", help="整页截图（长图/高度自适应页面）")
    ap.add_argument("--jpg", default=None, help="合成 JPG 文件名，默认 <页名>.jpg")
    args = ap.parse_args()

    html_path = pathlib.Path(args.html)
    out = pathlib.Path(args.out)
    if not out.is_dir():
        out.mkdir(parents=True)
    key = html_path.stem
    jpg_name = args.jpg or f"{key}.jpg"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": args.width, "height": args.height},
                                device_scale_factor=args.dsf)
        page.set_content(html_path.read_text(encoding="utf-8"), wait_until="load")
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(700)
        if args.full_page:
            print("page height:", page.evaluate("document.documentElement.scrollHeight"))
        layers = page.eval_on_selector_all(".layer", "els => els.map(e => e.dataset.layer)")

        comp = out / f"{key}_raw.png"
        page.screenshot(path=str(comp), full_page=args.full_page, omit_background=False)

        ldir = out / f"{key}_layers"
        ldir.mkdir(exist_ok=True)
        for L in layers:
            page.evaluate(f"document.body.dataset.only='{L}'")
            page.wait_for_timeout(90)
            page.screenshot(path=str(ldir / f"{L}.png"), full_page=args.full_page,
                            omit_background=True)
        page.evaluate("delete document.body.dataset.only")
        page.close()
        browser.close()

    # 合成 JPG（白底、高质量）
    im = Image.open(comp).convert("RGB")
    im.save(out / jpg_name, quality=96, subsampling=0, optimize=True)
    print(f"{jpg_name}: {im.size[0]}x{im.size[1]}")

    # 分层 PNG 重存 + 覆盖率校验
    sigs = {}
    for L in layers:
        li = Image.open(ldir / f"{L}.png").convert("RGBA")
        li.save(ldir / f"{L}.png")
        sigs[L] = round(float((np.array(li)[:, :, 3] > 10).mean()) * 100, 2)
    dup = len(set(sigs.values())) < len(sigs)
    print(f"layers={layers}  覆盖率%={sigs}{'  ⚠️ 存在重复层，检查隔离 CSS!' if dup else ''}")


if __name__ == "__main__":
    main()
