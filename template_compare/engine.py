"""Run a comparison. New code.

This wires trim detection, element detection, matching, and measurement to the
original drawing. The optional model step runs after the measurements exist and
cannot replace them.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import pymupdf

from template_compare.ai import ALLOWED_MODELS, DEFAULT_MODEL, apply_ai, resolve_ai
from template_compare.draw import render_pdf
from template_compare.elements import detect_page
from template_compare.match import match_elements
from template_compare.measure import build_page_issues, extra_page_issue, page_count_issue, renumber
from template_compare.models import CompareError, CompareResult, PagePair
from template_compare.original_import import render

_VISUAL = {"image", "mark", "graphic"}
_MAX_BYTES = 40 * 1024 * 1024


def compare(
    template,
    design,
    *,
    mode: str = "markup",
    use_ai: bool | None = None,
    model: str = DEFAULT_MODEL,
    template_name: str = "template.pdf",
    design_name: str = "design.pdf",
) -> CompareResult:
    """Compare ``design`` with ``template``.

    Each argument is a filesystem path or raw PDF bytes. ``mode`` is ``markup``
    or ``side-by-side``.
    """

    if mode not in ("markup", "side-by-side"):
        raise CompareError("mode must be markup or side-by-side")
    if model not in ALLOWED_MODELS:
        raise CompareError("model must be gemini-2.5-pro or gemini-2.5-flash")
    template_name = _safe_name(template_name)
    design_name = _safe_name(design_name)
    with tempfile.TemporaryDirectory(prefix="template-compare-") as temporary:
        template_path = _materialize(template, Path(temporary) / "template.pdf")
        design_path = _materialize(design, Path(temporary) / "design.pdf")
        template_doc = _open(template_path, "template")
        design_doc = _open(design_path, "design")
        try:
            template_count = template_doc.page_count
            design_count = design_doc.page_count
        finally:
            template_doc.close()
            design_doc.close()
        if template_count < 1 or design_count < 1:
            raise CompareError("Each PDF needs at least one page.")
        pairs, visuals = _collect(template_path, design_path, template_count, design_count)
        enabled, reason, key = resolve_ai(use_ai)
        rewritten = 0
        used_model = None
        if enabled:
            if visuals:
                _fill_crops(visuals, template_path, design_path)
            status = apply_ai(pairs, visuals, model, key)
            used_model = model if status["used"] else None
            reason = status["reason"]
            rewritten = status["rewritten"]
            enabled = status["used"]
        meta = {
            "template_path": str(template_path),
            "design_path": str(design_path),
            "template_name": template_name,
            "design_name": design_name,
            "template_pages": template_count,
            "design_pages": design_count,
        }
        pdf = render_pdf(pairs, meta, mode)
        issues = [issue for pair in pairs for issue in pair.issues]
        pages = [_page_record(pair) for pair in pairs]
        return CompareResult(
            pdf=pdf,
            issues=issues,
            pages=pages,
            mode=mode,
            ai_used=enabled,
            ai_reason=reason,
            ai_notes_rewritten=rewritten,
            model=used_model,
            template_name=template_name,
            design_name=design_name,
            template_pages=template_count,
            design_pages=design_count,
        )


def _collect(template_path, design_path, template_count: int, design_count: int):
    pairs: list[PagePair] = []
    visuals: list[dict] = []
    shared = min(template_count, design_count)
    for index in range(shared):
        template_trim, template_elements = detect_page(template_path, index)
        design_trim, design_elements = detect_page(design_path, index)
        matched, missing, extra = match_elements(template_elements, design_elements)
        issues = build_page_issues(matched, missing, extra, design_trim, template_trim)
        pair = PagePair(
            design_page=index + 1,
            template_page=index + 1,
            design_index=index,
            template_index=index,
            design_trim=design_trim,
            template_trim=template_trim,
            issues=issues,
        )
        pairs.append(pair)
        for template_element, design_element, _score in matched:
            if template_element.role not in _VISUAL and design_element.role not in _VISUAL:
                continue
            if template_element.area >= 0.25 or design_element.area >= 0.25:
                continue
            visuals.append(
                {
                    "page": index + 1,
                    "role": design_element.role,
                    "design_bbox": [round(float(value), 4) for value in design_element.bbox],
                    "template_bbox": [round(float(value), 4) for value in template_element.bbox],
                    "design_index": index,
                    "template_index": index,
                    "design_trim": design_trim,
                    "template_trim": template_trim,
                    "template_png": None,
                    "design_png": None,
                }
            )
    for index in range(shared, design_count):
        design_trim, _elements = detect_page(design_path, index)
        pairs.append(
            PagePair(
                design_page=index + 1,
                template_page=None,
                design_index=index,
                template_index=None,
                design_trim=design_trim,
                template_trim=None,
                issues=[extra_page_issue()],
            )
        )
    count_issue = page_count_issue(template_count, design_count)
    if count_issue and pairs:
        pairs[0].issues.append(count_issue)
    for pair in pairs:
        pair.issues = renumber(pair.issues, pair.design_page)
    visuals = sorted(visuals, key=lambda item: item["role"] != "mark")[:6]
    return pairs, visuals


def _fill_crops(visuals, template_path, design_path) -> None:
    for visual in visuals:
        visual["template_png"] = _crop(
            template_path, visual["template_index"], visual["template_trim"], visual["template_bbox"]
        )
        visual["design_png"] = _crop(
            design_path, visual["design_index"], visual["design_trim"], visual["design_bbox"]
        )


def _crop(path, page_index, trim, bbox) -> bytes | None:
    """Crop a trim render. The raster comes from ``render`` in ``original/comp.py``."""

    from PIL import Image

    image = render(path, page_index, trim, 700)
    height, width, _channels = image.shape
    x0 = max(0, min(width - 1, int(bbox[0] * width)))
    y0 = max(0, min(height - 1, int(bbox[1] * height)))
    x1 = max(x0 + 1, min(width, int(bbox[2] * width) + 1))
    y1 = max(y0 + 1, min(height, int(bbox[3] * height) + 1))
    if x1 - x0 < 4 or y1 - y0 < 4:
        return None
    picture = Image.fromarray(image[y0:y1, x0:x1])
    picture.thumbnail((256, 256))
    buffer = io.BytesIO()
    picture.save(buffer, format="PNG")
    return buffer.getvalue()


def _page_record(pair: PagePair) -> dict:
    record = {
        "design_page": pair.design_page,
        "template_page": pair.template_page,
    }
    if pair.design_trim:
        record["design_width_pt"] = round(pair.design_trim[2] - pair.design_trim[0], 2)
        record["design_height_pt"] = round(pair.design_trim[3] - pair.design_trim[1], 2)
    if pair.template_trim:
        record["template_width_pt"] = round(pair.template_trim[2] - pair.template_trim[0], 2)
        record["template_height_pt"] = round(pair.template_trim[3] - pair.template_trim[1], 2)
    return record


def _open(path: Path, label: str):
    try:
        document = pymupdf.open(path)
    except Exception as exc:
        raise CompareError(f"Could not open the {label} PDF.") from exc
    if document.is_encrypted and document.needs_pass:
        document.close()
        raise CompareError(f"The {label} PDF is password protected.")
    return document


def _materialize(source, destination: Path) -> Path:
    if isinstance(source, (bytes, bytearray)):
        if len(source) > _MAX_BYTES:
            raise CompareError("A PDF is larger than 40 MB.")
        destination.write_bytes(source)
        return destination
    path = Path(source)
    if not path.is_file():
        raise CompareError(f"File not found: {path.name}")
    if path.stat().st_size > _MAX_BYTES:
        raise CompareError("A PDF is larger than 40 MB.")
    return path


def _safe_name(name: str) -> str:
    base = Path(name or "file.pdf").name
    cleaned = base.encode("latin-1", "replace").decode("latin-1")
    return cleaned[:120] or "file.pdf"
