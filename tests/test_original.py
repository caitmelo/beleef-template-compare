import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "template_compare"
FORBIDDEN = re.compile(
    r"stone|zander|insaram|poppins|nimbus|pendle|signboard|6x4|6x2|for sale|for lease|beleef",
    re.IGNORECASE,
)


def test_original_files_match_sha256():
    lines = (ROOT / "original" / "SHA256SUMS.txt").read_text().splitlines()
    assert lines
    for line in lines:
        digest, recorded = line.split(None, 1)
        name = Path(recorded.strip()).name
        actual = hashlib.sha256((ROOT / "original" / name).read_bytes()).hexdigest()
        assert actual == digest


def test_package_uses_the_original_comp_functions():
    import inspect

    from template_compare.original_import import bands, comp_path, original_comp, render, spans

    path = comp_path()
    module = original_comp()
    assert path.name == "comp.py"
    assert path.parent.name == "original"
    assert Path(module.render.__code__.co_filename) == path
    assert Path(module.spans.__code__.co_filename) == path
    assert Path(module.bands.__code__.co_filename) == path
    assert module.render.__name__ == "render"
    assert "original_comp().render" in inspect.getsource(render)
    assert "original_comp().spans" in inspect.getsource(spans)
    assert "original_comp().bands" in inspect.getsource(bands)


def test_new_code_has_no_brand_specific_names():
    offenders = []
    for folder in (PACKAGE, ROOT / "tests"):
        for path in folder.rglob("*.py"):
            if path.name == "test_original.py":
                continue
            text = path.read_text()
            if FORBIDDEN.search(text):
                offenders.append(f"{path.relative_to(ROOT)}: {FORBIDDEN.search(text).group(0)}")
    dockerfile = (ROOT / "Dockerfile").read_text() if (ROOT / "Dockerfile").exists() else ""
    if FORBIDDEN.search(dockerfile):
        offenders.append("Dockerfile")
    assert offenders == []
