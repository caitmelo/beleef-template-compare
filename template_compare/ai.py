"""Optional Gemini step. New code.

The model does two things only. It rewrites a measured note into a shorter
sentence, and it looks at a small image region and says whether the artwork
looks different. It is not given a way to change the measurements. A rewrite
that adds a number, a colour, or a dash that was not already measured is
thrown away and the measured sentence is kept.

If ``GEMINI_API_KEY`` is unset, nothing here is called and the measured notes
are the notes.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

ALLOWED_MODELS = ("gemini-2.5-pro", "gemini-2.5-flash")
DEFAULT_MODEL = "gemini-2.5-pro"
_VISUAL_ROLES = {"image", "mark", "graphic"}
_DASHES = ("—", "–")


def resolve_ai(use_ai: bool | None) -> tuple[bool, str, str]:
    if use_ai is False:
        return False, "disabled", ""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        return False, "no_api_key", ""
    return True, "ok", key


def endpoint(model: str) -> str:
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def request_json(url: str, payload: dict, key: str, timeout: int = 40) -> dict:
    """POST to Gemini and parse the JSON object from the reply.

    The key is sent as a header, not in the URL.
    """

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    text = _response_text(body)
    return _load_json_object(text)


def apply_ai(pairs, visuals: list[dict], model: str, key: str) -> dict:
    """Rewrite notes and attach artwork comments. Returns a small status dict."""

    rewritten = 0
    reason = "ok"
    issues = [issue for pair in pairs for issue in pair.issues if issue["kind"] != "extra_page"]
    if issues:
        try:
            rewritten = _rewrite(issues, model, key)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, json.JSONDecodeError):
            reason = "request_failed"
    artwork = 0
    if reason != "request_failed" and visuals:
        try:
            artwork = _vision(pairs, visuals, model, key)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, json.JSONDecodeError):
            if reason == "ok":
                reason = "request_failed"
    for pair in pairs:
        _renumber_keep_notes(pair)
    used = rewritten > 0 or artwork > 0
    if not used and reason == "ok":
        reason = "nothing_accepted" if (issues or visuals) else "nothing_to_send"
    return {"used": used, "reason": reason, "rewritten": rewritten, "artwork": artwork}


def _rewrite(issues: list[dict], model: str, key: str) -> int:
    payload = {
        "contents": [{"role": "user", "parts": [{"text": _rewrite_prompt(issues)}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    parsed = request_json(endpoint(model), payload, key)
    by_key = {}
    for item in parsed.get("notes") or []:
        try:
            by_key[(int(item["page"]), int(item["number"]))] = str(item.get("note") or "")
        except (KeyError, TypeError, ValueError):
            continue
    accepted = 0
    for issue in issues:
        candidate = by_key.get((issue.get("page"), issue.get("number")))
        if not candidate:
            continue
        if _rewrite_ok(candidate, issue):
            issue["note"] = " ".join(candidate.split())
            accepted += 1
    return accepted


def _rewrite_prompt(issues: list[dict]) -> str:
    packed = [
        {
            "page": issue.get("page"),
            "number": issue.get("number"),
            "measured_note": issue["measured_note"],
            "measurements": issue["measurements"],
        }
        for issue in issues
    ]
    return (
        "Rewrite each measured note as one or two short plain sentences.\n"
        "Rules:\n"
        "Use only facts already in that item's measured note or measurements.\n"
        "Do not add a number, a colour, a font name, or an element.\n"
        "Do not use a hyphen, an en dash, or an em dash.\n"
        "Do not use bullet points.\n"
        "Return JSON of the form "
        '{"notes": [{"page": 1, "number": 1, "note": "short sentence"}]}.\n'
        "Items:\n"
        + json.dumps(packed, ensure_ascii=True)
    )


def _rewrite_ok(note: str, issue: dict) -> bool:
    if not note.strip() or len(note) > 700:
        return False
    if any(mark in note for mark in _DASHES):
        return False
    blob = json.dumps(issue["measurements"], ensure_ascii=True) + "\n" + issue["measured_note"]
    for token in re.findall(r"\S*-\S*", note):
        if token not in blob:
            return False
    allowed = _allowed_numbers(blob)
    for number in _numbers(note):
        if not any(abs(number - item) <= max(0.11, abs(item) * 0.02) for item in allowed):
            return False
    allowed_units = _allowed_unit_pairs(issue)
    for number, unit in _unit_pairs(note):
        if not any(unit == item_unit and abs(number - item) <= max(0.11, abs(item) * 0.02) for item, item_unit in allowed_units):
            return False
    for colour in re.findall(r"#[0-9A-Fa-f]{6}", note):
        if colour.upper() not in blob.upper():
            return False
    return True


def _vision(pairs, visuals: list[dict], model: str, key: str) -> int:
    added = 0
    for visual in visuals[:6]:
        if not visual.get("template_png") or not visual.get("design_png"):
            continue
        same, sentence = _look(visual, model, key)
        if same is not False:
            continue
        clean = _artwork_sentence(sentence)
        pair = _pair_for_page(pairs, visual["page"])
        if pair is None:
            continue
        host = _issue_for_box(pair.issues, visual["design_bbox"])
        if host is not None:
            if "artwork" not in host["kinds"]:
                host["kinds"].append("artwork")
            host["measurements"]["artwork"] = "different"
            if clean not in host["note"]:
                host["note"] = host["note"].rstrip() + " " + clean
            added += 1
            continue
        pair.issues.append(
            {
                "number": 0,
                "page": visual["page"],
                "role": visual["role"],
                "kind": "artwork",
                "kinds": ["artwork"],
                "note": clean,
                "measured_note": clean,
                "design_bbox": visual["design_bbox"],
                "template_bbox": visual["template_bbox"],
                "measurements": {"artwork": "different", "source": "image"},
            }
        )
        added += 1
    return added


def _look(visual: dict, model: str, key: str) -> tuple[bool | None, str]:
    import base64

    prompt = (
        "The first image is a graphic from a template. The second image is the graphic in the same role on a design. "
        "Say if the artwork looks the same or different. Mention only what you can see, such as a different shape or a different colour. "
        "Do not state a number, a size, a percent, or a position. Do not use a hyphen, an en dash, or an em dash. "
        'Reply as JSON {"same": true, "note": "short sentence"}.'
    )
    parts = [
        {"text": prompt},
        {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(visual["template_png"]).decode("ascii")}},
        {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(visual["design_png"]).decode("ascii")}},
    ]
    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    parsed = request_json(endpoint(model), payload, key)
    same = parsed.get("same")
    note = str(parsed.get("note") or "")
    if isinstance(same, str):
        same = same.strip().lower() == "true"
    if not isinstance(same, bool):
        return None, ""
    return same, note


def _artwork_sentence(note: str) -> str:
    fallback = "The artwork in this image region looks different from the template."
    cleaned = " ".join(note.split())
    if not cleaned or len(cleaned) > 280:
        return fallback
    if any(mark in cleaned for mark in _DASHES) or "-" in cleaned or re.search(r"\d", cleaned):
        return fallback
    if cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


def _pair_for_page(pairs, page):
    for pair in pairs:
        if pair.design_page == page:
            return pair
    return None


def _issue_for_box(issues, bbox) -> dict | None:
    from template_compare.geometry import box_iou

    best = None
    best_score = 0.35
    for issue in issues:
        if not issue.get("design_bbox"):
            continue
        score = box_iou(issue["design_bbox"], bbox)
        if score > best_score:
            best = issue
            best_score = score
    return best


def _renumber_keep_notes(pair) -> None:
    from template_compare.measure import renumber

    pair.issues = renumber(pair.issues, pair.design_page)


def _response_text(body: dict) -> str:
    candidates = body.get("candidates") or []
    if not candidates:
        raise ValueError("model returned no candidates")
    parts = ((candidates[0].get("content") or {}).get("parts")) or []
    return "".join(part.get("text", "") for part in parts)


def _load_json_object(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*", "", stripped).strip()
        stripped = stripped.removesuffix("```").strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end < start:
        raise ValueError("model reply was not JSON")
    parsed = json.loads(stripped[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("model reply was not a JSON object")
    return parsed


def _numbers(text: str) -> list[float]:
    return [float(item) for item in re.findall(r"\d+(?:\.\d+)?", text)]


def _allowed_numbers(blob: str) -> list[float]:
    found = _numbers(blob)
    extra = []
    for value in found:
        extra.append(float(round(value)))
        extra.append(round(value, 1))
    return found + extra


def _norm_unit(unit: str) -> str:
    text = unit.lower()
    if text == "%":
        return "percent"
    return text


def _unit_pairs(text: str) -> list[tuple[float, str]]:
    return [(float(number), _norm_unit(unit)) for number, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(mm|pt|percent|%)", text, re.I)]


def _allowed_unit_pairs(issue: dict) -> list[tuple[float, str]]:
    """Numbers that are already tied to mm, pt, or percent.

    A rewrite may repeat 17 mm. It may not take a 17 that was a point size
    and call it millimetres.
    """

    pairs = _unit_pairs(issue["measured_note"])

    def walk(value, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child in value.items():
                walk(child, str(child_key))
        elif isinstance(value, list):
            for child in value:
                walk(child, key)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            unit = _unit_from_key(key)
            if unit:
                pairs.append((float(value), unit))

    walk(issue["measurements"])
    return pairs


def _unit_from_key(key: str) -> str | None:
    lowered = key.lower()
    if lowered.endswith("_mm") or lowered == "mm":
        return "mm"
    if lowered.endswith("_pt") or lowered == "pt":
        return "pt"
    if "percent" in lowered:
        return "percent"
    return None
