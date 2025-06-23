"""Partial implementation of the deprecated audioop module.

Only supports:
  - widths 1, 2, and 4
  - signed samples
  - tomono, tostereo, lin2lin, ratecv
"""

import math
import struct
from typing import Final, List, Optional, Tuple, Union

BufferType = Union[bytes, bytearray]
State = Tuple[int, Tuple[Tuple[int, ...], ...]]

# width = (_, 1, 2, _, 4)
_MAX_VALS: Final = [0, 0x7F, 0x7FFF, 0, 0x7FFFFFFF]
_MIN_VALS: Final = [0, -0x80, -0x8000, 0, -0x80000000]
_SIGNED_FORMATS: Final = ["", "b", "h", "", "i"]
_UNSIGNED_FORMATS: Final = ["", "B", "H", "", "I"]


def check_size(size: int) -> None:
    if size not in (1, 2, 4):
        raise ValueError(f"Size should be 1, 2, 4. Got {size}")


def check_parameters(fragment_length: int, size: int) -> None:
    check_size(size)
    if (fragment_length % size) != 0:
        raise ValueError(
            "Not a whole number of frames: "
            f"fragment_length={fragment_length}, size={size}"
        )


def fbound(val: float, min_val: float, max_val: float) -> int:
    if val > max_val:
        val = max_val
    elif val < (min_val + 1):
        val = min_val

    val = math.floor(val)

    return int(val)


def tomono(
    fragment: BufferType, width: int, lfactor: float, rfactor: float
) -> BufferType:
    fragment_length = len(fragment)
    check_parameters(fragment_length, width)

    max_val = _MAX_VALS[width]
    min_val = _MIN_VALS[width]
    struct_format = _SIGNED_FORMATS[width]
    result = bytearray(fragment_length // 2)

    for i in range(0, fragment_length, width * 2):
        val_left = struct.unpack_from(struct_format, fragment, i)[0]
        val_right = struct.unpack_from(struct_format, fragment, i + width)[0]
        val_mono = (val_left * lfactor) + (val_right * rfactor)
        sample_mono = fbound(val_mono, min_val, max_val)
        struct.pack_into(struct_format, result, i // 2, sample_mono)

    return result


def tostereo(
    fragment: BufferType, width: int, lfactor: float, rfactor: float
) -> BufferType:
    fragment_length = len(fragment)
    check_parameters(fragment_length, width)

    max_val = _MAX_VALS[width]
    min_val = _MIN_VALS[width]
    struct_format = _SIGNED_FORMATS[width]
    result = bytearray(fragment_length * 2)

    for i in range(0, fragment_length, width):
        val_mono = struct.unpack_from(struct_format, fragment, i)[0]
        sample_left = fbound(val_mono * lfactor, min_val, max_val)
        sample_right = fbound(val_mono * rfactor, min_val, max_val)
        struct.pack_into(struct_format, result, i * 2, sample_left)
        struct.pack_into(struct_format, result, (i * 2) + width, sample_right)

    return result


def _get_sample32(fragment: BufferType, width: int, index: int) -> int:
    if width == 1:
        return fragment[index]

    if width == 2:
        return (fragment[index] << 8) + (fragment[index + 1])

    if width == 4:
        return (
            (fragment[index] << 24)
            + (fragment[index + 1] << 16)
            + (fragment[index + 2] << 8)
            + fragment[index + 3]
        )

    raise ValueError(f"Invalid width: {width}")


def _set_sample32(fragment: bytearray, width: int, index: int, sample: int) -> None:
    if width == 1:
        fragment[index] = sample & 0x000000FF
    elif width == 2:
        fragment[index] = (sample >> 8) & 0x000000FF
        fragment[index + 1] = sample & 0x000000FF
    elif width == 4:
        fragment[index] = sample >> 24
        fragment[index + 1] = (sample >> 16) & 0x000000FF
        fragment[index + 2] = (sample >> 8) & 0x000000FF
        fragment[index + 3] = sample & 0x000000FF
    else:
        raise ValueError(f"Invalid width: {width}")


def lin2lin(fragment: BufferType, width: int, new_width: int) -> BufferType:
    if width == new_width:
        return fragment

    fragment_length = len(fragment)
    check_parameters(fragment_length, width)
    check_size(new_width)

    result = bytearray(int((fragment_length / width) * new_width))

    j = 0
    for i in range(0, fragment_length, width):
        sample = _get_sample32(fragment, width, i)
        _set_sample32(result, new_width, j, sample)
        j += new_width

    return result


def ratecv(
    fragment: BufferType,
    width: int,
    nchannels: int,
    inrate: int,
    outrate: int,
    state: Optional[State],
    weightA: int = 1,
    weightB: int = 0,
) -> Tuple[bytearray, Optional[State]]:
    fragment_length = len(fragment)
    check_size(width)
    if nchannels < 1:
        raise ValueError(f"Number of channels should be >= 1, got {nchannels}")
    bytes_per_frame = width * nchannels
    if (weightA < 1) or (weightB) < 0:
        raise ValueError(
            "weightA should be >= 1, weightB should be >= 0, "
            f"got weightA={weightA}, weightB={weightB}"
        )

    if (fragment_length % bytes_per_frame) != 0:
        raise ValueError("Not a whole number of frames")

    if (inrate <= 0) or (outrate <= 0):
        raise ValueError("Sampling rate not > 0")

    d = math.gcd(inrate, outrate)
    inrate //= d
    outrate //= d

    d = math.gcd(weightA, weightB)
    weightA //= d
    weightB //= d

    prev_i: List[int] = [0] * nchannels
    cur_i: List[int] = [0] * nchannels

    if state is None:
        d = -outrate
        # prev_i and cur_i are already zeroed
    else:
        d, samps = state
        if len(samps) != nchannels:
            raise ValueError("Illegal state argument")

        for chan_index, channel in enumerate(samps):
            prev_i[chan_index], cur_i[chan_index] = channel

    input_frames = fragment_length // bytes_per_frame
    output_frames = int(math.ceil(input_frames * (outrate / inrate)))

    # Approximate version used in C code to avoid overflow:
    # q = 1 + ((input_frames - 1) // inrate)
    # output_frames = q * outrate * bytes_per_frame

    result = bytearray(output_frames * bytes_per_frame)
    struct_format = _SIGNED_FORMATS[width]

    input_index = 0
    output_index = 0
    while True:
        while d < 0:
            if input_frames == 0:
                samps = tuple(
                    (prev_i[chan], cur_i[chan]) for chan in range(0, nchannels)
                )

                # NOTE: It's critical that result is clipped here
                return result[:output_index], (d, samps)

            for chan in range(0, nchannels):
                prev_i[chan] = cur_i[chan]
                cur_i[chan] = struct.unpack_from(struct_format, fragment, input_index)[
                    0
                ]
                input_index += width
                cur_i[chan] = ((weightA * cur_i[chan]) + (weightB * prev_i[chan])) // (
                    weightA + weightB
                )

            input_frames -= 1
            d += outrate
        while d >= 0:
            for chan in range(0, nchannels):
                sample = int(
                    (
                        (float(prev_i[chan]) * float(d))
                        + (float(cur_i[chan]) * (float(outrate) - float(d)))
                    )
                    / float(outrate)
                )
                struct.pack_into(struct_format, result, output_index, sample)
                output_index += width
            d -= inrate

    return result, None
