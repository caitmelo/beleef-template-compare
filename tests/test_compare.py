import pymupdf
import numpy as np

from template_compare import compare
from template_compare.cli import main
from template_compare.trim import detect_trim
from tests.pdfs import (
    build_clipped,
    build_harbor,
    build_ray_white,
    build_stack,
    build_trim_word,
    build_visible_prefix,
    build_word,
)


def _explain(issues):
    lines = []
    for issue in issues:
        lines.append(
            f"p{issue.get('page')} #{issue['number']} {issue['role']} {issue['kind']} {issue['kinds']} {issue['note']}"
        )
    return "\n".join(lines)


def _marks(pdf: bytes):
    document = pymupdf.open(stream=pdf, filetype="pdf")
    reds = blues = 0
    for page in document:
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1, 1), alpha=False)
        pixels = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.h, pixmap.w, 3)
        reds += int(((pixels[:, :, 0] > 180) & (pixels[:, :, 1] < 90) & (pixels[:, :, 2] < 90)).sum())
        blues += int(((pixels[:, :, 2] > 180) & (pixels[:, :, 0] < 90) & (pixels[:, :, 1] < 150)).sum())
    count = document.page_count
    document.close()
    return reds, blues, count


def _assert_plain(issues):
    for issue in issues:
        assert "—" not in issue["measured_note"]
        assert "–" not in issue["measured_note"]
        assert " - " not in issue["measured_note"]


def test_ray_white_landscape_finds_real_differences(tmp_path):
    template = tmp_path / "ray-white-template.pdf"
    design = tmp_path / "ray-white-design.pdf"
    build_ray_white(template, design=False)
    build_ray_white(design, design=True)
    result = compare(template, design, use_ai=False, template_name="ray-white-template.pdf", design_name="ray-white-design.pdf")
    issues = result.issues
    assert any(i["role"] == "heading" and "font_size" in i["kinds"] and "position" in i["kinds"] for i in issues), _explain(issues)
    assert any(i["role"] == "phone" and "colour" in i["kinds"] for i in issues), _explain(issues)
    assert any(i["kind"] == "missing" and i["role"] == "email" for i in issues), _explain(issues)
    assert any(i["kind"] == "extra" and "Auction 2pm" in i["note"] for i in issues), _explain(issues)
    assert any(i["role"] == "rule" and "size" in i["kinds"] for i in issues), _explain(issues)
    assert result.ai_used is False
    assert result.ai_reason == "disabled"
    _assert_plain(issues)
    _red, blue, pages = _marks(result.pdf)
    assert blue > 15, _marks(result.pdf)
    assert pages >= 2
    text = _pdf_text(result.pdf)
    assert "Blue dashed" in text
    assert "Ray White" in text


def test_harbor_portrait_finds_a_different_set_of_differences(tmp_path):
    template = tmp_path / "harbor-template.pdf"
    design = tmp_path / "harbor-design.pdf"
    build_harbor(template, design=False)
    build_harbor(design, design=True)
    result = compare(template, design, use_ai=False)
    issues = result.issues
    assert any(i["role"] == "heading" and "font" in i["kinds"] for i in issues), _explain(issues)
    assert any("Times" in i["note"] and "Helvetica" in i["note"] for i in issues), _explain(issues)
    assert any(i["role"] == "rule" and "size" in i["kinds"] for i in issues), _explain(issues)
    assert any(i["role"] == "text" and "colour" in i["kinds"] for i in issues), _explain(issues)
    assert any(i["role"] in ("mark", "image") and "position" in i["kinds"] for i in issues), _explain(issues)
    assert all("Ray White" not in i["note"] for i in issues)
    assert all("Auction 2pm" not in i["note"] for i in issues)
    _assert_plain(issues)
    _red, blue, _pages = _marks(result.pdf)
    assert blue > 15


def test_each_brand_matches_itself(tmp_path):
    for builder, name in ((build_ray_white, "ray"), (build_harbor, "harbor")):
        path = tmp_path / f"{name}.pdf"
        builder(path, design=False)
        result = compare(path, path, use_ai=False)
        assert result.issues == [], _explain(result.issues)


def test_page_count_mismatch_both_ways(tmp_path):
    long = tmp_path / "long.pdf"
    short = tmp_path / "short.pdf"
    build_stack(long, 2, 500, 640, 0.18)
    build_stack(short, 1, 500, 640, 0.18)
    fewer = compare(long, short, use_ai=False)
    count = next(issue for issue in fewer.issues if issue["kind"] == "page_count")
    assert count["measurements"]["template_pages"] == 2
    assert count["measurements"]["design_pages"] == 1
    assert count["measurements"]["missing_template_pages"] == [2]
    assert "2" in count["note"]
    assert not any(issue["kind"] in ("missing", "extra", "difference") for issue in fewer.issues), _explain(fewer.issues)

    more = compare(short, long, use_ai=False)
    count = next(issue for issue in more.issues if issue["kind"] == "page_count")
    assert count["measurements"]["extra_design_pages"] == [2]
    assert any(issue["kind"] == "extra_page" and issue["page"] == 2 for issue in more.issues)
    text = _pdf_text(more.pdf)
    assert "no template page" in text.lower() or "No template page" in text


def test_page_size_mismatch_is_reported_and_elements_still_compare(tmp_path):
    template = tmp_path / "a4.pdf"
    design = tmp_path / "small.pdf"
    build_stack(template, 1, 595, 842, 0.16, heading="North Office")
    build_stack(design, 1, 320, 480, 0.34, heading="North Office")
    result = compare(template, design, use_ai=False)
    size = next(issue for issue in result.issues if issue["kind"] == "page_size")
    assert size["measurements"]["template_width_pt"] == 595
    assert size["measurements"]["design_width_pt"] == 320
    assert any(issue["kind"] == "difference" and "position" in issue["kinds"] for issue in result.issues), _explain(result.issues)
    side = compare(template, design, mode="side-by-side", use_ai=False)
    assert side.pdf.startswith(b"%PDF")
    assert _marks(side.pdf)[2] >= 2


def test_page_count_and_page_size_together(tmp_path):
    template = tmp_path / "two-large.pdf"
    design = tmp_path / "one-small.pdf"
    build_stack(template, 2, 595, 842, 0.14, heading="North Office")
    build_stack(design, 1, 300, 400, 0.40, heading="North Office")
    result = compare(template, design, mode="side-by-side", use_ai=False)
    kinds = {issue["kind"] for issue in result.issues}
    assert "page_count" in kinds
    assert "page_size" in kinds
    assert any("position" in issue["kinds"] for issue in result.issues), _explain(result.issues)
    assert result.template_pages == 2
    assert result.design_pages == 1
    assert result.pages[0]["template_page"] == 1
    assert result.pages[0]["design_page"] == 1


def test_copy_change_on_an_unrelated_page(tmp_path):
    template = tmp_path / "sold.pdf"
    design = tmp_path / "leased.pdf"
    build_word(template, "Sold")
    build_word(design, "Leased")
    result = compare(template, design, use_ai=False)
    assert len(result.issues) == 1, _explain(result.issues)
    issue = result.issues[0]
    assert issue["kind"] == "difference"
    assert "text" in issue["kinds"]
    assert "Sold" in issue["note"] and "Leased" in issue["note"]


def test_trim_box_and_overflow(tmp_path):
    plain = pymupdf.open()
    page = plain.new_page(width=200, height=200)
    assert detect_trim(page) == (0.0, 0.0, 200.0, 200.0)
    plain.close()

    boxed = pymupdf.open()
    page = boxed.new_page(width=420, height=420)
    boxed.xref_set_key(page.xref, "TrimBox", "[30 30 390 390]")
    assert detect_trim(page) == (30.0, 30.0, 390.0, 390.0)
    boxed.close()

    template = tmp_path / "inside.pdf"
    design = tmp_path / "outside.pdf"
    build_trim_word(template, overflow=False)
    build_trim_word(design, overflow=True)
    result = compare(template, design, use_ai=False)
    assert any("overflow" in issue["kinds"] or "cutoff" in issue["kinds"] for issue in result.issues), _explain(result.issues)


def test_clipped_text_is_cut_off(tmp_path):
    template = tmp_path / "full.pdf"
    design = tmp_path / "clipped.pdf"
    build_visible_prefix(template)
    build_clipped(design)
    result = compare(template, design, use_ai=False)
    assert any("cutoff" in issue["kinds"] for issue in result.issues), _explain(result.issues)


def test_side_by_side_puts_template_label_on_the_left(tmp_path):
    template = tmp_path / "t.pdf"
    design = tmp_path / "d.pdf"
    build_word(template, "Sold")
    build_word(design, "Leased")
    result = compare(template, design, mode="side-by-side", use_ai=False)
    first = pymupdf.open(stream=result.pdf, filetype="pdf")[0]
    spans = [
        span
        for block in first.get_text("dict")["blocks"]
        for line in block.get("lines", [])
        for span in line["spans"]
    ]
    labels = [span for span in spans if abs(span["size"] - 9.5) < 0.2]
    template_x = min(span["bbox"][0] for span in labels if span["text"].startswith("Template"))
    design_x = min(span["bbox"][0] for span in labels if span["text"].startswith("Design"))
    assert template_x < design_x
    _red, blue, _pages = _marks(result.pdf)
    assert blue > 10


def test_cli_writes_pdf_and_issues(tmp_path):
    template = tmp_path / "t.pdf"
    design = tmp_path / "d.pdf"
    output = tmp_path / "out.pdf"
    issues = tmp_path / "issues.json"
    build_word(template, "Sold")
    build_word(design, "Leased")
    code = main([str(template), str(design), "-o", str(output), "--mode", "markup", "--no-ai", "--issues", str(issues)])
    assert code == 0
    assert output.read_bytes().startswith(b"%PDF")
    assert "Leased" in issues.read_text()


def test_image_only_pages_do_not_crash(tmp_path):
    def picture(path, color):
        document = pymupdf.open()
        page = document.new_page(width=300, height=300)
        from tests.pdfs import _png

        page.insert_image(pymupdf.Rect(40, 40, 260, 200), stream=_png((220, 160), color))
        document.save(path)
        document.close()

    template = tmp_path / "pic-a.pdf"
    design = tmp_path / "pic-b.pdf"
    picture(template, (10, 20, 30))
    picture(design, (200, 20, 20))
    result = compare(template, design, use_ai=False)
    assert result.pdf.startswith(b"%PDF")
    assert isinstance(result.issues, list)


def _pdf_text(pdf: bytes) -> str:
    document = pymupdf.open(stream=pdf, filetype="pdf")
    text = "\n".join(page.get_text() for page in document)
    document.close()
    return text
