import json

from template_compare import compare
from template_compare.ai import _rewrite_ok, apply_ai, endpoint
from template_compare.models import PagePair
from tests.pdfs import build_ray_white, build_word


def test_model_names():
    assert endpoint("gemini-2.5-pro").endswith("/models/gemini-2.5-pro:generateContent")
    assert endpoint("gemini-2.5-flash").endswith("/models/gemini-2.5-flash:generateContent")


def test_rewrite_rejects_invented_numbers_and_dashes():
    issue = {
        "measured_note": "Heading. Font size is 22 pt and the template is 32 pt, so the design is 31 percent smaller.",
        "measurements": {"font_size": {"design_pt": 22, "template_pt": 32, "delta_percent": -31.25}},
    }
    assert _rewrite_ok("Heading font size is 22 pt against the template 32 pt.", issue)
    assert not _rewrite_ok("Heading font size is 99 pt.", issue)
    assert not _rewrite_ok("The heading is lower — by a lot.", issue)
    assert not _rewrite_ok("The heading is 22 pt and sits 40 mm lower.", issue)
    assert not _rewrite_ok("The heading moved 22 mm.", issue)


def test_no_key_skips_the_model(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    template = tmp_path / "t.pdf"
    design = tmp_path / "d.pdf"
    build_word(template, "Sold")
    build_word(design, "Leased")
    result = compare(template, design)
    assert result.ai_used is False
    assert result.ai_reason == "no_api_key"
    assert result.issues[0]["note"] == result.issues[0]["measured_note"]
    assert "Sold" in result.issues[0]["measurements"]["text"]["template"]


def test_rewrite_and_vision_do_not_invent_measurements(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    template = tmp_path / "t.pdf"
    design = tmp_path / "d.pdf"
    build_ray_white(template, design=False)
    build_ray_white(design, design=True)

    def fake_request(url, payload, key, timeout=40):
        assert key == "test-key"
        assert "gemini-2.5-flash" in url
        text = payload["contents"][0]["parts"][0]["text"]
        if text.startswith("Rewrite"):
            items = json.loads(text.split("Items:\n", 1)[1])
            notes = []
            for item in items:
                if item["number"] == 1:
                    notes.append({"page": item["page"], "number": 1, "note": "Invented shift of 99 mm."})
                else:
                    notes.append(
                        {
                            "page": item["page"],
                            "number": item["number"],
                            "note": "This item differs from the template.",
                        }
                    )
            return {"notes": notes}
        return {"same": False, "note": "The shapes look different and one is 12 mm wider."}

    monkeypatch.setattr("template_compare.ai.request_json", fake_request)
    result = compare(template, design, model="gemini-2.5-flash")
    assert result.ai_notes_rewritten >= 1
    assert not any("99 mm" in issue["note"] or issue["note"].startswith("Invented") for issue in result.issues)
    # The rejected rewrite keeps the measured sentence, including its real numbers.
    kept = [issue for issue in result.issues if issue["note"] == issue["measured_note"] and issue["kind"] == "difference"]
    assert kept
    artwork = [issue for issue in result.issues if "artwork" in issue["kinds"] or issue["kind"] == "artwork"]
    assert artwork, _dump(result.issues)
    for issue in artwork:
        assert "12" not in issue["note"]
        assert "mm" not in issue["note"].split("artwork")[-1]


def _dump(issues):
    return "\n".join(f"{issue['kind']} {issue['kinds']} {issue['note']}" for issue in issues)


def test_apply_ai_reports_disabled_reason_without_calling(monkeypatch):
    pair = PagePair(1, 1, 0, 0, (0, 0, 10, 10), (0, 0, 10, 10), issues=[])
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from template_compare.ai import resolve_ai

    enabled, reason, key = resolve_ai(False)
    assert enabled is False and reason == "disabled" and key == ""
    enabled, reason, key = resolve_ai(None)
    assert reason == "no_api_key"
    # apply_ai itself is only called when a key exists; a failed request keeps measured notes.
    pair.issues.append(
        {
            "number": 1,
            "page": 1,
            "role": "text",
            "kind": "difference",
            "kinds": ["text"],
            "note": "Text reads \"B\" and the template reads \"A\".",
            "measured_note": "Text reads \"B\" and the template reads \"A\".",
            "design_bbox": [0, 0, 1, 1],
            "template_bbox": [0, 0, 1, 1],
            "measurements": {"text": {"design": "B", "template": "A"}},
        }
    )

    def boom(*_args, **_kwargs):
        raise TimeoutError("slow")

    monkeypatch.setattr("template_compare.ai.request_json", boom)
    status = apply_ai([pair], [], "gemini-2.5-pro", "key")
    assert status["used"] is False
    assert status["reason"] == "request_failed"
    assert pair.issues[0]["note"] == pair.issues[0]["measured_note"]
