"""Command line. New code.

    compare template.pdf design.pdf -o out.pdf --mode markup|side-by-side
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from template_compare.ai import ALLOWED_MODELS, DEFAULT_MODEL
from template_compare.engine import compare
from template_compare.models import CompareError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compare",
        description="Compare a design PDF with a template PDF and write a marked up PDF.",
    )
    parser.add_argument("template", help="Approved template PDF")
    parser.add_argument("design", help="New design PDF")
    parser.add_argument("-o", "--output", required=True, help="Where to write the marked up PDF")
    parser.add_argument("--mode", choices=["markup", "side-by-side"], default="markup")
    parser.add_argument("--model", choices=list(ALLOWED_MODELS), default=DEFAULT_MODEL)
    parser.add_argument("--no-ai", action="store_true", help="Do not call Gemini, even if a key is set")
    parser.add_argument("--issues", help="Also write the issue list as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = compare(
            args.template,
            args.design,
            mode=args.mode,
            use_ai=False if args.no_ai else None,
            model=args.model,
            template_name=Path(args.template).name,
            design_name=Path(args.design).name,
        )
    except CompareError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    Path(args.output).write_bytes(result.pdf)
    if args.issues:
        Path(args.issues).write_text(json.dumps({"issues": result.issues, "pages": result.pages}, indent=2))
    print(f"Wrote {args.output} with {len(result.issues)} issue(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
