"""Turn measured differences into short sentences. New code.

Sentences added here do not use a hyphen, en dash, or em dash as punctuation.
A measurement that is not in the numbers below is not mentioned.
"""

from __future__ import annotations

import re

_LABEL = {
    "heading": "Heading",
    "text": "Text",
    "phone": "Phone number",
    "email": "Email",
    "link": "Link",
    "rule": "Rule",
    "image": "Image",
    "mark": "Small image",
    "graphic": "Graphic",
    "region": "Ink region",
    "page": "Page",
    "document": "Document",
}


def label_for(role: str) -> str:
    return _LABEL.get(role, "Item")


def font_for_note(name: str | None) -> str:
    if not name:
        return ""
    cleaned = name.split("+")[-1]
    cleaned = cleaned.replace("-", " ").replace("_", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def percent_phrase(delta_percent: float, smaller: str, larger: str) -> str:
    amount = _number(abs(delta_percent))
    word = smaller if delta_percent < 0 else larger
    return f"{amount} percent {word}"


def _number(value: float) -> str:
    absolute = abs(value)
    if absolute >= 10:
        return str(int(round(absolute)))
    rounded = round(absolute, 1)
    if float(rounded).is_integer():
        return str(int(rounded))
    return f"{rounded:.1f}"


def mm_phrase(mm: float) -> str:
    return f"{_number(mm)} mm"


def difference_note(role: str, kinds: list[str], measurements: dict, cutoff: bool, overflow: bool) -> str:
    sentences: list[str] = []
    text = measurements.get("text")
    if text:
        sentences.append(f'Text reads "{text["design"]}" and the template reads "{text["template"]}".')
    font = measurements.get("font")
    if font:
        sentences.append(f'Font is {font["design"]} and the template uses {font["template"]}.')
    font_size = measurements.get("font_size")
    if font_size:
        sentences.append(
            "Font size is "
            f'{_number(font_size["design_pt"])} pt and the template is {_number(font_size["template_pt"])} pt, '
            f'so the design is {percent_phrase(font_size["delta_percent"], "smaller", "larger")}.'
        )
    position = measurements.get("position")
    if position:
        bits = []
        if position.get("dy_frac") is not None:
            direction = "lower" if position["dy_frac"] > 0 else "higher"
            bits.append(
                f'{mm_phrase(abs(position["design_dy_mm"]))} {direction} on the design page '
                f'({_number(abs(position["dy_frac"]) * 100)} percent of page height)'
            )
        if position.get("dx_frac") is not None:
            direction = "to the right" if position["dx_frac"] > 0 else "to the left"
            bits.append(
                f'{mm_phrase(abs(position["design_dx_mm"]))} {direction} on the design page '
                f'({_number(abs(position["dx_frac"]) * 100)} percent of page width)'
            )
        if bits:
            sentences.append("It sits " + " and ".join(bits) + ".")
    size = measurements.get("size")
    if size:
        bits = []
        if size.get("width_percent") is not None:
            bits.append(
                f'{percent_phrase(size["width_percent"], "narrower", "wider")} '
                f'({_number(size["design_width_pt"])} pt against {_number(size["template_width_pt"])} pt)'
            )
        if size.get("height_percent") is not None:
            bits.append(
                f'{percent_phrase(size["height_percent"], "shorter", "taller")} '
                f'({_number(size["design_height_pt"])} pt against {_number(size["template_height_pt"])} pt)'
            )
        if bits:
            sentences.append("It is " + " and ".join(bits) + " than the template.")
    colour = measurements.get("colour")
    if colour:
        sentences.append(f'Colour is {colour["design"]} and the template is {colour["template"]}.')
    if cutoff:
        hidden = measurements.get("hidden_text") or ""
        if hidden:
            sentences.append(f'The text is cut off. Hidden characters continue as "{hidden}".')
        else:
            sentences.append("The text is cut off.")
    if overflow:
        sentences.append("The text runs outside the trim.")
    if not sentences:
        sentences.append("This element differs from the template.")
    return label_for(role) + ". " + " ".join(sentences)


def missing_note(role: str, text: str | None) -> str:
    name = label_for(role).lower()
    if text:
        return f'Missing {name}. The template has "{text}" and the design does not.'
    return f"Missing {name}. The template has this and the design does not."


def extra_note(role: str, text: str | None) -> str:
    name = label_for(role).lower()
    if text:
        return f'Extra {name}. The design has "{text}" and the template does not.'
    return f"Extra {name}. The design has this and the template does not."


def page_size_note(measurements: dict) -> str:
    return (
        "Page size differs. "
        f'Design trim is {_number(measurements["design_width_pt"])} by {_number(measurements["design_height_pt"])} pt '
        f'({_number(measurements["design_width_mm"])} by {_number(measurements["design_height_mm"])} mm). '
        f'Template trim is {_number(measurements["template_width_pt"])} by {_number(measurements["template_height_pt"])} pt '
        f'({_number(measurements["template_width_mm"])} by {_number(measurements["template_height_mm"])} mm).'
    )


def page_count_note(measurements: dict) -> str:
    missing = measurements.get("missing_template_pages") or []
    extra = measurements.get("extra_design_pages") or []
    sentence = (
        "Page count differs. "
        f'The design has {measurements["design_pages"]} page'
        f'{"s" if measurements["design_pages"] != 1 else ""} and the template has '
        f'{measurements["template_pages"]} page'
        f'{"s" if measurements["template_pages"] != 1 else ""}. '
        "Pages are paired in order."
    )
    sentence += _unpaired("Template", "design", missing)
    sentence += _unpaired("Design", "template", extra)
    return sentence


def _unpaired(owner: str, other: str, numbers: list) -> str:
    if not numbers:
        return ""
    listed = ", ".join(str(number) for number in numbers)
    word = "page" if len(numbers) == 1 else "pages"
    verb = "has" if len(numbers) == 1 else "have"
    return f" {owner} {word} {listed} {verb} no {other} page."


def extra_page_note() -> str:
    return "This design page has no template page. Pages are paired in order, and this page is past the end of the template."
