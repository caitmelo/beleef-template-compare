"""Small generated PDFs. Two layouts, plus mismatched page counts and sizes."""

from __future__ import annotations

import io

import pymupdf
from PIL import Image, ImageDraw


def _png(size, fill, outline=(255, 255, 255)) -> bytes:
    image = Image.new("RGB", size, fill)
    draw = ImageDraw.Draw(image)
    draw.rectangle((6, 6, size[0] - 7, size[1] - 7), outline=outline, width=3)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def build_ray_white(path, design: bool = False) -> None:
    """Wide landscape page: heading, stacked lines, a rule, a wide image."""

    document = pymupdf.open()
    page = document.new_page(width=780, height=400)
    gold = (0.95, 0.75, 0.1)
    ink = (0.1, 0.1, 0.15)
    if design:
        page.insert_text((48, 118), "Ray White", fontsize=22, fontname="times-bold", color=gold)
    else:
        page.insert_text((48, 72), "Ray White", fontsize=32, fontname="times-bold", color=gold)
    page.insert_text((48, 170), "Open home Saturday", fontsize=16, fontname="helv", color=ink)
    page.insert_text((48, 210), "14 Beach Road", fontsize=12, fontname="helv", color=ink)
    phone = (0.8, 0.05, 0.05) if design else (0, 0, 0)
    page.insert_text((48, 250), "0412 111 222", fontsize=12, fontname="helv", color=phone)
    if not design:
        page.insert_text((48, 290), "team@raywhite.example", fontsize=12, fontname="helv", color=ink)
    if design:
        page.insert_text((48, 360), "Auction 2pm", fontsize=14, fontname="helv", color=ink)
    if design:
        page.draw_rect(pymupdf.Rect(200, 310, 420, 318), fill=(0, 0.15, 0.4), color=(0, 0.15, 0.4))
    else:
        page.draw_rect(pymupdf.Rect(80, 310, 540, 318), fill=(0, 0.15, 0.4), color=(0, 0.15, 0.4))
    page.insert_image(pymupdf.Rect(600, 36, 740, 100), stream=_png((160, 70), (20, 60, 140)))
    document.save(path)
    document.close()


def build_harbor(path, design: bool = False) -> None:
    """Tall portrait page: a different heading, a short or long rule, a square image low down."""

    document = pymupdf.open()
    page = document.new_page(width=450, height=720)
    navy = (0.05, 0.12, 0.35)
    font = "helv" if design else "times-bold"
    page.insert_text((40, 96), "Harbor Lane", fontsize=28, fontname=font, color=navy)
    if design:
        page.draw_rect(pymupdf.Rect(40, 120, 180, 132), fill=(0.75, 0.1, 0.15), color=(0.75, 0.1, 0.15))
    else:
        page.draw_rect(pymupdf.Rect(40, 120, 400, 132), fill=(0.75, 0.1, 0.15), color=(0.75, 0.1, 0.15))
    body = (0.55, 0.1, 0.1) if design else (0.15, 0.15, 0.15)
    page.insert_text((40, 190), "Price on request", fontsize=14, fontname="helv", color=body)
    page.insert_text((40, 230), "Inspect by appointment", fontsize=12, fontname="helv", color=(0.15, 0.15, 0.15))
    page.insert_text((40, 660), "0399 123 456", fontsize=13, fontname="helv", color=navy)
    box = pymupdf.Rect(90, 580, 170, 660) if design else pymupdf.Rect(40, 560, 120, 640)
    page.insert_image(box, stream=_png((80, 80), (180, 40, 40)))
    document.save(path)
    document.close()


def build_stack(path, count: int, width: float, height: float, heading_y: float, heading: str = "North Office") -> None:
    document = pymupdf.open()
    for index in range(count):
        page = document.new_page(width=width, height=height)
        text = heading if index == 0 else f"Follow up {index + 1}"
        page.insert_text((width * 0.1, heading_y * height), text, fontsize=22, fontname="helv")
        page.insert_text((width * 0.1, heading_y * height + 36), "Shared body line for the pair", fontsize=12, fontname="helv")
    document.save(path)
    document.close()


def build_word(path, text: str, width=400, height=300) -> None:
    document = pymupdf.open()
    page = document.new_page(width=width, height=height)
    page.insert_text((40, 80), text, fontsize=20, fontname="helv")
    document.save(path)
    document.close()


def build_trim_word(path, overflow: bool) -> None:
    document = pymupdf.open()
    page = document.new_page(width=420, height=420)
    document.xref_set_key(page.xref, "TrimBox", "[30 30 390 390]")
    point = (300, 120) if overflow else (60, 120)
    page.insert_text(point, "Overflowing", fontsize=28, fontname="helv")
    document.save(path)
    document.close()


def build_clipped(path) -> None:
    """A long word with a clip path, so only the first letters stay visible."""

    document = pymupdf.open()
    page = document.new_page(width=360, height=240)
    page.insert_text((20, 120), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", fontsize=22, fontname="helv")
    xref = page.get_contents()[0]
    stream = document.xref_stream(xref)
    document.update_stream(xref, b"q\n20 40 70 100 re W n\n" + stream + b"\nQ\n")
    document.save(path)
    document.close()


def build_visible_prefix(path) -> None:
    document = pymupdf.open()
    page = document.new_page(width=360, height=240)
    page.insert_text((20, 120), "ABCDE", fontsize=22, fontname="helv")
    document.save(path)
    document.close()
