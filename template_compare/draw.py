"""Draw the marked up PDF. New wiring around two original drawers.

``draw_markup`` follows ``build`` in ``original/markup2.py``: the design page,
red boxes, blue dashed boxes, red number circles, a notes panel, and a summary.

``draw_side_by_side`` follows ``draw_pair`` in ``original/v3.py``: template on
the left, design on the right, at the same scale, with the same box colours.

The summary page follows the ``line`` helper at the bottom of
``original/markup2.py`` (the same idea is repeated in ``original/v3.py``).
"""

from __future__ import annotations

import io

import pymupdf

from template_compare.geometry import rect_from_fraction

RED = (0.86, 0.1, 0.1)
BLUE = (0.1, 0.35, 0.95)
GREY = (0.97, 0.97, 0.97)


def render_pdf(pairs, meta: dict, mode: str) -> bytes:
    document = pymupdf.open()
    try:
        if mode == "side-by-side":
            for pair in pairs:
                _draw_side_by_side(document, pair, meta)
        else:
            for pair in pairs:
                _draw_markup(document, pair, meta)
        _draw_summary(document, pairs, meta)
        buffer = io.BytesIO()
        document.save(buffer, garbage=3, deflate=True)
        return buffer.getvalue()
    finally:
        document.close()


def _pdf_text(value: str) -> str:
    return value.encode("latin-1", "replace").decode("latin-1")


def _draw_markup(document, pair, meta: dict) -> None:
    """One markup page.

    Adapted from ``build`` in ``original/markup2.py``. The original saved a
    fixed path and read hand written boxes. This version draws one detected
    page onto an open document. The notes panel grows when the notes need it.
    """

    if pair.design_index is None:
        return
    source = pymupdf.open(meta["design_path"])
    try:
        src = source[pair.design_index]
        width, height = src.rect.width, src.rect.height
        landscape = width > height
        # Font scale adapted from build() in original/markup2.py.
        font = min(width, height) / (28 if landscape else (42 if width / height > 0.5 else 24))
        note_size = font * 0.62
        issues = pair.issues
        title = f"Design page {pair.design_page}"
        compared = f"Compared with template: {meta['template_name']}"
        if pair.template_page is None:
            compared = "No template page was paired with this design page."
        legend = "Red box = design element with the issue. Blue dashed box = where the template puts it."
        note_width = (width - 2 * font) if landscape else (width * 0.8 - 2 * font)
        note_width = max(note_width, 120)
        needed = note_size * 6
        needed += _text_height(title, "hebo", note_size * 1.25, note_width)
        needed += _text_height(compared, "heit", note_size * 0.9, note_width)
        needed += _text_height(legend, "heit", note_size * 0.85, note_width)
        for issue in issues:
            needed += _text_height(issue["note"], "helv", note_size, note_width - note_size * 1.5) + note_size * 0.4
        if landscape:
            out_w, out_h = width, height + max(height * 0.45, needed + font)
            panel = pymupdf.Rect(font, height + font, width - font, out_h - font / 2)
        else:
            out_w = width * 1.8
            out_h = max(height, needed + 2 * font)
            panel = pymupdf.Rect(width + font, font, out_w - font, out_h - font)
        page = document.new_page(width=out_w, height=out_h)
        page.show_pdf_page(pymupdf.Rect(0, 0, width, height), source, pair.design_index)
        if landscape:
            page.draw_rect(pymupdf.Rect(0, height, out_w, out_h), color=None, fill=GREY)
        else:
            page.draw_rect(pymupdf.Rect(width, 0, out_w, out_h), color=None, fill=GREY)
        trim = pair.design_trim or (0, 0, width, height)
        line_width = font * 0.15
        for issue in issues:
            reds = [issue["design_bbox"]] if issue.get("design_bbox") else []
            blues = [issue["template_bbox"]] if issue.get("template_bbox") else []
            for box in blues:
                page.draw_rect(
                    _clamped(rect_from_fraction(trim, _padded(box, 0.003)), pymupdf.Rect(0, 0, width, height)),
                    color=BLUE,
                    width=line_width,
                    dashes=f"[{font * 0.5} {font * 0.35}] 0",
                )
            for box in reds:
                page.draw_rect(
                    _clamped(rect_from_fraction(trim, _padded(box, 0.003)), pymupdf.Rect(0, 0, width, height)),
                    color=RED,
                    width=line_width * 1.3,
                )
            if reds or blues:
                anchor = rect_from_fraction(trim, (reds or blues)[0])
                center = pymupdf.Point(
                    min(anchor.x1 + font * 0.9, width - font * 0.9),
                    max(anchor.y0 + font * 0.3, font * 0.9),
                )
                number = str(issue["number"])
                page.draw_circle(center, font * 0.75, color=RED, fill=RED)
                page.insert_text(
                    pymupdf.Point(center.x - font * 0.28 * len(number), center.y + font * 0.35),
                    number,
                    fontsize=font * 0.95,
                    color=(1, 1, 1),
                    fontname="hebo",
                )
        cursor = panel.y0 + note_size * 0.3

        def paragraph(text, fontname="helv", color=(0, 0, 0), size=note_size, indent=0):
            nonlocal cursor
            safe = _pdf_text(text)
            block_width = panel.x1 - panel.x0 - indent
            height_needed = _text_height(safe, fontname, size, block_width)
            page.insert_textbox(
                pymupdf.Rect(panel.x0 + indent, cursor, panel.x1, cursor + height_needed + size),
                safe,
                fontsize=size,
                fontname=fontname,
                color=color,
            )
            cursor += height_needed

        paragraph(title, "hebo", (0, 0, 0), note_size * 1.25)
        paragraph(compared, "heit", (0.2, 0.2, 0.2), note_size * 0.9)
        paragraph(legend, "heit", BLUE, note_size * 0.85)
        for issue in issues:
            number = str(issue["number"])
            page.draw_circle(pymupdf.Point(panel.x0 + note_size * 0.55, cursor + note_size * 0.55), note_size * 0.55, color=RED, fill=RED)
            page.insert_text(
                pymupdf.Point(panel.x0 + note_size * 0.55 - note_size * 0.2 * len(number), cursor + note_size * 0.85),
                number,
                fontsize=note_size * 0.75,
                color=(1, 1, 1),
                fontname="hebo",
            )
            paragraph(issue["note"], indent=note_size * 1.5)
    finally:
        source.close()


def _draw_side_by_side(document, pair, meta: dict) -> None:
    """One side by side page.

    Adapted from ``draw_pair`` in ``original/v3.py``. The original compared two
    fixed files at one scale and wrote labels for those files. This version
    places the template on the left and the design on the right, and it uses
    the detected trim of each page. Both panels use the same scale.
    """

    design_trim = pair.design_trim
    template_trim = pair.template_trim
    if design_trim is None:
        return
    d_rect = pymupdf.Rect(*design_trim)
    t_rect = pymupdf.Rect(*template_trim) if template_trim else d_rect
    scale = 720 / max(t_rect.height, d_rect.height, 1)
    t_w, t_h = t_rect.width * scale, t_rect.height * scale
    d_w, d_h = d_rect.width * scale, d_rect.height * scale
    widest = max(t_w, d_w)
    if widest > 980:
        scale *= 980 / widest
        t_w, t_h = t_rect.width * scale, t_rect.height * scale
        d_w, d_h = d_rect.width * scale, d_rect.height * scale
    margin = 28
    notes_w = 420
    header = 78
    note_size = 9.6
    notes_height = 36 + sum(_text_height(issue["note"], "helv", note_size, notes_w - 24) + 8 for issue in pair.issues)
    panel_h = max(t_h, d_h)
    out_h = header + max(panel_h, notes_height) + 28
    out_w = margin + t_w + margin + d_w + margin + notes_w + margin
    page = document.new_page(width=out_w, height=out_h)
    title = f"Design page {pair.design_page}"
    page.insert_text((margin, 34), _pdf_text(title), fontsize=17, fontname="hebo")
    subtitle = "Same scale. Each page is cropped to its trim. Template on the left, design on the right."
    page.insert_text((margin, 52), _pdf_text(subtitle), fontsize=9, fontname="helv", color=(0.25, 0.25, 0.25))
    y0 = 70
    left = pymupdf.Rect(margin, y0, margin + t_w, y0 + t_h)
    right = pymupdf.Rect(margin + t_w + margin, y0, margin + t_w + margin + d_w, y0 + d_h)
    if pair.template_index is not None and template_trim is not None:
        template = pymupdf.open(meta["template_path"])
        try:
            page.show_pdf_page(left, template, pair.template_index, clip=pymupdf.Rect(*template_trim))
        finally:
            template.close()
    else:
        page.draw_rect(left, color=None, fill=GREY)
        page.insert_text((left.x0 + 12, left.y0 + 24), "No template page", fontsize=12, fontname="hebo", color=BLUE)
    design = pymupdf.open(meta["design_path"])
    try:
        page.show_pdf_page(right, design, pair.design_index, clip=pymupdf.Rect(*design_trim))
    finally:
        design.close()
    page.draw_rect(left, color=(0.5, 0.5, 0.5), width=0.6)
    page.draw_rect(right, color=(0.5, 0.5, 0.5), width=0.6)
    template_label = "Template"
    if pair.template_page:
        template_label += f" page {pair.template_page}"
    page.insert_text((left.x0, y0 - 8), template_label, fontsize=9.5, fontname="hebo", color=BLUE)
    page.insert_text((right.x0, y0 - 8), f"Design page {pair.design_page}", fontsize=9.5, fontname="hebo", color=RED)
    notes_x = right.x1 + margin
    page.insert_text((notes_x, y0 - 8), "Differences", fontsize=9.5, fontname="hebo")
    legend = "Red box = design element with the issue. Blue dashed box = where the template puts it."
    page.insert_text((notes_x, y0 + 12), legend, fontsize=7.5, fontname="heit", color=BLUE)
    cursor = y0 + 28
    dash = "[4 3] 0"
    for issue in pair.issues:
        number = str(issue["number"])
        if issue.get("template_bbox") and pair.template_index is not None:
            template_box = _panel_rect(left, issue["template_bbox"])
            page.draw_rect(template_box, color=BLUE, width=1.0, dashes=dash)
            page.insert_text((template_box.x0 - 1, template_box.y0 - 3), number, fontsize=8.5, fontname="hebo", color=BLUE)
            page.draw_rect(_panel_rect(right, issue["template_bbox"]), color=BLUE, width=1.0, dashes=dash)
        if issue.get("design_bbox"):
            design_box = _panel_rect(right, issue["design_bbox"])
            page.draw_rect(design_box, color=RED, width=1.5)
            center = pymupdf.Point(min(design_box.x1 + 9, right.x1 - 9), max(design_box.y0 + 4, right.y0 + 9))
            page.draw_circle(center, 8, color=RED, fill=RED)
            page.insert_text(
                pymupdf.Point(center.x - 2.8 * len(number), center.y + 3.4),
                number,
                fontsize=9,
                fontname="hebo",
                color=(1, 1, 1),
            )
        block_h = _text_height(issue["note"], "helv", note_size, notes_w - 24)
        page.draw_circle(pymupdf.Point(notes_x + 7, cursor + 7), 7, color=RED, fill=RED)
        page.insert_text(
            pymupdf.Point(notes_x + 7 - 2.6 * len(number), cursor + 10),
            number,
            fontsize=8.5,
            fontname="hebo",
            color=(1, 1, 1),
        )
        page.insert_textbox(
            pymupdf.Rect(notes_x + 20, cursor + 1, notes_x + notes_w, cursor + block_h + 14),
            _pdf_text(issue["note"]),
            fontsize=note_size,
            fontname="helv",
        )
        cursor += block_h + 6


def _draw_summary(document, pairs, meta: dict) -> None:
    """Summary page.

    Adapted from the ``line`` helper in ``original/markup2.py``.
    """

    page = document.new_page(width=595, height=842)
    state = {"page": page, "y": 48}

    def line(text, size=9, fontname="helv", gap=3, width=515):
        safe = _pdf_text(text)
        block = _text_height(safe, fontname, size, width) + gap
        if state["y"] + block > 800:
            state["page"] = document.new_page(width=595, height=842)
            state["y"] = 48
        state["page"].insert_textbox(
            pymupdf.Rect(40, state["y"], 40 + width, state["y"] + block + 8),
            safe,
            fontsize=size,
            fontname=fontname,
        )
        state["y"] += block

    line("Template comparison", 16, "hebo", 8)
    line(f"Template file: {meta['template_name']}", 9, "heit", 2)
    line(f"Design file: {meta['design_name']}", 9, "heit", 2)
    line(
        f"Template pages: {meta['template_pages']}. Design pages: {meta['design_pages']}. "
        "Pages are paired in order.",
        9,
        "helv",
        4,
    )
    line(
        "Red box = design element with the issue. Blue dashed box = where the template puts it.",
        8,
        "heit",
        6,
    )
    for pair in pairs:
        if pair.design_page is None:
            continue
        bits = [f"Design page {pair.design_page}"]
        if pair.template_page:
            bits.append(f"paired with template page {pair.template_page}")
        else:
            bits.append("with no template page")
        if pair.design_trim:
            bits.append(_size_phrase("Design trim", pair.design_trim))
        if pair.template_trim:
            bits.append(_size_phrase("Template trim", pair.template_trim))
        line(". ".join(bits) + ".", 8, "heit", 3)
    issues = [issue for pair in pairs for issue in pair.issues]
    if not issues:
        line("No differences found.", 12, "hebo", 6)
        return
    line("Notes", 12, "hebo", 4)
    for issue in issues:
        page_bit = f"Page {issue['page']}. " if issue.get("page") else ""
        line(f"{page_bit}{issue['number']}. {issue['note']}", 8.5, "helv", 2)


def _size_phrase(name: str, trim) -> str:
    width = trim[2] - trim[0]
    height = trim[3] - trim[1]
    return f"{name} {width:.0f} by {height:.0f} pt"


def _text_height(text: str, fontname: str, size: float, width: float) -> float:
    safe = _pdf_text(text)
    if width <= 1:
        width = 1
    lines = max(1, int(pymupdf.get_text_length(safe, fontname, size) / (width * 0.93)) + 1)
    return lines * size * 1.25 + size * 0.35


def _padded(box, pad: float):
    return [box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad]


def _clamped(rect: pymupdf.Rect, frame: pymupdf.Rect) -> pymupdf.Rect:
    return pymupdf.Rect(
        max(rect.x0, frame.x0),
        max(rect.y0, frame.y0),
        min(rect.x1, frame.x1),
        min(rect.y1, frame.y1),
    )


def _panel_rect(panel: pymupdf.Rect, box, pad: float = 0.004) -> pymupdf.Rect:
    """Map a trim fraction onto a side by side panel.

    Adapted from the inner ``R`` in ``draw_pair`` in ``original/v3.py``.
    """

    return pymupdf.Rect(
        panel.x0 + (box[0] - pad) * panel.width,
        panel.y0 + (box[1] - pad) * panel.height,
        panel.x0 + (box[2] + pad) * panel.width,
        panel.y0 + (box[3] + pad) * panel.height,
    )
