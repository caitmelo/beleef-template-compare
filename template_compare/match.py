"""Pair design elements with template elements. New code.

Matching uses role, text, and position. It is a heuristic: a layout that was
rearranged can pair the wrong items, or report a move as a missing item plus
an extra item.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from template_compare.models import Element

_TEXT_ROLES = {"heading", "text", "phone", "email", "link"}
_VISUAL_ROLES = {"image", "mark", "graphic", "region"}
_ACCEPT = 0.50


def match_elements(template: list[Element], design: list[Element]):
    """Return ``(pairs, missing, extra)``.

    ``pairs`` is a list of ``(template_element, design_element, score)``.
    ``missing`` are template elements with no design partner.
    ``extra`` are design elements with no template partner.
    """

    scored = []
    for t_index, template_element in enumerate(template):
        for d_index, design_element in enumerate(design):
            score = _score(template_element, design_element)
            if score >= _ACCEPT:
                scored.append((score, t_index, d_index))
    scored.sort(key=lambda item: item[0], reverse=True)
    used_t: set[int] = set()
    used_d: set[int] = set()
    pairs = []
    for score, t_index, d_index in scored:
        if t_index in used_t or d_index in used_d:
            continue
        used_t.add(t_index)
        used_d.add(d_index)
        pairs.append((template[t_index], design[d_index], score))
    missing = [element for index, element in enumerate(template) if index not in used_t]
    extra = [element for index, element in enumerate(design) if index not in used_d]
    return pairs, missing, extra


def _compatible(template: Element, design: Element) -> bool:
    if template.role == design.role:
        return True
    if template.role in _TEXT_ROLES and design.role in _TEXT_ROLES:
        return True
    if template.role in _VISUAL_ROLES and design.role in _VISUAL_ROLES:
        return True
    if "rule" in (template.role, design.role) and (
        "region" in (template.role, design.role) or template.role == design.role
    ):
        return True
    return False


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _score(template: Element, design: Element) -> float:
    if not _compatible(template, design):
        return -1.0
    dx = template.cx - design.cx
    dy = template.cy - design.cy
    distance = (dx * dx + dy * dy) ** 0.5
    position = max(0.0, 1.0 - distance / 0.55)
    left = template.text or ""
    right = design.text or ""
    if left and right:
        similarity = SequenceMatcher(None, _norm(left), _norm(right)).ratio()
    elif not left and not right:
        similarity = 0.55
    else:
        similarity = 0.2
    if left and right and similarity < 0.2 and template.role != design.role:
        return -1.0
    if similarity >= 0.92:
        position = max(position, 0.75)
    if distance > 0.55 and similarity < 0.85:
        return -1.0
    width_score = _ratio(template.width, design.width)
    role_score = 1.0 if template.role == design.role else 0.45
    return 0.44 * position + 0.28 * similarity + 0.16 * role_score + 0.12 * width_score


def _ratio(left: float, right: float) -> float:
    if left <= 0 or right <= 0:
        return 0.5
    return min(left, right) / max(left, right)
