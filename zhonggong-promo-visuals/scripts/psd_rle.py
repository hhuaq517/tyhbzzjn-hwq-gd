# -*- coding: utf-8 -*-
"""
规范 PSD 写入器（RLE 压缩）—— 替代 pytoshop。

为什么不用 pytoshop：
  1. 它用 ZIP 压缩写 PSD（version 1）。PSD 格式的压缩只允许 Raw(0)/RLE(1)，
     ZIP(2/3) 是 PSB(version 2) 的特性，Photoshop 会直接报「文件与这个版本的
     Photoshop 不兼容」。
  2. 它写图层名 Pascal 字符串时把 padding 计入了长度字段，读出来名字尾部带 \\x00。

本模块只做一件事：把一组「同尺寸 RGBA 图层」写成 Photoshop 能打开的分层 PSD。
  - 压缩：RLE (PackBits)，按行压缩，行字节数表按规范写
  - 图层自动裁剪到非透明包围盒（top/left/bottom/right 如实记录）
  - 图层名同时写 Pascal(UTF-8) 与 'luni' Unicode 块
  - Image Resources 写入 ResolutionInfo
"""
import struct
import numpy as np
from PIL import Image

__all__ = ["save_psd"]


def _packbits(a: np.ndarray) -> bytes:
    """PackBits 编码（uint8 一维数组）。numpy 找 run 边界，Python 写字节。"""
    n = a.size
    if n == 0:
        return b""
    if n == 1:
        return bytes((0, int(a[0])))
    change = np.flatnonzero(a[1:] != a[:-1]) + 1
    bounds = np.concatenate(([0], change, [n])).astype(np.int64)
    lens = np.diff(bounds)
    m = lens.size
    out = bytearray()
    i = 0
    while i < m:
        if lens[i] == 1:
            # 累积 literal：连续的「长度 1」run，合计不超过 128 字节
            j = i
            while j < m and lens[j] == 1 and (j - i) < 128:
                j += 1
            lit = a[bounds[i]:bounds[j]].tobytes()
            out.append(len(lit) - 1)
            out += lit
            i = j
        else:
            # 重复 run，拆成不超过 128；重复段最短 2 字节，避免余下 1 字节无法编码
            s, e = int(bounds[i]), int(bounds[i + 1])
            p = s
            while e - p >= 2:
                cl = min(128, e - p)
                if e - p - cl == 1:
                    cl -= 1
                out.append(257 - cl)
                out.append(int(a[p]))
                p += cl
            if p < e:                            # 余下 1 字节按 literal 输出
                out.append(0)
                out.append(int(a[p]))
            i += 1
    return bytes(out)


def _rle_planes(planes, h: int, w: int) -> bytes:
    """把若干通道平面（各 h*w 个 uint8）按 RLE 写成一个数据块。

    格式：compression(2)=1 + 行字节数表(len(planes)*h 个 2 字节大端) + 逐行压缩数据
    行表按「通道优先」排列：通道0的第0..h-1行，通道1的第0..h-1行，……
    """
    counts = np.empty(h * len(planes), dtype=">u2")
    parts = []
    k = 0
    for pl in planes:
        for y in range(h):
            pk = _packbits(pl[y * w:(y + 1) * w])
            counts[k] = len(pk)
            k += 1
            parts.append(pk)
    return struct.pack(">H", 1) + counts.tobytes() + b"".join(parts)


def _pascal(name: str) -> bytes:
    """Pascal 字符串，padding 到 4 字节（padding 不计入长度字段）。"""
    raw = name.encode("utf-8")[:255]
    body = bytes((len(raw),)) + raw
    return body + b"\x00" * ((-len(body)) % 4)


def _luni_block(name: str) -> bytes:
    """'luni' 附加图层信息块（Unicode 图层名）。"""
    data = struct.pack(">I", len(name)) + name.encode("utf-16-be")
    blk = b"8BIM" + b"luni" + struct.pack(">I", len(data)) + data
    return blk + b"\x00" * (len(blk) % 2)


def _resolution_resources(dpi: int = 72) -> bytes:
    """Image Resources：只写 ResolutionInfo(1005)，让 Photoshop 显示正确 DPI。"""
    res = struct.pack(">IHHIHH", dpi << 16, 1, 1, dpi << 16, 1, 1)
    blk = b"8BIM" + struct.pack(">H", 1005) + b"\x00\x00" + struct.pack(">I", len(res)) + res
    return struct.pack(">I", len(blk)) + blk


def _layer_record(name: str, top, left, bottom, right, chan_lens) -> bytes:
    """单个图层记录。chan_lens: [(channel_id, byte_length), ...]"""
    rec = bytearray()
    rec += struct.pack(">4i", top, left, bottom, right)
    rec += struct.pack(">H", len(chan_lens))
    for cid, ln in chan_lens:
        rec += struct.pack(">hI", cid, ln)
    rec += b"8BIM" + b"norm"                    # blend mode signature + 'normal'
    rec += bytes((255, 0, 0, 0))                # opacity / clipping / flags / filler
    extra = bytearray()
    extra += struct.pack(">I", 0)               # 无图层蒙版
    extra += struct.pack(">I", 0)               # 无 blending ranges
    extra += _pascal(name)
    extra += _luni_block(name)
    if len(extra) % 2:                          # extra data 总长须为偶数
        extra += b"\x00"
    rec += struct.pack(">I", len(extra)) + extra
    return bytes(rec)


def save_psd(layers, path: str, size: int, dpi: int = 72):
    """layers: [(图层名, PIL RGBA Image)]，尺寸均为 size×size；列表顺序 = 由下到上。"""
    W = H = size
    records, chan_blobs = [], []

    for name, im in layers:
        if im.size != (W, H):
            raise ValueError(f"图层 {name!r} 尺寸 {im.size} 与画布 {(W, H)} 不符")
        arr = np.asarray(im.convert("RGBA"), dtype=np.uint8)
        alpha = arr[..., 3]
        rows = np.flatnonzero(alpha.any(axis=1))
        cols = np.flatnonzero(alpha.any(axis=0))
        if rows.size:
            top, bottom = int(rows[0]), int(rows[-1]) + 1
            left, right = int(cols[0]), int(cols[-1]) + 1
        else:                                    # 全透明：退化为 1×1
            top, bottom, left, right = 0, 1, 0, 1
        sub = arr[top:bottom, left:right]
        h_, w_ = sub.shape[0], sub.shape[1]

        chan_lens = []
        for idx in (3, 0, 1, 2):                 # 通道 id 顺序：alpha(-1), R, G, B
            plane = np.ascontiguousarray(sub[..., idx]).reshape(-1)
            blob = _rle_planes([plane], h_, w_)
            if len(blob) % 2:
                blob += b"\x00"
            chan_blobs.append(blob)
            chan_lens.append((-1 if idx == 3 else idx, len(blob)))
        records.append(_layer_record(name, top, left, bottom, right, chan_lens))

    # ---- Layer info ----
    layer_info = bytearray()
    layer_info += struct.pack(">h", len(layers))     # 正数：无透明合并通道
    for rec in records:
        layer_info += rec
    for blob in chan_blobs:
        layer_info += blob
    if len(layer_info) % 2:
        layer_info += b"\x00"

    # ---- Layer and Mask Information ----
    lmi = bytearray()
    lmi += struct.pack(">I", len(layer_info)) + layer_info
    lmi += struct.pack(">I", 0)                      # 无 global layer mask info

    # ---- 合并图像（Image Data）----
    flat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for _, im in layers:
        flat.alpha_composite(im)
    rgb = np.asarray(flat.convert("RGB"), dtype=np.uint8)
    planes = [np.ascontiguousarray(rgb[..., i]).reshape(-1) for i in range(3)]
    image_data = _rle_planes(planes, H, W)

    # ---- 组装 ----
    out = bytearray()
    out += b"8BPS" + struct.pack(">H", 1) + b"\x00" * 6
    out += struct.pack(">HIIHH", 3, H, W, 8, 3)      # channels / H / W / depth / RGB
    out += struct.pack(">I", 0)                      # Color Mode Data 长度 0
    out += _resolution_resources(dpi)
    out += struct.pack(">I", len(lmi)) + lmi
    out += image_data
    with open(path, "wb") as fh:
        fh.write(bytes(out))
    return len(out)
