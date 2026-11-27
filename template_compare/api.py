"""HTTP service. New code.

``POST /compare`` takes two PDF uploads and returns the marked up PDF together
with the issue list. Nothing is stored after the response is sent.
"""

from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from template_compare.ai import DEFAULT_MODEL
from template_compare.engine import compare
from template_compare.models import CompareError

app = FastAPI(title="Template compare", version="1.0.0")
_MAX_BYTES = 40 * 1024 * 1024


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/compare")
async def compare_pdfs(
    template: UploadFile = File(..., description="Approved template PDF"),
    design: UploadFile = File(..., description="New design PDF"),
    mode: str = Form("markup"),
    model: str = Form(DEFAULT_MODEL),
    use_ai: str = Form("auto"),
):
    """Compare two uploaded PDFs.

    ``mode`` is ``markup`` or ``side-by-side``. ``use_ai`` is ``auto``, ``true``,
    or ``false``. ``auto`` calls Gemini only when ``GEMINI_API_KEY`` is set.
    The response JSON contains ``issues`` and ``pdf_base64``.
    """

    flag = _parse_use_ai(use_ai)
    template_bytes = await _read(template, "template")
    design_bytes = await _read(design, "design")
    try:
        result = compare(
            template_bytes,
            design_bytes,
            mode=mode,
            use_ai=flag,
            model=model,
            template_name=template.filename or "template.pdf",
            design_name=design.filename or "design.pdf",
        )
    except CompareError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result.as_response()


def _parse_use_ai(value: str) -> bool | None:
    text = (value or "auto").strip().lower()
    if text in ("auto", ""):
        return None
    if text in ("true", "1", "yes"):
        return True
    if text in ("false", "0", "no"):
        return False
    raise HTTPException(status_code=400, detail="use_ai must be auto, true, or false")


async def _read(upload: UploadFile, label: str) -> bytes:
    data = await upload.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"The {label} PDF is larger than 40 MB.")
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail=f"The {label} file is not a PDF.")
    return data
