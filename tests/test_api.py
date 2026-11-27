import base64

from fastapi.testclient import TestClient

from template_compare.api import app
from tests.pdfs import build_stack, build_word


def test_compare_endpoint_returns_pdf_and_issues(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    template = tmp_path / "template.pdf"
    design = tmp_path / "design.pdf"
    build_word(template, "Sold")
    build_word(design, "Leased")
    client = TestClient(app)
    response = client.post(
        "/compare",
        files={
            "template": ("template.pdf", template.read_bytes(), "application/pdf"),
            "design": ("design.pdf", design.read_bytes(), "application/pdf"),
        },
        data={"mode": "markup", "use_ai": "false"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ai_used"] is False
    assert body["issues"]
    assert body["issues"][0]["measurements"]["text"]["design"] == "Leased"
    pdf = base64.b64decode(body["pdf_base64"])
    assert pdf.startswith(b"%PDF")


def test_compare_endpoint_page_mismatches(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    template = tmp_path / "template.pdf"
    design = tmp_path / "design.pdf"
    build_stack(template, 2, 595, 842, 0.2)
    build_stack(design, 1, 280, 360, 0.2)
    client = TestClient(app)
    response = client.post(
        "/compare",
        files={
            "template": ("wide.pdf", template.read_bytes(), "application/pdf"),
            "design": ("narrow.pdf", design.read_bytes(), "application/pdf"),
        },
        data={"mode": "side-by-side", "use_ai": "false", "model": "gemini-2.5-flash"},
    )
    assert response.status_code == 200, response.text
    kinds = {issue["kind"] for issue in response.json()["issues"]}
    assert "page_count" in kinds
    assert "page_size" in kinds


def test_health_and_bad_upload():
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    response = client.post(
        "/compare",
        files={
            "template": ("a.txt", b"hello", "text/plain"),
            "design": ("b.txt", b"%PDF-1.4", "application/pdf"),
        },
        data={"use_ai": "false"},
    )
    assert response.status_code == 400
