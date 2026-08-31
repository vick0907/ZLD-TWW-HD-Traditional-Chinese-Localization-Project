"""Wii U (GX2 / Latte) surface tiling address computation.

Reimplementation of the AMD R600-family address library parameters used by the
Wii U GPU: 2 pipes, 4 banks, 256-byte pipe interleave.
"""

M_BANKS = 4
M_BANKS_BITCOUNT = 2
M_PIPES = 2
M_PIPES_BITCOUNT = 1
M_PIPE_INTERLEAVE_BYTES = 256
M_PIPE_INTERLEAVE_BYTES_BITCOUNT = 8
M_ROW_SIZE = 2048
M_SWAP_SIZE = 256
M_SPLIT_SIZE = 2048

MICRO_TILE_PIXELS = 64
BANK_SWAP_ORDER = [0, 1, 3, 2, 6, 7, 5, 4]

MICRO_TILE_DISPLAYABLE = 0
MICRO_TILE_NON_DISPLAYABLE = 1
MICRO_TILE_DEPTH_SAMPLE_ORDER = 2
MICRO_TILE_THICK = 3


def surface_thickness(tile_mode: int) -> int:
    if tile_mode in (3, 7, 11, 13, 15):
        return 4
    if tile_mode in (16, 17):
        return 8
    return 1


def is_thick_macro_tiled(tile_mode: int) -> bool:
    return tile_mode in (7, 11, 13, 15)


def is_bank_swapped(tile_mode: int) -> bool:
    return tile_mode in (8, 9, 10, 11, 14, 15)


def macro_tile_aspect_ratio(tile_mode: int) -> int:
    if tile_mode in (5, 9):
        return 2
    if tile_mode in (6, 10):
        return 4
    return 1


def surface_rotation(tile_mode: int) -> int:
    if 4 <= tile_mode <= 11:
        return M_PIPES * ((M_BANKS >> 1) - 1)
    if 12 <= tile_mode <= 15:
        return 1
    return 0


def pixel_index_within_micro_tile(x, y, z, bpp, tile_mode, is_depth):
    thickness = surface_thickness(tile_mode)
    x0, x1, x2 = x & 1, (x >> 1) & 1, (x >> 2) & 1
    y0, y1, y2 = y & 1, (y >> 1) & 1, (y >> 2) & 1
    z0, z1, z2 = z & 1, (z >> 1) & 1, (z >> 2) & 1
    b6 = b7 = b8 = 0

    if is_depth:
        b0, b1, b2, b3, b4, b5 = x0, y0, x1, y1, x2, y2
    elif bpp == 8:
        b0, b1, b2, b3, b4, b5 = x0, x1, x2, y1, y0, y2
    elif bpp == 16:
        b0, b1, b2, b3, b4, b5 = x0, x1, x2, y0, y1, y2
    elif bpp in (32, 96):
        b0, b1, b2, b3, b4, b5 = x0, x1, y0, x2, y1, y2
    elif bpp in (64, 128):
        # verified against the game's own CKingMsg.bffnt sheets
        b0, b1, b2, b3, b4, b5 = x0, y0, x1, x2, y1, y2
    else:
        b0, b1, b2, b3, b4, b5 = x0, x1, y0, x2, y1, y2

    if thickness > 1:
        b6, b7 = z0, z1
    if thickness == 8:
        b8 = z2

    return (b8 << 8) | (b7 << 7) | (b6 << 6) | (b5 << 5) | (b4 << 4) | \
           (b3 << 3) | (b2 << 2) | (b1 << 1) | b0


def pipe_from_coord(x, y):
    return ((y >> 3) ^ (x >> 3)) & 1


def bank_from_coord(x, y):
    bank_bit0 = ((y // (16 * M_PIPES)) ^ (x >> 3)) & 1
    bank_bit1 = ((y // (8 * M_PIPES)) ^ (x >> 4)) & 1
    return bank_bit0 | (bank_bit1 << 1)


def bank_swapped_width(tile_mode, bpp, num_samples, pitch):
    if not is_bank_swapped(tile_mode):
        return 0
    bytes_per_sample = 8 * bpp
    slices_per_tile = 1
    if bytes_per_sample:
        samples_per_tile = M_SPLIT_SIZE // bytes_per_sample
        if samples_per_tile:
            slices_per_tile = max(1, num_samples // samples_per_tile)
    if is_thick_macro_tiled(tile_mode):
        num_samples = 4
    bytes_per_tile_slice = num_samples * bytes_per_sample // slices_per_tile
    factor = macro_tile_aspect_ratio(tile_mode)
    swap_tiles = max(1, (M_SWAP_SIZE >> 1) // bpp)
    swap_width = swap_tiles * 8 * M_BANKS
    height_bytes = num_samples * factor * M_PIPES * bpp // slices_per_tile
    swap_max = M_PIPES * M_BANKS * M_ROW_SIZE // height_bytes
    swap_min = M_PIPE_INTERLEAVE_BYTES * 8 * M_BANKS // bytes_per_tile_slice
    width = min(swap_max, max(swap_min, swap_width))
    while width >= 2 * pitch:
        width >>= 1
    return width


def addr_micro_tiled(x, y, z, bpp, pitch, height, tile_mode, is_depth):
    thickness = surface_thickness(tile_mode)
    micro_tile_bytes = (MICRO_TILE_PIXELS * thickness * bpp + 7) // 8
    micro_tiles_per_row = pitch >> 3
    micro_tile_index_x = x >> 3
    micro_tile_index_y = y >> 3
    micro_tile_index_z = z // thickness
    micro_tile_offset = micro_tile_bytes * (
        micro_tile_index_x + micro_tile_index_y * micro_tiles_per_row)
    slice_bytes = (pitch * height * thickness * bpp + 7) // 8
    slice_offset = slice_bytes * micro_tile_index_z
    pixel_index = pixel_index_within_micro_tile(x, y, z, bpp, tile_mode, is_depth)
    pixel_offset = (bpp * pixel_index) >> 3
    return pixel_offset + micro_tile_offset + slice_offset


def addr_macro_tiled(x, y, z, sample, bpp, pitch, height, num_samples,
                     tile_mode, is_depth, pipe_swizzle, bank_swizzle):
    thickness = surface_thickness(tile_mode)
    micro_tile_bits = num_samples * bpp * (thickness * MICRO_TILE_PIXELS)
    micro_tile_bytes = (micro_tile_bits + 7) // 8

    pixel_index = pixel_index_within_micro_tile(x, y, z, bpp, tile_mode, is_depth)
    if is_depth:
        sample_offset = bpp * sample
        pixel_offset = num_samples * bpp * pixel_index
    else:
        sample_offset = sample * (micro_tile_bits // num_samples)
        pixel_offset = bpp * pixel_index
    elem_offset = pixel_offset + sample_offset

    bytes_per_sample = micro_tile_bits // num_samples
    if num_samples <= 1 or micro_tile_bytes <= M_SPLIT_SIZE:
        num_sample_splits = 1
        sample_slice = 0
    else:
        samples_per_slice = M_SPLIT_SIZE // bytes_per_sample
        num_sample_splits = max(1, num_samples // samples_per_slice)
        num_samples = samples_per_slice
        temp = micro_tile_bits // num_sample_splits
        sample_slice = elem_offset // temp
        elem_offset %= temp
    elem_offset >>= 3

    pipe = pipe_from_coord(x, y)
    bank = bank_from_coord(x, y)
    bank_pipe = pipe + M_PIPES * bank
    rotation = surface_rotation(tile_mode)
    swizzle = pipe_swizzle + M_PIPES * bank_swizzle
    slice_in = z
    if is_thick_macro_tiled(tile_mode):
        slice_in >>= 2
    bank_pipe ^= M_PIPES * sample_slice * ((M_BANKS >> 1) + 1) ^ (swizzle + slice_in * rotation)
    bank_pipe %= M_PIPES * M_BANKS
    pipe = bank_pipe % M_PIPES
    bank = bank_pipe // M_PIPES

    slice_bytes = (height * pitch * thickness * bpp * num_samples + 7) // 8
    slice_offset = slice_bytes * ((sample_slice + num_sample_splits * z) // thickness)

    macro_tile_pitch = 8 * M_BANKS
    macro_tile_height = 8 * M_PIPES
    if tile_mode in (5, 9):
        macro_tile_pitch >>= 1
        macro_tile_height *= 2
    elif tile_mode in (6, 10):
        macro_tile_pitch >>= 2
        macro_tile_height *= 4

    macro_tiles_per_row = pitch // macro_tile_pitch
    macro_tile_bytes = (num_samples * thickness * bpp * macro_tile_height *
                        macro_tile_pitch + 7) // 8
    macro_tile_index_x = x // macro_tile_pitch
    macro_tile_index_y = y // macro_tile_height
    macro_tile_offset = (macro_tile_index_x +
                         macro_tiles_per_row * macro_tile_index_y) * macro_tile_bytes

    if is_bank_swapped(tile_mode):
        width = bank_swapped_width(tile_mode, bpp, num_samples, pitch)
        if width:
            swap_index = macro_tile_pitch * macro_tile_index_x // width
            bank ^= BANK_SWAP_ORDER[swap_index & (M_BANKS - 1)]

    group_mask = (1 << M_PIPE_INTERLEAVE_BYTES_BITCOUNT) - 1
    num_swizzle_bits = M_BANKS_BITCOUNT + M_PIPES_BITCOUNT
    total_offset = elem_offset + ((macro_tile_offset + slice_offset) >> num_swizzle_bits)
    offset_high = (total_offset & ~group_mask) << num_swizzle_bits
    offset_low = total_offset & group_mask
    bank_bits = bank << (M_PIPES_BITCOUNT + M_PIPE_INTERLEAVE_BYTES_BITCOUNT)
    pipe_bits = pipe << M_PIPE_INTERLEAVE_BYTES_BITCOUNT
    return bank_bits | pipe_bits | offset_low | offset_high


def build_address_map(width, height, bpp, tile_mode, swizzle,
                      is_depth=False, slice_index=0):
    """Return list mapping linear element index -> byte offset in tiled data."""
    pipe_swizzle = (swizzle >> 8) & 1 if swizzle > 7 else swizzle & 1
    bank_swizzle = (swizzle >> 9) & 3 if swizzle > 7 else (swizzle >> 1) & 3
    bytes_per_elem = bpp // 8
    out = [0] * (width * height)
    macro = tile_mode >= 4
    for y in range(height):
        row = y * width
        for x in range(width):
            if macro:
                addr = addr_macro_tiled(x, y, slice_index, 0, bpp, width, height, 1,
                                        tile_mode, is_depth, pipe_swizzle, bank_swizzle)
            else:
                addr = addr_micro_tiled(x, y, slice_index, bpp, width, height,
                                        tile_mode, is_depth)
            out[row + x] = addr
    return out, bytes_per_elem


def untile(data: bytes, width, height, bpp, tile_mode, swizzle, slice_index=0,
           is_depth=False) -> bytes:
    addrs, n = build_address_map(width, height, bpp, tile_mode, swizzle,
                                 is_depth, slice_index)
    out = bytearray(width * height * n)
    for i, addr in enumerate(addrs):
        out[i * n:i * n + n] = data[addr:addr + n]
    return bytes(out)


def tile(data: bytes, width, height, bpp, tile_mode, swizzle, slice_index=0,
         is_depth=False) -> bytes:
    addrs, n = build_address_map(width, height, bpp, tile_mode, swizzle,
                                 is_depth, slice_index)
    out = bytearray(max(addrs) + n)
    for i, addr in enumerate(addrs):
        out[addr:addr + n] = data[i * n:i * n + n]
    return bytes(out)
