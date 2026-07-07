#!/usr/bin/env python3
"""Renderiza PNGs em alta resolucao a partir dos SVGs vetoriais (source/ -> png/)."""
import os
import cairosvg
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "source")
PNG = os.path.join(ROOT, "png")
os.makedirs(PNG, exist_ok=True)

SCALE = 16  # ~400dpi equivalente (16 px/mm) para preview premium em alta resolucao


def render(svg_name, png_name, scale=SCALE):
    svg_path = os.path.join(SRC, svg_name)
    png_path = os.path.join(PNG, png_name)
    cairosvg.svg2png(url=svg_path, write_to=png_path, scale=scale)
    im = Image.open(png_path)
    print(f"OK: {png_path}  ({im.size[0]}x{im.size[1]}px)")


def render_full():
    front_path = os.path.join(PNG, "preview_front.png")
    back_path = os.path.join(PNG, "preview_back.png")
    front = Image.open(front_path)
    back = Image.open(back_path)
    pad = int(0.4 * SCALE)
    gap = int(6 * SCALE)
    w = front.width + back.width + gap + 2 * pad
    h = max(front.height, back.height) + 2 * pad
    canvas = Image.new("RGBA", (w, h), (18, 16, 14, 255))
    canvas.paste(front, (pad, pad), front)
    canvas.paste(back, (pad + front.width + gap, pad), back)
    out_path = os.path.join(PNG, "preview_full.png")
    canvas.save(out_path)
    print(f"OK: {out_path}  ({canvas.size[0]}x{canvas.size[1]}px)")


if __name__ == "__main__":
    render("card_front.svg", "preview_front.png")
    render("card_back.svg", "preview_back.png")
    render("logo_clean.svg", "logo_clean.png")
    render_full()
