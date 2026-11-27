"""Shared records for one comparison. All of this is new."""

from __future__ import annotations

from dataclasses import dataclass, field


class CompareError(Exception):
    """A caller-facing error: a bad file, an empty PDF, or a bad option."""


@dataclass
class Element:
    """One detected item, in fractions of that page's trim box."""

    kind: str
    role: str
    bbox: tuple[float, float, float, float]
    text: str | None = None
    font: str | None = None
    size: float | None = None
    color: str | None = None
    source: str = ""
    cutoff: bool = False
    overflow: bool = False
    hidden_text: str = ""
    origin_y: float | None = None

    @property
    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]

    @property
    def cx(self) -> float:
        return (self.bbox[0] + self.bbox[2]) / 2

    @property
    def cy(self) -> float:
        return (self.bbox[1] + self.bbox[3]) / 2

    @property
    def area(self) -> float:
        return max(0.0, self.width) * max(0.0, self.height)


@dataclass
class PagePair:
    """A design page and the template page it was paired with, if any."""

    design_page: int | None
    template_page: int | None
    design_index: int | None
    template_index: int | None
    design_trim: tuple[float, float, float, float] | None
    template_trim: tuple[float, float, float, float] | None
    issues: list[dict] = field(default_factory=list)


@dataclass
class CompareResult:
    pdf: bytes
    issues: list[dict]
    pages: list[dict]
    mode: str
    ai_used: bool
    ai_reason: str
    ai_notes_rewritten: int
    model: str | None
    template_name: str
    design_name: str
    template_pages: int
    design_pages: int

    def as_response(self) -> dict:
        import base64

        return {
            "mode": self.mode,
            "ai_used": self.ai_used,
            "ai_reason": self.ai_reason,
            "ai_notes_rewritten": self.ai_notes_rewritten,
            "model": self.model,
            "template_name": self.template_name,
            "design_name": self.design_name,
            "template_pages": self.template_pages,
            "design_pages": self.design_pages,
            "pages": self.pages,
            "issues": self.issues,
            "pdf_base64": base64.b64encode(self.pdf).decode("ascii"),
        }
