"""Measure matched elements. New code.

Every number in an issue comes from the PDF boxes, fonts, or colours. Thresholds
below are the only filter: smaller differences are left out so render noise is
not reported as a change.
"""

from __future__ import annotations

import re

from template_compare.geometry import channel_delta, pt_to_mm
from template_compare.models import Element
from template_compare.notes import (
    difference_note,
    extra_note,
    extra_page_note,
    font_for_note,
    missing_note,
    page_count_note,
    page_size_note,
)

# Fraction of trim. 0.008 is 0.8 percent of that side.
POSITION_FRAC = 0.008
# Relative change in width or height.
SIZE_FRAC = 0.04
# Absolute font size change, in points.
FONT_SIZE_PT = 0.4
# Max channel change, 0 to 255, before two colours count as different.
COLOUR_CHANNEL = 12
# Relative trim width or height change.
PAGE_SIZE_FRAC = 0.01


def build_page_issues(pairs, missing, extra, design_trim, template_trim) -> list[dict]:
    issues = []
    if design_trim and template_trim:
        size_issue = page_size_issue(design_trim, template_trim)
        if size_issue:
            issues.append(size_issue)
    for template, design, _score in pairs:
        issue = measure_match(template, design, design_trim, template_trim)
        if issue:
            issues.append(issue)
    for element in missing:
        issues.append(_unmatched("missing", element, template_side=True))
    for element in extra:
        issues.append(_unmatched("extra", element, template_side=False))
    return _sort_and_number(issues, page=None)


def measure_match(template: Element, design: Element, design_trim, template_trim) -> dict | None:
    kinds: list[str] = []
    measurements: dict = {
        "source": {"design": design.source, "template": template.source},
        "role": {"design": design.role, "template": template.role},
    }
    if design.text or template.text:
        measurements["text_raw"] = {"design": design.text, "template": template.text}
    if design.text and template.text and _norm(design.text) != _norm(template.text):
        kinds.append("text")
        measurements["text"] = {"design": design.text, "template": template.text}
    font = _font_diff(template, design)
    if font:
        kinds.append("font")
        measurements["font"] = font
    font_size = _font_size_diff(template, design)
    if font_size:
        kinds.append("font_size")
        measurements["font_size"] = font_size
    position = _position_diff(template, design, design_trim, template_trim)
    if position:
        kinds.append("position")
        measurements["position"] = position
    # Text height follows the font size, which is measured in points. Width is
    # compared in points so a smaller page does not by itself make the text "wider".
    size = _size_diff(
        template,
        design,
        design_trim,
        template_trim,
        report_height=design.kind != "text",
    )
    if size:
        kinds.append("size")
        measurements["size"] = size
    colour = _colour_diff(template, design)
    if colour:
        kinds.append("colour")
        measurements["colour"] = colour
    if design.cutoff:
        kinds.append("cutoff")
        if design.hidden_text:
            measurements["hidden_text"] = design.hidden_text
    if design.overflow:
        kinds.append("overflow")
    if not kinds:
        return None
    role = design.role if design.role == template.role else design.role
    note = difference_note(role, kinds, measurements, design.cutoff, design.overflow)
    return _issue(
        role=role,
        kind="difference",
        kinds=kinds,
        note=note,
        design_bbox=design.bbox,
        template_bbox=template.bbox,
        measurements=measurements,
    )


def page_size_issue(design_trim, template_trim) -> dict | None:
    dw = design_trim[2] - design_trim[0]
    dh = design_trim[3] - design_trim[1]
    tw = template_trim[2] - template_trim[0]
    th = template_trim[3] - template_trim[1]
    if tw <= 0 or th <= 0:
        return None
    if abs(dw - tw) / tw < PAGE_SIZE_FRAC and abs(dh - th) / th < PAGE_SIZE_FRAC:
        return None
    measurements = {
        "design_width_pt": round(dw, 2),
        "design_height_pt": round(dh, 2),
        "template_width_pt": round(tw, 2),
        "template_height_pt": round(th, 2),
        "design_width_mm": round(pt_to_mm(dw), 2),
        "design_height_mm": round(pt_to_mm(dh), 2),
        "template_width_mm": round(pt_to_mm(tw), 2),
        "template_height_mm": round(pt_to_mm(th), 2),
    }
    note = page_size_note(measurements)
    return _issue("page", "page_size", ["page_size"], note, None, None, measurements)


def page_count_issue(template_pages: int, design_pages: int) -> dict | None:
    if template_pages == design_pages:
        return None
    missing = list(range(design_pages + 1, template_pages + 1))
    extra = list(range(template_pages + 1, design_pages + 1))
    measurements = {
        "template_pages": template_pages,
        "design_pages": design_pages,
        "missing_template_pages": missing,
        "extra_design_pages": extra,
    }
    note = page_count_note(measurements)
    return _issue("document", "page_count", ["page_count"], note, None, None, measurements)


def extra_page_issue() -> dict:
    note = extra_page_note()
    return _issue("document", "extra_page", ["extra_page"], note, None, None, {})


def _unmatched(kind: str, element: Element, template_side: bool) -> dict:
    kinds = [kind]
    measurements = {
        "source": element.source,
        "role": element.role,
        "text": element.text,
        "font": element.font,
        "size_pt": element.size,
        "colour": element.color,
    }
    if element.cutoff:
        kinds.append("cutoff")
        if element.hidden_text:
            measurements["hidden_text"] = element.hidden_text
    if element.overflow:
        kinds.append("overflow")
    if kind == "missing":
        note = missing_note(element.role, element.text)
        if element.overflow:
            note += " The template text runs outside the trim."
        return _issue(
            element.role,
            kind,
            kinds,
            note,
            None,
            element.bbox,
            measurements,
        )
    note = extra_note(element.role, element.text)
    if element.cutoff:
        note += " The text is cut off."
    if element.overflow:
        note += " The text runs outside the trim."
    return _issue(element.role, kind, kinds, note, element.bbox, None, measurements)


def _position_diff(template: Element, design: Element, design_trim, template_trim) -> dict | None:
    dx = design.cx - template.cx
    dy = design.cy - template.cy
    record = {}
    if abs(dx) >= POSITION_FRAC:
        record["dx_frac"] = round(dx, 4)
        record["design_dx_mm"] = round(dx * pt_to_mm(design_trim[2] - design_trim[0]), 2)
        record["template_dx_mm"] = round(dx * pt_to_mm(template_trim[2] - template_trim[0]), 2)
    if abs(dy) >= POSITION_FRAC:
        record["dy_frac"] = round(dy, 4)
        record["design_dy_mm"] = round(dy * pt_to_mm(design_trim[3] - design_trim[1]), 2)
        record["template_dy_mm"] = round(dy * pt_to_mm(template_trim[3] - template_trim[1]), 2)
    return record or None


def _size_diff(template: Element, design: Element, design_trim, template_trim, report_height: bool) -> dict | None:
    """Compare sizes in points, not only as a fraction of unlike pages."""

    record = {}
    design_width = design.width * (design_trim[2] - design_trim[0])
    template_width = template.width * (template_trim[2] - template_trim[0])
    if template_width > 4:
        width_percent = (design_width - template_width) / template_width * 100
        if abs(width_percent) >= SIZE_FRAC * 100:
            record["width_percent"] = round(width_percent, 2)
            record["design_width_pt"] = round(design_width, 2)
            record["template_width_pt"] = round(template_width, 2)
    if report_height:
        design_height = design.height * (design_trim[3] - design_trim[1])
        template_height = template.height * (template_trim[3] - template_trim[1])
        if template_height > 1.5:
            height_percent = (design_height - template_height) / template_height * 100
            if abs(height_percent) >= SIZE_FRAC * 100:
                record["height_percent"] = round(height_percent, 2)
                record["design_height_pt"] = round(design_height, 2)
                record["template_height_pt"] = round(template_height, 2)
    return record or None


def _font_diff(template: Element, design: Element) -> dict | None:
    if not template.font or not design.font:
        return None
    if _norm_font(template.font) == _norm_font(design.font):
        return None
    return {"design": font_for_note(design.font), "template": font_for_note(template.font), "design_raw": design.font, "template_raw": template.font}


def _font_size_diff(template: Element, design: Element) -> dict | None:
    if not template.size or not design.size:
        return None
    if abs(design.size - template.size) < FONT_SIZE_PT:
        return None
    delta = (design.size - template.size) / template.size * 100
    return {
        "design_pt": round(design.size, 2),
        "template_pt": round(template.size, 2),
        "delta_percent": round(delta, 2),
    }


def _colour_diff(template: Element, design: Element) -> dict | None:
    if not template.color or not design.color:
        return None
    delta = channel_delta(template.color, design.color)
    if delta is None or delta < COLOUR_CHANNEL:
        return None
    return {"design": design.color.upper(), "template": template.color.upper(), "max_channel_delta": delta}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _norm_font(name: str) -> str:
    base = name.split("+")[-1]
    return re.sub(r"[^a-z0-9]", "", base.lower())


def _issue(role, kind, kinds, note, design_bbox, template_bbox, measurements) -> dict:
    return {
        "number": 0,
        "page": None,
        "role": role,
        "kind": kind,
        "kinds": list(kinds),
        "note": note,
        "measured_note": note,
        "design_bbox": _box(design_bbox),
        "template_bbox": _box(template_bbox),
        "measurements": _plain(measurements),
    }


def _box(box):
    if box is None:
        return None
    return [round(float(value), 4) for value in box]


def _plain(value):
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, (int, str, bool)) or value is None:
        return value
    return str(value)


def _sort_and_number(issues: list[dict], page: int | None) -> list[dict]:
    def key(issue: dict):
        if issue["kind"] == "page_count":
            return (-2, 0, 0)
        if issue["kind"] == "page_size":
            return (-1, 0, 0)
        box = issue["design_bbox"] or issue["template_bbox"] or [0, 0, 0, 0]
        return (box[1], box[0], 0)

    ordered = sorted(issues, key=key)
    for number, issue in enumerate(ordered, start=1):
        issue["number"] = number
        if page is not None:
            issue["page"] = page
    return ordered


def renumber(issues: list[dict], page: int | None) -> list[dict]:
    return _sort_and_number(issues, page)
