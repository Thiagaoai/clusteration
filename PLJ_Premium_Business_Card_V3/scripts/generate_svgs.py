#!/usr/bin/env python3
"""
Gera todos os arquivos SVG (100% vetoriais) para o PLJ Premium Business Card V3:
  source/logo_clean.svg
  source/qr_code.svg
  source/leather_texture.svg
  source/card_front.svg
  source/card_back.svg

Também grava models/qr_matrix.json (matriz booleana do QR) para ser reutilizada
pelo modelo OpenSCAD, garantindo que o relevo 3D corresponda exatamente ao SVG.
"""
import json
import math
import os

import qrcode
from qrcode.constants import ERROR_CORRECT_M

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "source")
MODELS = os.path.join(ROOT, "models")
os.makedirs(SRC, exist_ok=True)
os.makedirs(MODELS, exist_ok=True)

CARD_W = 85.0
CARD_H = 54.0
FONT_FAMILY = "Liberation Sans, DejaVu Sans, Arial, sans-serif"
GOLD = "#C9A227"
BLACK = "#101010"
DARK_BG = "#0B0B0B"

# ---------------------------------------------------------------------------
# 1. Saw blade icon (logo sem circulo externo) - gerado proceduralmente
# ---------------------------------------------------------------------------

def saw_blade_path(cx, cy, r_outer, r_root, teeth=18, tooth_bias=0.62):
    """Retorna os pontos (silhueta) de uma serra circular com dentes triangulares
    assimetricos (sem o anel/circulo externo continuo)."""
    pts = []
    step = 2 * math.pi / teeth
    for i in range(teeth):
        a0 = i * step
        a1 = a0 + step * tooth_bias
        a2 = a0 + step
        # base do dente (raio menor)
        pts.append((cx + r_root * math.cos(a0), cy + r_root * math.sin(a0)))
        # ponta do dente (raio maior) - deslocada para dar efeito de corte
        pts.append((cx + r_outer * math.cos(a1), cy + r_outer * math.sin(a1)))
        # volta para o raio menor antes do proximo dente
        pts.append((cx + r_root * math.cos(a2), cy + r_root * math.sin(a2)))
    return pts


def points_to_path(pts, close=True):
    d = f"M {pts[0][0]:.3f},{pts[0][1]:.3f} "
    d += " ".join(f"L {x:.3f},{y:.3f}" for x, y in pts[1:])
    if close:
        d += " Z"
    return d


def saw_blade_svg_fragment(cx, cy, r_outer, fill=BLACK, accent=GOLD, id_suffix=""):
    """Icone da serra circular: dentes + furos de ventilacao + furo central.
    NAO possui circulo externo continuo (removido conforme especificacao)."""
    r_root = r_outer * 0.78
    r_hole_ring = r_outer * 0.42
    r_center = r_outer * 0.10
    blade_pts = saw_blade_path(cx, cy, r_outer, r_root, teeth=18)
    blade_d = points_to_path(blade_pts)

    holes = []
    n_holes = 6
    for i in range(n_holes):
        a = (2 * math.pi / n_holes) * i
        hx = cx + r_hole_ring * math.cos(a)
        hy = cy + r_hole_ring * math.sin(a)
        holes.append(f'<circle cx="{hx:.3f}" cy="{hy:.3f}" r="{r_outer*0.07:.3f}" fill="{fill}" fill-opacity="0" stroke="{accent}" stroke-width="0.25"/>')

    frag = [
        f'<g id="saw-blade{id_suffix}">',
        f'  <path d="{blade_d}" fill="{fill}" stroke="{accent}" stroke-width="0.35" stroke-linejoin="round"/>',
        f'  <circle cx="{cx:.3f}" cy="{cy:.3f}" r="{r_hole_ring+r_outer*0.09:.3f}" fill="none" stroke="{accent}" stroke-width="0.30"/>',
    ]
    frag += [f"  {h}" for h in holes]
    frag.append(f'  <circle cx="{cx:.3f}" cy="{cy:.3f}" r="{r_center:.3f}" fill="{accent}"/>')
    frag.append("</g>")
    return "\n".join(frag)


def write_logo_clean():
    """Lockup completo: serra circular (sem anel externo) + PLJ CARPENTRY + CAPE COD * MA."""
    w, h = 60.0, 34.0
    cx, cy, r = 17.0, 14.0, 11.5
    blade = saw_blade_svg_fragment(cx, cy, r, fill=BLACK, accent=GOLD)
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" viewBox="0 0 {w} {h}">
  <title>PLJ Carpentry - Logo Limpo (sem circulo externo)</title>
  {blade}
  <text x="{cx-r+1:.2f}" y="27.5" font-family="{FONT_FAMILY}" font-weight="700" font-size="8.6" letter-spacing="0.3" fill="{BLACK}">PLJ CARPENTRY</text>
  <text x="{cx-r+1:.2f}" y="33.0" font-family="{FONT_FAMILY}" font-weight="500" font-size="4.0" letter-spacing="0.6" fill="{GOLD}">CAPE COD &#8226; MA</text>
</svg>
'''
    path = os.path.join(SRC, "logo_clean.svg")
    with open(path, "w") as f:
        f.write(svg)
    print("OK:", path)


# ---------------------------------------------------------------------------
# 2. Leather texture (padrao tileable, 100% vetorial)
# ---------------------------------------------------------------------------

def write_leather_texture():
    tile = 8.0
    lines = []
    # Losangos irregulares tipo "couro pull-up" com micro veios - tudo em <path>/<line>, sem raster.
    import random
    random.seed(42)
    # Nota: contraste elevado aqui de proposito para o PREVIEW vetorial/PNG
    # ficar legivel como "textura de couro" numa miniatura/thumbnail. A
    # profundidade FISICA real do relevo (0.08-0.12mm) e definida separadamente
    # em models/plj_card_complete.scad (LEATHER_DEPTH) e nao muda com isto.
    for gx in range(0, int(tile) + 1, 2):
        for gy in range(0, int(tile) + 1, 2):
            jitter_x = random.uniform(-0.35, 0.35)
            jitter_y = random.uniform(-0.35, 0.35)
            x, y = gx + jitter_x, gy + jitter_y
            lines.append(f'<path d="M {x-0.9:.2f},{y:.2f} L {x:.2f},{y-0.9:.2f} L {x+0.9:.2f},{y:.2f} L {x:.2f},{y+0.9:.2f} Z" fill="none" stroke="#5a4a32" stroke-width="0.09" stroke-opacity="0.85"/>')
    for i in range(0, int(tile) + 2, 1):
        lines.append(f'<line x1="{i}" y1="0" x2="{i-2}" y2="{tile}" stroke="#413424" stroke-width="0.06" stroke-opacity="0.6"/>')

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{tile}mm" height="{tile}mm" viewBox="0 0 {tile} {tile}">
  <title>Leather texture tile (vetorial, tileable {tile}x{tile}mm)</title>
  <defs>
    <pattern id="leatherTile" width="{tile}" height="{tile}" patternUnits="userSpaceOnUse">
      <rect width="{tile}" height="{tile}" fill="#171512"/>
      {chr(10).join(lines)}
    </pattern>
  </defs>
  <rect width="{tile}" height="{tile}" fill="url(#leatherTile)"/>
</svg>
'''
    path = os.path.join(SRC, "leather_texture.svg")
    with open(path, "w") as f:
        f.write(svg)
    print("OK:", path)
    return tile, "\n".join(lines)


# ---------------------------------------------------------------------------
# 3. QR code (vetorial - paths reais, sem raster) apontando para o site
# ---------------------------------------------------------------------------

def build_qr_matrix(url="https://pljcarpentry.us"):
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, border=0)
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()  # list[list[bool]]
    return matrix, qr.version


def write_qr_svg(matrix, quiet_zone_mm=2.5, module_mm=0.85):
    n = len(matrix)
    total = n * module_mm + 2 * quiet_zone_mm
    rects = []
    for row_idx, row in enumerate(matrix):
        for col_idx, dark in enumerate(row):
            if dark:
                x = quiet_zone_mm + col_idx * module_mm
                y = quiet_zone_mm + row_idx * module_mm
                rects.append(f'<rect x="{x:.3f}" y="{y:.3f}" width="{module_mm:.3f}" height="{module_mm:.3f}"/>')
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{total:.2f}mm" height="{total:.2f}mm" viewBox="0 0 {total:.3f} {total:.3f}">
  <title>QR Code - https://pljcarpentry.us (modulo {module_mm}mm, quiet zone {quiet_zone_mm}mm)</title>
  <rect x="0" y="0" width="{total:.3f}" height="{total:.3f}" fill="#FFFFFF"/>
  <g fill="#000000">
    {chr(10).join(rects)}
  </g>
</svg>
'''
    path = os.path.join(SRC, "qr_code.svg")
    with open(path, "w") as f:
        f.write(svg)
    print("OK:", path, f"(versao QR={None}, modulos={n}x{n}, lado total={total:.2f}mm)")
    return total, n


def qr_group_fragment(matrix, ox, oy, quiet_zone_mm, module_mm, dark="#000000"):
    """Fragmento <g> do QR posicionado em (ox,oy) para ser embutido no card_front.svg."""
    rects = []
    for row_idx, row in enumerate(matrix):
        for col_idx, dark_module in enumerate(row):
            if dark_module:
                x = ox + quiet_zone_mm + col_idx * module_mm
                y = oy + quiet_zone_mm + row_idx * module_mm
                rects.append(f'<rect x="{x:.3f}" y="{y:.3f}" width="{module_mm:.3f}" height="{module_mm:.3f}"/>')
    return f'<g fill="{dark}">\n' + "\n".join(rects) + "\n</g>"


# ---------------------------------------------------------------------------
# 4. Card front / back
# ---------------------------------------------------------------------------

def phone_icon(x, y, size, color=GOLD):
    s = size
    return f'''<g transform="translate({x:.2f},{y:.2f})" fill="none" stroke="{color}" stroke-width="0.45" stroke-linecap="round" stroke-linejoin="round">
    <path d="M {0.15*s},{0.02*s} L {0.42*s},{0.02*s} L {0.52*s},{0.28*s} L {0.34*s},{0.40*s} C {0.44*s},{0.66*s} {0.56*s},{0.78*s} {0.80*s},{0.86*s} L {0.92*s},{0.66*s} L {s},{0.78*s} L {s},{0.94*s} C {s},{0.98*s} {0.96*s},{s} {0.92*s},{s} C {0.42*s},{s} {0},{0.58*s} {0},{0.08*s} C {0},{0.05*s} {0.05*s},{0.02*s} {0.15*s},{0.02*s} Z" fill="{color}" stroke="none"/>
  </g>'''


def write_card_front(logo_r=6.0):
    # Layout dimensionado a partir da largura REAL renderizada de cada texto
    # (medida com cairosvg, ver scripts/validate_stroke_widths.py) para
    # garantir que nada extrapole a borda do cartao - um layout definido "no
    # olho" aqui fez "PLJ CARPENTRY" estourar ~2mm alem da borda direita.
    matrix, version = build_qr_matrix()
    n = len(matrix)
    quiet = 2.5           # spec: quiet zone 2.50mm
    module = 0.68         # spec: modulo minimo 0.60mm (0.68mm da margem de seguranca)
    qr_side = n * module + 2 * quiet  # 25*0.68 + 5 = 22.0mm

    blade_cx, blade_cy = 10.5, 15.0
    blade = saw_blade_svg_fragment(blade_cx, blade_cy, logo_r, fill=BLACK, accent=GOLD)

    text_x = blade_cx + logo_r + 2.5   # 19.0

    TITLE_SIZE = 4.5       # largura real ~37.1mm, traco ~0.65mm (>= 0.55mm exigido)
    SUBTITLE_SIZE = 3.4    # largura real ~26.1mm, traco ~0.45mm
    PHONE_SIZE = 3.8       # largura real ~25.4mm, traco ~0.55mm
    SCAN_SIZE = 3.4        # largura real ~19.7mm, traco ~0.45mm

    divider_x = text_x + 40.0   # 59.0 - folga apos o texto mais longo (titulo, ~37.1mm)
    qr_x = CARD_W - qr_side - 2.0
    qr_y = (CARD_H - qr_side) / 2 - 1.0

    qr_frag = qr_group_fragment(matrix, qr_x, qr_y, quiet, module, dark=BLACK)

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}mm" height="{CARD_H}mm" viewBox="0 0 {CARD_W} {CARD_H}">
  <title>PLJ Carpentry - Cartao de Visita 3D - Frente</title>
  <defs>
    <clipPath id="cardClipFront">
      <rect x="0" y="0" width="{CARD_W}" height="{CARD_H}" rx="4" ry="4"/>
    </clipPath>
  </defs>
  <g clip-path="url(#cardClipFront)">
    <rect x="0" y="0" width="{CARD_W}" height="{CARD_H}" fill="{BLACK}"/>
    <rect x="1.2" y="1.2" width="{CARD_W-2.4}" height="{CARD_H-2.4}" rx="3.2" ry="3.2" fill="none" stroke="{GOLD}" stroke-width="1.2"/>

    {blade}

    <text x="{text_x:.2f}" y="13.0" font-family="{FONT_FAMILY}" font-weight="700" font-size="{TITLE_SIZE}" fill="#F5F1E6">PLJ CARPENTRY</text>
    <text x="{text_x:.2f}" y="19.2" font-family="{FONT_FAMILY}" font-weight="700" font-size="{SUBTITLE_SIZE}" fill="{GOLD}">CAPE COD &#8226; MA</text>

    {phone_icon(text_x, 27.5, 4.6, color=GOLD)}
    <text x="{text_x+6.4:.2f}" y="31.7" font-family="{FONT_FAMILY}" font-weight="600" font-size="{PHONE_SIZE}" fill="#F5F1E6">(508) 123-4567</text>

    <line x1="{divider_x:.2f}" y1="7.5" x2="{divider_x:.2f}" y2="{CARD_H-7.5:.2f}" stroke="{GOLD}" stroke-width="0.5"/>

    <rect x="{qr_x-1.4:.2f}" y="{qr_y-1.4:.2f}" width="{qr_side+2.8:.2f}" height="{qr_side+2.8:.2f}" fill="#FFFFFF" rx="1.2" ry="1.2"/>
    <rect x="{qr_x:.2f}" y="{qr_y:.2f}" width="{qr_side:.2f}" height="{qr_side:.2f}" fill="#FFFFFF"/>
    {qr_frag}
    <text x="{qr_x+qr_side/2:.2f}" y="{qr_y+qr_side+4.6:.2f}" text-anchor="middle" font-family="{FONT_FAMILY}" font-weight="600" font-size="{SCAN_SIZE}" fill="{GOLD}">SCAN HERE</text>
  </g>
</svg>
'''
    path = os.path.join(SRC, "card_front.svg")
    with open(path, "w") as f:
        f.write(svg)
    print("OK:", path)

    layout = dict(
        matrix_size=n, qr_version=version, quiet_zone_mm=quiet, module_mm=module,
        qr_side_mm=qr_side, qr_x=qr_x, qr_y=qr_y, divider_x=divider_x,
        blade_cx=blade_cx, blade_cy=blade_cy, blade_r=logo_r,
        text_x=text_x,
        title_size=TITLE_SIZE, subtitle_size=SUBTITLE_SIZE,
        phone_size=PHONE_SIZE, scan_size=SCAN_SIZE,
    )
    with open(os.path.join(MODELS, "front_layout.json"), "w") as f:
        json.dump(layout, f, indent=2)
    with open(os.path.join(MODELS, "qr_matrix.json"), "w") as f:
        json.dump({"matrix": [[bool(c) for c in row] for row in matrix],
                   "version": version, "quiet_zone_mm": quiet, "module_mm": module}, f)
    return layout


def write_card_back(tile_size, leather_lines):
    blade_cx, blade_cy, blade_r = CARD_W / 2, 17.0, 6.0
    blade = saw_blade_svg_fragment(blade_cx, blade_cy, blade_r, fill=BLACK, accent=GOLD, id_suffix="-back")

    tiles_x = math.ceil(CARD_W / tile_size) + 1
    tiles_y = math.ceil(CARD_H / tile_size) + 1

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}mm" height="{CARD_H}mm" viewBox="0 0 {CARD_W} {CARD_H}">
  <title>PLJ Carpentry - Cartao de Visita 3D - Verso (leather texture)</title>
  <defs>
    <clipPath id="cardClipBack">
      <rect x="0" y="0" width="{CARD_W}" height="{CARD_H}" rx="4" ry="4"/>
    </clipPath>
    <pattern id="leatherTileBack" width="{tile_size}" height="{tile_size}" patternUnits="userSpaceOnUse">
      <rect width="{tile_size}" height="{tile_size}" fill="#171512"/>
      {leather_lines}
    </pattern>
  </defs>
  <g clip-path="url(#cardClipBack)">
    <rect x="0" y="0" width="{CARD_W}" height="{CARD_H}" fill="url(#leatherTileBack)"/>
    <rect x="1.2" y="1.2" width="{CARD_W-2.4}" height="{CARD_H-2.4}" rx="3.2" ry="3.2" fill="none" stroke="{GOLD}" stroke-width="1.2"/>
    {blade}
    <text x="{CARD_W/2:.2f}" y="{blade_cy+blade_r+7.5:.2f}" text-anchor="middle" font-family="{FONT_FAMILY}" font-weight="600" font-size="4.6" letter-spacing="1.6" fill="{GOLD}">PLJCARPENTRY.US</text>
  </g>
</svg>
'''
    path = os.path.join(SRC, "card_back.svg")
    with open(path, "w") as f:
        f.write(svg)
    print("OK:", path)


if __name__ == "__main__":
    write_logo_clean()
    tile, leather_lines = write_leather_texture()
    matrix, version = build_qr_matrix()
    write_qr_svg(matrix)
    write_card_front()
    write_card_back(tile, leather_lines)
    print("\nTodos os SVG gerados em:", SRC)
