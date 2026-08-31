"""BC4 (single channel, 4 bpp) encode / decode helpers."""
import numpy as np


def _palette(r0, r1):
    """r0/r1 shape (N,1); returns (N,8) palette using the r0 > r1 (8 value) mode."""
    r0 = r0.astype(np.float32)
    r1 = r1.astype(np.float32)
    pal = [r0, r1]
    for i in range(1, 7):
        pal.append(((7 - i) * r0 + i * r1) / 7.0)
    return np.concatenate(pal, axis=1)


def encode(img: np.ndarray) -> bytes:
    """img: uint8 (H, W), H and W multiples of 4. Returns linear BC4 blocks."""
    h, w = img.shape
    bh, bw = h // 4, w // 4
    blocks = img.reshape(bh, 4, bw, 4).transpose(0, 2, 1, 3).reshape(-1, 16)

    r0 = blocks.max(axis=1, keepdims=True)
    r1 = blocks.min(axis=1, keepdims=True)
    flat = r0[:, 0] == r1[:, 0]
    pal = _palette(r0, r1)
    dist = np.abs(blocks[:, :, None].astype(np.float32) - pal[:, None, :])
    idx = dist.argmin(axis=2).astype(np.uint64)
    idx[flat] = 0

    packed = np.zeros(len(blocks), dtype=np.uint64)
    for i in range(16):
        packed |= idx[:, i] << np.uint64(3 * i)

    out = np.zeros((len(blocks), 8), dtype=np.uint8)
    out[:, 0] = r0[:, 0]
    out[:, 1] = r1[:, 0]
    for b in range(6):
        out[:, 2 + b] = ((packed >> np.uint64(8 * b)) & np.uint64(0xFF)).astype(np.uint8)
    return out.tobytes()
