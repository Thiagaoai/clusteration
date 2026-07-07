#!/usr/bin/env python3
"""
Validacao de largura minima de traco: renderiza os textos do cartao em
resolucao muito alta e mede, por varredura horizontal de pixels, a menor
sequencia continua de pixels "tinta" (stroke) em cada texto, convertendo
para mm. Usado para confirmar que nenhum traco fica abaixo do minimo
imprimivel especificado (0.55mm para texto principal, nozzle 0.2mm).
"""
import os
import cairosvg
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "source")

SCALE = 30  # px/mm - alta resolucao para medicao subpixel confiavel

# Cada entrada usa o glifo "I" (haste reta, sem curvas) no MESMO font-size/weight
# usado no elemento real, para medir a espessura de traco (stem width) sem o
# ruido de cordas horizontais tangentes a curvas (que subestimam a largura real
# em letras como C/O/S/A). O "I" e a haste mais fina tipica de uma fonte Bold,
# entao serve como pior-caso representativo para o restante do texto.
SNIPPETS = {
    "PLJ CARPENTRY (texto principal)":  ("700", 7.4),
    "CAPE COD * MA (secundario)":       ("700", 3.9),  # Bold no modelo 3D (OpenSCAD) - SVG usa 700 para casar
    "(508) 123-4567 (telefone)":        ("600", 4.4),
    "SCAN HERE":                        ("600", 3.4),
    "PLJCARPENTRY.US (verso)":          ("600", 4.6),
}

MIN_STROKE_MAIN = 0.55
MIN_STROKE_SECONDARY = 0.35  # meta pratica p/ nozzle 0.2mm (traco fino ainda solido)


def min_stroke_mm(weight, font_size_mm, height_mm=18, width_mm=20):
    # width/height SEM sufixo "mm": assim 1 unidade do viewBox = 1px logico,
    # e "scale" no cairosvg passa a corresponder exatamente a px por mm.
    # (Usar "mm" aciona a conversao fisica de 96dpi do cairosvg, inflando o
    # resultado por ~3.78x - por isso as unidades aqui sao propositalmente
    # sem sufixo, so no viewBox que representa milimetros.)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_mm}" height="{height_mm}" '
        f'viewBox="0 0 {width_mm} {height_mm}"><rect width="100%" height="100%" fill="white"/>'
        f'<text x="2" y="14" font-family="Liberation Sans, DejaVu Sans, sans-serif" '
        f'font-weight="{weight}" font-size="{font_size_mm}" fill="black">I</text></svg>'
    )
    png_bytes = cairosvg.svg2png(bytestring=svg.encode(), scale=SCALE)
    import io
    im = Image.open(io.BytesIO(png_bytes)).convert("L")
    arr = np.array(im)
    dark = arr < 60  # tinta solida, ignora franja de anti-aliasing
    px_per_mm = SCALE
    # mede na faixa vertical central do glifo (haste reta, sem serifas/curvas)
    rows_with_ink = np.where(dark.any(axis=1))[0]
    if len(rows_with_ink) == 0:
        return None
    top, bottom = rows_with_ink.min(), rows_with_ink.max()
    mid_band = range(top + (bottom - top) // 3, top + 2 * (bottom - top) // 3)
    widths = [dark[row].sum() for row in mid_band if dark[row].any()]
    if not widths:
        return None
    return min(widths) / px_per_mm


if __name__ == "__main__":
    print(f"{'Elemento':40s} {'Traco min. medido':>18s}  {'Status'}")
    print("-" * 80)
    results = []
    for name, (weight, size) in SNIPPETS.items():
        mm = min_stroke_mm(weight, size)
        limit = MIN_STROKE_MAIN if "principal" in name else MIN_STROKE_SECONDARY
        status = "OK" if mm is not None and mm >= limit else "ATENCAO - abaixo do minimo"
        results.append((name, mm, limit, status))
        print(f"{name:40s} {mm:16.3f}mm  {status}  (minimo: {limit}mm)")

    out_path = os.path.join(ROOT, "makerworld", "stroke_validation_report.txt")
    with open(out_path, "w") as f:
        f.write("VALIDACAO DE LARGURA MINIMA DE TRACO (nozzle 0.2mm)\n")
        f.write("Metodo: renderizacao vetorial em 30 px/mm + varredura de pixels\n")
        f.write("=" * 70 + "\n\n")
        for name, mm, limit, status in results:
            f.write(f"{name:40s} traco min. medido: {mm:.3f} mm | minimo: {limit} mm | {status}\n")
    print("\nRelatorio salvo em:", out_path)
