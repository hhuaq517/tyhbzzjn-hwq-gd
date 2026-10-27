# -*- coding: utf-8 -*-
"""psd_from_layers.py —— 分层 PNG → 可编辑 PSD

内置两个关键修复：
1. pytoshop 自带 packbits 是未编译 .pyx 会挂，用纯 Python RLE 顶替；
2. 显式写入合成图（--flat），否则 PSD 在 PS / 访达缩略图里全黑。

用法（--layer 按从下到上的顺序重复传入，名字即 PS 图层名）：
  python3 psd_from_layers.py --out 成品.psd --flat 合成图.png \
      --layer "01-背景:out/page_layers/bg.png" \
      --layer "02-文字内容:out/page_layers/text.png"
"""
import argparse
import types

import numpy as np
from PIL import Image
from pytoshop import enums, codecs, core
from pytoshop.user import nested_layers


# ---- packbits 补丁 ----
def _pb_encode(data):
    if isinstance(data, np.ndarray):
        data = data.tobytes()
    out = bytearray()
    i, n = 0, len(data)
    while i < n:
        run = 1
        while i + run < n and run < 128 and data[i + run] == data[i]:
            run += 1
        if run >= 2:
            out.append((257 - run) & 0xFF)
            out.append(data[i])
            i += run
        else:
            j = i + 1
            while j < n and (j - i) < 128:
                if j + 1 < n and data[j] == data[j + 1]:
                    break
                j += 1
            lit = data[i:j]
            out.append(len(lit) - 1)
            out.extend(lit)
            i = j
    return bytes(out)


codecs.packbits = types.SimpleNamespace(encode=_pb_encode)


def channels(path):
    a = np.ascontiguousarray(np.array(Image.open(path).convert("RGBA")))
    return {
        enums.ChannelId.red: a[:, :, 0],
        enums.ChannelId.green: a[:, :, 1],
        enums.ChannelId.blue: a[:, :, 2],
        enums.ChannelId.transparency: a[:, :, 3],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="输出 PSD 路径")
    ap.add_argument("--flat", required=True, help="合成图 PNG/JPG（嵌入防全黑）")
    ap.add_argument("--layer", action="append", required=True,
                    help="格式 '图层名:png路径'，按从下到上的顺序重复传入")
    args = ap.parse_args()

    layers = []
    for spec in args.layer:
        name, _, path = spec.partition(":")
        layers.append(nested_layers.Image(
            name=name, visible=True, opacity=255, group_id=0,
            blend_mode=enums.BlendMode.normal, top=0, left=0,
            channels=channels(path),
        ))
    psd = nested_layers.nested_layers_to_psd(layers, color_mode=enums.ColorMode.rgb,
                                             compression=enums.Compression.rle)
    # 关键：显式写合成图，形状必须是 (3,H,W)（不是 H,W,3），否则全黑
    flat = np.ascontiguousarray(
        np.array(Image.open(args.flat).convert("RGB")).transpose(2, 0, 1))
    psd.image_data = core.ImageData(flat)
    psd.image_data.compression = enums.Compression.rle

    with open(args.out, "wb") as f:
        psd.write(f)
    print(f"{args.out}  {__import__('os').path.getsize(args.out)/1e6:.1f}MB  "
          f"layers={[n for n, _, _ in (s.partition(':') for s in args.layer)]}")


if __name__ == "__main__":
    main()
