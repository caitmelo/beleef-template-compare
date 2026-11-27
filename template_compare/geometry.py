"""Box and colour helpers. New code.

The hex formatting of a drawing colour follows the ``h`` helper inside ``show``
in ``original/comp.py``.
"""

from __future__ import annotations

import pymupdf


def hex_from_rgb(color) -> str | None:
    """Turn a 0..1 RGB tuple or an integer into ``#RRGGBB``.

    Adapted from the ``h`` helper inside ``show`` in ``original/comp.py``.
    """

    if color is None:
        return None
    if isinstance(color, int) and not isinstance(color, bool):
        return f"#{color & 0xFFFFFF:06X}"
    if isinstance(color, (tuple, list)) and len(color) >= 3:
        channels = []
        for value in color[:3]:
            number = float(value)
            if number <= 1:
                number = number * 255
            channels.append(max(0, min(255, int(round(number)))))
        return "#{:02X}{:02X}{:02X}".format(*channels)
    return None


def channel_delta(left: str | None, right: str | None) -> int | None:
    if not left or not right:
        return None
    try:
        a = _channels(left)
        b = _channels(right)
    except ValueError:
        return None
    return max(abs(a[i] - b[i]) for i in range(3))


def _channels(value: str) -> tuple[int, int, int]:
    text = value.lstrip("#")
    if len(text) != 6:
        raise ValueError(text)
    return tuple(int(text[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def box_iou(a, b) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = ix1 - ix0, iy1 - iy0
    if iw <= 0 or ih <= 0:
        return 0.0
    inter = iw * ih
    area_a = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
    area_b = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    union = area_a + area_b - inter
    if union <= 0:
        return 0.0
    return inter / union


def center_inside(inner, outer, pad: float = 0.0) -> bool:
    cx = (inner[0] + inner[2]) / 2
    cy = (inner[1] + inner[3]) / 2
    return (outer[0] - pad) <= cx <= (outer[2] + pad) and (outer[1] - pad) <= cy <= (outer[3] + pad)


def expand(box, pad: float):
    return (box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad)


def near(a, b, gap: float) -> bool:
    return box_iou(expand(a, gap), expand(b, gap)) > 0 or (
        a[0] <= b[2] + gap and b[0] <= a[2] + gap and a[1] <= b[3] + gap and b[1] <= a[3] + gap
    )


def union(boxes):
    return (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )


def fraction_box(rect, trim) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = trim
    width = x1 - x0
    height = y1 - y0
    return (
        (rect.x0 - x0) / width,
        (rect.y0 - y0) / height,
        (rect.x1 - x0) / width,
        (rect.y1 - y0) / height,
    )


def rect_from_fraction(trim, box) -> pymupdf.Rect:
    """Map a trim-fraction box onto page coordinates.

    Adapted from ``R`` in ``original/markup2.py``.
    """

    x0, y0, x1, y1 = trim
    width = x1 - x0
    height = y1 - y0
    return pymupdf.Rect(
        x0 + box[0] * width,
        y0 + box[1] * height,
        x0 + box[2] * width,
        y0 + box[3] * height,
    )


def pt_to_mm(points: float) -> float:
    return points / 72.0 * 25.4


def trim_size_mm(trim) -> tuple[float, float]:
    return pt_to_mm(trim[2] - trim[0]), pt_to_mm(trim[3] - trim[1])


def clamp_box(box):
    values = [float(v) for v in box]
    x0, y0, x1, y1 = values
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    return (x0, y0, x1, y1)


def overlaps_trim(box, minimum: float = 0.3) -> bool:
    """True when enough of the box lies inside the trim (fractions of the trim)."""

    x0, y0, x1, y1 = box
    ix0, iy0 = max(x0, 0.0), max(y0, 0.0)
    ix1, iy1 = min(x1, 1.0), min(y1, 1.0)
    if ix1 <= ix0 or iy1 <= iy0:
        return False
    area = max(1e-9, (x1 - x0) * (y1 - y0))
    return ((ix1 - ix0) * (iy1 - iy0)) / area >= minimum
