"""Detect the trim box of a PDF page. New code.

A file that does not declare a trim is compared on the full page rectangle.
"""

from __future__ import annotations

import pymupdf


def _has_box(page: pymupdf.Page, name: str) -> bool:
    kind, _value = page.parent.xref_get_key(page.xref, name)
    return kind == "array"


def detect_trim(page: pymupdf.Page) -> tuple[float, float, float, float]:
    """Return ``(x0, y0, x1, y1)`` in the same space as text and drawing boxes.

    Order: an explicit TrimBox, then ArtBox, then CropBox, otherwise the page
    rectangle. The result is intersected with the page rectangle.
    """

    if _has_box(page, "TrimBox"):
        chosen = page.trimbox
    elif _has_box(page, "ArtBox"):
        chosen = page.artbox
    elif _has_box(page, "CropBox"):
        chosen = page.cropbox
    else:
        chosen = page.rect
    frame = page.rect
    box = (
        max(float(chosen.x0), float(frame.x0)),
        max(float(chosen.y0), float(frame.y0)),
        min(float(chosen.x1), float(frame.x1)),
        min(float(chosen.y1), float(frame.y1)),
    )
    if box[2] - box[0] < 2 or box[3] - box[1] < 2:
        return (float(frame.x0), float(frame.y0), float(frame.x1), float(frame.y1))
    return box
