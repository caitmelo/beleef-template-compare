# Template compare

Compares a design PDF with an approved template PDF and writes a marked up PDF: red numbered boxes on the design, blue dashed boxes where the template puts each item, numbered notes, and a summary page.

This is the engine behind that check. It is not tied to one agency, one product, or one page size. Any two PDFs can be uploaded.

## What is original, and what is new

`original/` is the exact scripts used to mark up the Stone signboards, brochures, and mailcards. Do not edit those files. `original/SHA256SUMS.txt` is the checksum list. Those scripts hardcode file paths, trim boxes, and per product element lists. In `markup2.py` the issue boxes were partly typed in by hand. They are kept so the old runs can be reproduced. They are not the general engine.

The package uses three functions from `original/comp.py` as they were written:

- `render` rasterises a page
- `spans` reads text spans
- `bands` finds horizontal ink rows

The markup page (design, red boxes, blue dashes, number circles, notes panel) is adapted from `build` in `original/markup2.py`. The side by side page (template on the left, design on the right, same scale) is adapted from `draw_pair` in `original/v3.py`. The summary page is adapted from the `line` helper in `original/markup2.py`. Each adapted function says so in a comment.

Everything else is new: trim detection, finding elements, matching them, measuring them, the notes, the optional Gemini step, the command line, and the HTTP service.

`side()` in `original/comp.py` only builds a PNG contact sheet. This package does not use it. `original/bands.py` is an earlier copy of the ink row printer. The package calls `bands` from `comp.py`.

## What it measures

On each paired page it finds:

- text lines (grouped from spans)
- images
- drawn rules and other drawn shapes
- ink regions that are not already one of those

It pairs each design element with a template element by role, text, and position. For each pair it measures position, size in points, font, font size, and colour. It also reports missing elements, extra elements, text that is cut off, and text that runs outside the trim.

Roles are generic: heading, text, phone number, email, link, rule, image, small image, graphic, ink region. A phone number or an email is recognised from the characters. Everything else is text or a heading when the type is clearly larger. There is no list of product elements.

## Limits

These are real limits. Read them before trusting a note.

**Pages are paired in order.** Page 1 of the design is compared with page 1 of the template, then page 2 with page 2. The tool does not hunt for a "similar" page. If the design has an extra cover, every later page is compared with the wrong template page. Extra design pages and missing template pages are reported. They are not matched by picture.

**Page size is the trim, and elements are fractions of that trim.** Position is "how far down this page", then converted to millimetres on the design page. A different page size is its own issue. The same point size on a smaller page is not reported as a bigger font. Width and height are compared in points.

**Trim detection is only as good as the file.** The order is: a real TrimBox, then ArtBox, then CropBox, otherwise the whole page. A full bleed file that never declares a trim is compared edge to edge, bleed included. The old Stone scripts typed those trims in by hand because many of those files did not declare one. This tool will not guess a trim that is not in the file.

**A flattened page has no fonts.** If the page is one picture, or the letters are outlined paths, there is no font name and no font size. Ink rows from `bands` give position and a colour. Items that sit on the same row are split only when there is a clear gap. Tight rows can merge into one region.

**Matching can pair the wrong things.** It is a score, not a person looking at the layout. Two similar lines can swap. A block that moved a long way can come back as "missing" plus "extra" instead of "moved". Repeated items (two phone numbers, two photos) are separated mainly by position.

**One note per element.** A paragraph that shares a font and a colour can be one element. Letters inside a word are not separate issues. Drawn paths that touch each other become one graphic, so a logo is not measured stroke by stroke.

**Small differences are ignored.** This is so antialiasing and sub point noise are not issues. The thresholds are:

| Check | Reported when |
| --- | --- |
| Position | at least 0.8% of that side of the trim |
| Size | at least 4% in points |
| Font size | at least 0.4 pt |
| Colour | at least 12 levels apart on one RGB channel |
| Page size | at least 1% in width or height |

A brand colour that differs by less than 12 levels on every channel is not reported. Photos are not given a single colour. The optional image check is the place that looks at artwork.

**Cut off and overflow are not a full preflight.** Overflow means the text box extends more than 2 pt outside the trim. Cut off means a glyph crosses the trim, or `get_texttrace` still has characters that the visible line does not (a clip hid them). A clip path in the middle of a page is caught only when those hidden glyphs are still in the file. Text that was never written into the PDF cannot be seen.

**Notes on the PDF use the standard Helvetica fonts.** Characters outside WinAnsi can be replaced in the drawn note. The JSON issue keeps the original text.

**This is not a print proof.** It does not check image resolution, bleed safety, overprint, spot colours, or transparency. Password protected PDFs are rejected. A file over 40 MB is rejected.

**The model does not measure.** See below. If it adds a number, a colour, or a dash that was not measured, that sentence is thrown away.

## Optional Gemini step

If `GEMINI_API_KEY` is set, two things happen after the measurements exist:

1. The measured sentences are rewritten into shorter plain sentences. The prompt forbids new numbers and forbids hyphens, en dashes, and em dashes. A reply that breaks that rule is discarded and the measured sentence stays.
2. Up to six small image regions (images, small images, and graphics, each under 25% of the page) are sent as pictures. The model may say the artwork looks different. It is told not to state sizes. A reply that contains a number or a dash is replaced with a fixed sentence that has no measurement.

The measurements in the JSON are never replaced by the model. Default model is `gemini-2.5-pro`. Set the model to `gemini-2.5-flash` if you want the faster one. Those are the only two accepted names.

No key, or `--no-ai`, or `use_ai=false`: the tool still compares and still writes the PDF. The notes are the measured sentences.

## Command line

```bash
pip install -e ".[dev]"
compare template.pdf design.pdf -o out.pdf --mode markup
compare template.pdf design.pdf -o out.pdf --mode side-by-side --no-ai
compare template.pdf design.pdf -o out.pdf --mode markup --model gemini-2.5-flash --issues issues.json
```

`--mode` is `markup` (the design, with notes beside or below it) or `side-by-side` (template on the left, design on the right, same scale). `-o` is required.

## HTTP service

For the Beleef Admin app, run the API and `POST /compare` with the two PDFs. Nothing is stored after the response.

```bash
uvicorn template_compare.api:app --host 0.0.0.0 --port 8000
```

`GET /health` returns `{"status": "ok"}`. Interactive docs are at `/docs`.

```bash
curl -s -X POST http://localhost:8000/compare \
  -F "template=@template.pdf;type=application/pdf" \
  -F "design=@design.pdf;type=application/pdf" \
  -F "mode=markup" \
  -F "use_ai=auto" \
  -F "model=gemini-2.5-pro" \
  -o response.json
```

Form fields:

| Field | Meaning |
| --- | --- |
| `template` | Template PDF file |
| `design` | Design PDF file |
| `mode` | `markup` (default) or `side-by-side` |
| `model` | `gemini-2.5-pro` (default) or `gemini-2.5-flash` |
| `use_ai` | `auto` (default), `true`, or `false`. `auto` calls Gemini only when the key is set. `true` with no key still returns the measured result and sets `ai_reason` to `no_api_key`. |

The response is JSON. Treat `measurements` as the facts. Treat `note` as the sentence to show a person. `measured_note` is the sentence from the measurements, before any rewrite.

```json
{
  "mode": "markup",
  "ai_used": false,
  "ai_reason": "no_api_key",
  "ai_notes_rewritten": 0,
  "model": null,
  "template_pages": 1,
  "design_pages": 1,
  "pages": [
    {"design_page": 1, "template_page": 1, "design_width_pt": 780, "design_height_pt": 400, "template_width_pt": 780, "template_height_pt": 400}
  ],
  "issues": [
    {
      "number": 1,
      "page": 1,
      "role": "heading",
      "kind": "difference",
      "kinds": ["font_size", "position"],
      "note": "Heading. Font size is 22 pt and the template is 32 pt, so the design is 31 percent smaller.",
      "measured_note": "Heading. Font size is 22 pt and the template is 32 pt, so the design is 31 percent smaller.",
      "design_bbox": [0.06, 0.24, 0.28, 0.32],
      "template_bbox": [0.06, 0.1, 0.32, 0.2],
      "measurements": {}
    }
  ],
  "pdf_base64": "..."
}
```

`kind` is `difference`, `missing`, `extra`, `page_count`, `page_size`, `extra_page`, or `artwork`. Boxes are fractions of that page's trim. `design_bbox` is null when the element is missing. `template_bbox` is null when the element is extra.

Decode the PDF:

```python
import base64, json
body = json.load(open("response.json"))
open("marked.pdf", "wb").write(base64.b64decode(body["pdf_base64"]))
```

A bad PDF, a bad mode, or a password protected file returns HTTP 400. A file over 40 MB returns HTTP 413.

Environment:

| Variable | Meaning |
| --- | --- |
| `GEMINI_API_KEY` | Optional. Without it, comparison still runs. |
| `PORT` | HTTP port. The process binds `0.0.0.0`. |
| `TEMPLATE_COMPARE_ORIGINAL` | Directory that contains `comp.py`. The Docker image sets this. An editable install from this repo finds `original/` on its own. |

## Docker

The image is for running the service locally. This repo does not deploy it.

```bash
docker build -t template-compare .
docker run --rm -p 8000:8000 -e GEMINI_API_KEY -e PORT=8000 template-compare
```

The original scripts are copied into the image so `render`, `spans`, and `bands` can be loaded. They are not modified.

## Tests

```bash
pip install -e ".[dev]"
python -m pytest
```

The tests build small PDFs. They use two different layouts (a wide page and a tall page, different type, colours, and pictures), plus page count mismatches and page size mismatches. They do not use the old Stone files. One test checks that `original/` still matches `SHA256SUMS.txt`.
