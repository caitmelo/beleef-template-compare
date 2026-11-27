"""Load ``original/comp.py`` by file path and re-export its functions.

The original file is not modified and is not imported as a script. ``render``,
``spans`` and ``bands`` are the functions from that file.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

_MODULE = None


def comp_path() -> Path:
    """Find ``original/comp.py`` next to the repo, or via the environment."""

    env = os.environ.get("TEMPLATE_COMPARE_ORIGINAL")
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env) / "comp.py")
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidates.append(parent / "original" / "comp.py")
    candidates.append(Path.cwd() / "original" / "comp.py")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "Could not find original/comp.py. Set TEMPLATE_COMPARE_ORIGINAL to the original directory."
    )


def original_comp():
    """Return the loaded original module. Loaded once."""

    global _MODULE
    if _MODULE is None:
        path = comp_path()
        spec = importlib.util.spec_from_file_location("template_compare_original_comp", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _MODULE = module
    return _MODULE


def render(path, page_index, trim, width=1000):
    """Rasterise a trim box. This is ``render`` in ``original/comp.py``."""

    return original_comp().render(str(path), page_index, trim, width)


def spans(path, page_index, trim):
    """Text spans in trim fractions. This is ``spans`` in ``original/comp.py``."""

    return original_comp().spans(str(path), page_index, trim)


def bands(image, minrow=1, thr=60, bg=None):
    """Ink rows. This is ``bands`` in ``original/comp.py``."""

    return original_comp().bands(image, minrow=minrow, thr=thr, bg=bg)
