"""Detect elements on one page of any PDF. New, except where a comment says otherwise.

Roles are generic (heading, text, phone number, email, link, rule, image,
small image, graphic, ink region). Nothing here is tied to a brand or a product.
"""

from __future__ import annotations

import re
import statistics

import pymupdf

from template_compare.geometry import (
    box_iou,
    center_inside,
    clamp_box,
    expand,
    fraction_box,
    hex_from_rgb,
    near,
    overlaps_trim,
    union,
)
from template_compare.models import Element
from template_compare.original_import import bands, render, spans
from template_compare.trim import detect_trim

_PHONE = re.compile(r"^[+().\d\s-]+$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_LINK = re.compile(r"(?i)^(https?://|www\.)\S+$|^\S+\.(com|net|org|au|nz|uk|co)(\.[a-z]{2})?$")

# Ink threshold used by bands() in original/comp.py. The row split below uses the same value.
_INK_THRESHOLD = 60


def detect_page(path, page_index: int) -> tuple[tuple[float, float, float, float], list[Element]]:
    """Return the trim box and the elements on one page."""

    document = pymupdf.open(path)
    try:
        page = document[page_index]
        trim = detect_trim(page)
        text = _text_elements(path, page, page_index, trim)
        images = _image_elements(page, trim)
        drawings = _drawing_elements(page, trim)
        drawings = _drop_drawings_on_text(drawings, text)
        elements = text + images + drawings
        elements.extend(_ink_elements(path, page_index, trim, elements))
        elements = [element for element in elements if _on_trim(element)]
        elements.sort(key=lambda element: (element.bbox[1], element.bbox[0]))
        return trim, elements
    finally:
        document.close()


def _text_elements(path, page, page_index: int, trim) -> list[Element]:
    raw = spans(path, page_index, trim)
    lines = _group_spans(raw)
    if not lines:
        return []
    sizes = [max(span["size"] for span in line) for line in lines]
    median = statistics.median(sizes) if sizes else 0
    elements: list[Element] = []
    for line in lines:
        line = sorted(line, key=lambda span: span["x0"])
        chunks = _split_gaps(line)
        for chunk in chunks:
            element = _element_from_spans(chunk, median)
            if element is not None:
                elements.append(element)
    elements = _merge_body_lines(elements)
    _apply_cutoff(page, trim, elements)
    return elements


def _group_spans(raw) -> list[list[dict]]:
    ordered = sorted(raw, key=lambda span: (round(span["origy"], 3), span["x0"]))
    lines: list[list[dict]] = []
    for span in ordered:
        placed = False
        for line in lines:
            anchor = line[0]
            tolerance = max(0.008, (span.get("sizeH") or 0) / 100 * 0.45)
            if abs(span["origy"] - anchor["origy"]) <= tolerance:
                line.append(span)
                placed = True
                break
        if not placed:
            lines.append([span])
    return lines


def _split_gaps(line: list[dict]) -> list[list[dict]]:
    chunks = [[line[0]]]
    for previous, current in zip(line, line[1:]):
        if current["x0"] - previous["x1"] > 0.04:
            chunks.append([current])
        else:
            chunks[-1].append(current)
    return chunks


def _element_from_spans(chunk: list[dict], median: float) -> Element | None:
    text = " ".join(span["t"].strip() for span in chunk if span["t"].strip()).strip()
    if not text:
        return None
    longest = max(chunk, key=lambda span: len(span["t"]))
    bbox = union([clamp_box((span["x0"], span["y0"], span["x1"], span["y1"])) for span in chunk])
    size = float(longest["size"])
    return Element(
        kind="text",
        role=_role_for_text(text, size, median),
        bbox=bbox,
        text=text,
        font=str(longest["font"]),
        size=size,
        color=str(longest["col"]).upper(),
        source="spans",
        origin_y=float(longest["origy"]),
    )


def _role_for_text(text: str, size: float, median: float) -> str:
    compact = re.sub(r"\s+", "", text)
    digit_count = sum(character.isdigit() for character in text)
    if digit_count >= 8 and _PHONE.fullmatch(text) and digit_count / max(len(compact), 1) > 0.6:
        return "phone"
    if _EMAIL.fullmatch(text):
        return "email"
    if _LINK.fullmatch(text):
        return "link"
    if median and size >= max(16.0, median * 1.45):
        return "heading"
    return "text"


def _merge_body_lines(elements: list[Element]) -> list[Element]:
    others = [element for element in elements if not (element.kind == "text" and element.role == "text")]
    lines = [element for element in elements if element.kind == "text" and element.role == "text"]
    lines.sort(key=lambda element: (element.bbox[1], element.bbox[0]))
    merged: list[Element] = []
    index = 0
    while index < len(lines):
        block = [lines[index]]
        cursor = index + 1
        while cursor < len(lines):
            previous = block[-1]
            nxt = lines[cursor]
            if not _same_text_run(previous, nxt):
                break
            gap = nxt.bbox[1] - previous.bbox[3]
            line_height = max(previous.height, 0.008)
            if gap > line_height * 0.9:
                break
            block.append(nxt)
            cursor += 1
        merged.append(_union_text(block))
        index = cursor
    return others + merged


def _same_text_run(left: Element, right: Element) -> bool:
    if left.font != right.font or left.color != right.color:
        return False
    if left.size and right.size and abs(left.size - right.size) > 0.6:
        return False
    if abs(left.bbox[0] - right.bbox[0]) > 0.03:
        return False
    return True


def _union_text(block: list[Element]) -> Element:
    if len(block) == 1:
        return block[0]
    first = block[0]
    return Element(
        kind="text",
        role="text",
        bbox=union([element.bbox for element in block]),
        text=" ".join(element.text or "" for element in block).strip(),
        font=first.font,
        size=max(element.size or 0 for element in block),
        color=first.color,
        source="spans",
        origin_y=first.origin_y,
        cutoff=any(element.cutoff for element in block),
        overflow=any(element.overflow for element in block),
        hidden_text="".join(element.hidden_text for element in block),
    )


def _apply_cutoff(page, trim, elements: list[Element]) -> None:
    """Mark text that runs outside the trim, or that continues past a clip.

    Visible text comes from ``spans`` (which uses ``get_text``). Glyphs that
    ``get_texttrace`` still returns, but that sit just past the visible line,
    are treated as cut off. This check is new.
    """

    width = trim[2] - trim[0]
    height = trim[3] - trim[1]
    text = [element for element in elements if element.kind == "text"]
    boxes = {id(element): _point_box(element, trim, width, height) for element in text}
    for element in text:
        points = boxes[id(element)]
        past = max(0.0, trim[0] - points[0], trim[1] - points[1], points[2] - trim[2], points[3] - trim[3])
        if past > 2:
            element.overflow = True
    glyphs = _trace_glyphs(page)
    hidden_for: dict[int, list[str]] = {id(element): [] for element in text}
    for glyph in glyphs:
        if _glyph_inside_text(glyph, boxes):
            owner = _owner_element(glyph, text, boxes)
            if owner is not None and _glyph_crosses_trim(glyph["bbox"], trim):
                owner.cutoff = True
            continue
        owner = _continuation_owner(glyph, text, boxes)
        if owner is not None:
            hidden_for[id(owner)].append(glyph["c"])
    for element in text:
        hidden = "".join(hidden_for[id(element)])[:80]
        if hidden:
            element.cutoff = True
            element.hidden_text = hidden


def _point_box(element: Element, trim, width: float, height: float):
    return (
        trim[0] + element.bbox[0] * width,
        trim[1] + element.bbox[1] * height,
        trim[0] + element.bbox[2] * width,
        trim[1] + element.bbox[3] * height,
    )


def _glyph_inside_text(glyph, boxes) -> bool:
    x, y = glyph["origin"]
    for points in boxes.values():
        if points[0] - 2 <= x <= points[2] + 2 and points[1] - 4 <= y <= points[3] + 4:
            return True
    return False


def _owner_element(glyph, elements, boxes):
    x, y = glyph["origin"]
    for element in elements:
        points = boxes[id(element)]
        if points[0] - 2 <= x <= points[2] + 2 and points[1] - 4 <= y <= points[3] + 4:
            return element
    return None


def _continuation_owner(glyph, elements, boxes):
    """The visible line just to the left of a glyph that no line contains."""

    x, y = glyph["origin"]
    best = None
    best_edge = None
    for element in elements:
        points = boxes[id(element)]
        if not (points[1] - 6 <= y <= points[3] + 6):
            continue
        if x + 2 < points[2]:
            continue
        if best_edge is None or points[2] > best_edge:
            best = element
            best_edge = points[2]
    return best


def _glyph_crosses_trim(bbox, trim) -> bool:
    past = max(0.0, trim[0] - bbox[0], trim[1] - bbox[1], bbox[2] - trim[2], bbox[3] - trim[3])
    inside = bbox[2] > trim[0] + 1 and bbox[0] < trim[2] - 1 and bbox[3] > trim[1] + 1 and bbox[1] < trim[3] - 1
    return past > 1 and inside


def _trace_glyphs(page) -> list[dict]:
    glyphs = []
    try:
        traces = page.get_texttrace()
    except Exception:
        return glyphs
    for trace in traces:
        for char in trace.get("chars") or []:
            parsed = _parse_glyph(char)
            if parsed is not None and parsed["c"].strip():
                glyphs.append(parsed)
    return glyphs


def _parse_glyph(char) -> dict | None:
    if isinstance(char, dict):
        text = char.get("c") or ""
        origin = char.get("origin")
        bbox = char.get("bbox")
    elif isinstance(char, (tuple, list)) and len(char) >= 4:
        code = char[0]
        text = chr(code) if isinstance(code, int) else str(code)
        origin = char[2]
        bbox = char[3]
    else:
        return None
    if not origin or not bbox:
        return None
    return {"c": text, "origin": (float(origin[0]), float(origin[1])), "bbox": tuple(float(v) for v in bbox[:4])}


def _image_elements(page, trim) -> list[Element]:
    """Image blocks.

    The loop follows the image loop in ``show`` in ``original/comp.py``.
    Roles and the full-page skip are new.
    """

    elements = []
    for image in page.get_image_info():
        bbox = clamp_box(fraction_box(pymupdf.Rect(*image["bbox"]), trim))
        if bbox[2] - bbox[0] >= 0.92 and bbox[3] - bbox[1] >= 0.92:
            continue
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        if height <= 0 or width <= 0:
            continue
        aspect = width / height
        role = "mark" if max(width, height) <= 0.22 and 0.7 <= aspect <= 1.45 else "image"
        elements.append(Element(kind="image", role=role, bbox=bbox, source="image"))
    return elements


def _drawing_elements(page, trim) -> list[Element]:
    """Drawn shapes.

    Filtering of tiny empty paths follows ``show`` in ``original/comp.py``.
    Grouping the rest into rules and graphics is new.
    """

    rules = []
    others = []
    for drawing in page.get_drawings():
        rect = drawing["rect"]
        if rect.width * rect.height < 4 and drawing.get("width", 0) in (None, 0):
            continue
        bbox = clamp_box(fraction_box(rect, trim))
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        if width >= 0.9 and height >= 0.9:
            continue
        if width <= 0 or height <= 0:
            continue
        color = hex_from_rgb(drawing.get("fill")) or hex_from_rgb(drawing.get("color"))
        element = Element(kind="drawing", role="graphic", bbox=bbox, color=color, source="drawing")
        if _is_rule(width, height):
            element.role = "rule"
            rules.append(element)
        elif element.area >= 0.0003:
            others.append(element)
    return rules + _cluster_graphics(others)


def _is_rule(width: float, height: float) -> bool:
    if height <= 0.035 and width >= 0.08 and height < width * 0.3:
        return True
    if width <= 0.035 and height >= 0.08 and width < height * 0.3:
        return True
    return False


def _cluster_graphics(elements: list[Element]) -> list[Element]:
    if not elements:
        return []
    parent = list(range(len(elements)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def unite(left: int, right: int) -> None:
        a, b = find(left), find(right)
        if a != b:
            parent[b] = a

    for left in range(len(elements)):
        for right in range(left + 1, len(elements)):
            if near(elements[left].bbox, elements[right].bbox, 0.012):
                unite(left, right)
    groups: dict[int, list[Element]] = {}
    for index, element in enumerate(elements):
        groups.setdefault(find(index), []).append(element)
    clustered = []
    for group in groups.values():
        if len(group) == 1:
            element = group[0]
            width, height = element.width, element.height
            if height > 0 and max(width, height) <= 0.18 and 0.7 <= (width / height) <= 1.45:
                element.role = "mark"
            clustered.append(element)
            continue
        clustered.append(
            Element(
                kind="drawing",
                role="graphic",
                bbox=union([element.bbox for element in group]),
                color=next((element.color for element in group if element.color), None),
                source="drawing",
            )
        )
    return clustered


def _drop_drawings_on_text(drawings: list[Element], text: list[Element]) -> list[Element]:
    kept = []
    for drawing in drawings:
        if drawing.role == "rule":
            kept.append(drawing)
            continue
        covered = False
        for item in text:
            if center_inside(drawing.bbox, expand(item.bbox, 0.005)) and drawing.area < item.area * 1.4:
                covered = True
                break
        if not covered:
            kept.append(drawing)
    return kept


def _ink_elements(path, page_index: int, trim, existing: list[Element]) -> list[Element]:
    """Ink regions that are not already a text, image, or drawing element.

    Row ranges come from ``bands`` in ``original/comp.py``. Splitting a row
    where a vertical gap appears is new, so side by side items are not forced
    into one band.
    """

    try:
        image = render(path, page_index, trim, 900)
    except Exception:
        return []
    height, width, _channels = image.shape
    if height < 16 or width < 80:
        return []
    try:
        background, rows = bands(image, thr=_INK_THRESHOLD)
    except Exception:
        return []
    import numpy as np

    mask = (np.abs(image.astype(int) - np.array(background)).sum(2) > _INK_THRESHOLD)
    found: list[Element] = []
    for y0, y1, x0, x1, color in rows:
        # Same minimum row height as pb() in original/comp.py and bnds() in original/v3.py.
        if y1 - y0 <= 0.002:
            continue
        for box, ink_color in _split_row(mask, width, height, y0, y1, x0, x1, color):
            role = "rule" if _is_rule(box[2] - box[0], box[3] - box[1]) else "region"
            if role != "rule" and (box[2] - box[0]) * (box[3] - box[1]) < 0.004:
                continue
            if (box[2] - box[0]) >= 0.9 and (box[3] - box[1]) >= 0.7:
                continue
            element = Element(
                kind="ink",
                role=role,
                bbox=box,
                color=ink_color,
                source="bands",
            )
            if _explained(element, existing):
                continue
            found.append(element)
    return found


def _split_row(mask, width, height, y0, y1, x0, x1, color):
    row0 = max(0, min(height - 1, int(y0 * height)))
    row1 = max(row0 + 1, min(height, int(y1 * height)))
    col0 = max(0, min(width - 1, int(x0 * width)))
    col1 = max(col0 + 1, min(width, int(x1 * width)))
    sub = mask[row0:row1, col0:col1]
    if sub.size == 0:
        return []
    columns = sub.any(0)
    min_gap = max(3, int(0.015 * width))
    closed = columns.copy()
    index = 0
    count = len(closed)
    while index < count:
        if closed[index]:
            index += 1
            continue
        end = index
        while end < count and not closed[end]:
            end += 1
        if index > 0 and end < count and (end - index) < min_gap:
            closed[index:end] = True
        index = end
    boxes = []
    index = 0
    while index < count:
        if not closed[index]:
            index += 1
            continue
        end = index
        while end < count and closed[end]:
            end += 1
        boxes.append(
            (
                (
                    (col0 + index) / width,
                    y0,
                    (col0 + end) / width,
                    y1,
                ),
                "#{:02X}{:02X}{:02X}".format(*(int(v) for v in color)),
            )
        )
        index = end
    return boxes


def _explained(element: Element, existing: list[Element]) -> bool:
    text_hits = 0
    for other in existing:
        if box_iou(element.bbox, other.bbox) >= 0.2 or center_inside(element.bbox, expand(other.bbox, 0.012)):
            return True
        if other.kind == "text" and center_inside(other.bbox, expand(element.bbox, 0.005)):
            text_hits += 1
    return text_hits >= 2


def _on_trim(element: Element) -> bool:
    if element.cutoff or element.overflow:
        return overlaps_trim(element.bbox, minimum=0.05)
    return overlaps_trim(element.bbox)
