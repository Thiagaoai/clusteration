// =====================================================================
// PLJ CARPENTRY - Premium Business Card V3
// Modelo parametrico gerado automaticamente por scripts/generate_scad.py
// NAO editar a matriz do QR manualmente - ela e derivada de qr_matrix.json
// para garantir que o relevo impresso corresponda ao QR real e escaneavel.
// =====================================================================

// ---------- Parametro de selecao de parte para export (via -D) ----------
PART = "complete"; // "complete" | "front" (gold_details) | "back" (black_base)

$fn = 48;

// ---------- Dimensoes gerais do cartao ----------
CARD_W   = 85.0;
CARD_H   = 54.0;
THICK    = 2.60;   // espessura total da base (preta)
CORNER_R = 4.0;
CHAMFER  = 0.30;   // chanfro 45 graus nas bordas

// ---------- Moldura dourada ----------
FRAME_W = 1.20;
FRAME_H = 0.40;
FRAME_INSET = 1.2;

// ---------- Logo (serra circular) - 3 niveis ----------
LOGO_CX = 10.5;
LOGO_CY = 39.0;
LOGO_R  = 6.0;
LOGO_TEETH = 18;
LOGO_TIER1_H = 0.20; // silhueta da serra (dentes)
LOGO_TIER2_H = 0.40; // anel medio
LOGO_TIER3_H = 0.80; // cubo central (mancal)

// ---------- Textos (altura adicional acima da face) ----------
TEXT_MAIN_H       = 0.70; // "PLJ CARPENTRY" - largura minima de traco 0.55mm
TEXT_SECONDARY_H  = 0.45; // "CAPE COD * MA", telefone, "SCAN HERE"
TEXT_X            = 19.0;
TITLE_SIZE        = 4.5;
SUBTITLE_SIZE     = 3.4;
PHONE_SIZE        = 3.8;
SCAN_SIZE         = 3.4;

// ---------- Divisoria vertical ----------
DIVIDER_X = 59.0;
DIVIDER_H = 0.30;
DIVIDER_W = 0.50;

// ---------- QR Code ----------
QR_N        = 25;
QR_QUIET    = 2.5;
QR_MODULE   = 0.68;
QR_SIDE     = 22.0;
QR_X        = 61.0;
QR_Y        = 17.0;   // canto inferior-esquerdo da área do QR (coord. OpenSCAD)
QR_POCKET_D = 0.60;  // rebaixo
QR_BUMP_H   = 0.80;  // relevo a partir do fundo do rebaixo
QR_MATRIX = [
  [1,1,1,1,1,1,1,0,0,1,1,0,1,1,0,0,0,0,1,1,1,1,1,1,1],
  [1,0,0,0,0,0,1,0,1,1,1,0,1,0,1,0,0,0,1,0,0,0,0,0,1],
  [1,0,1,1,1,0,1,0,1,1,0,0,0,0,0,0,1,0,1,0,1,1,1,0,1],
  [1,0,1,1,1,0,1,0,1,0,1,0,1,1,0,1,1,0,1,0,1,1,1,0,1],
  [1,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,1,0,1,0,1,1,1,0,1],
  [1,0,0,0,0,0,1,0,0,0,0,1,0,1,0,0,1,0,1,0,0,0,0,0,1],
  [1,1,1,1,1,1,1,0,1,0,1,0,1,0,1,0,1,0,1,1,1,1,1,1,1],
  [0,0,0,0,0,0,0,0,1,0,0,1,0,0,0,0,1,0,0,0,0,0,0,0,0],
  [1,0,0,0,0,0,1,0,1,0,0,0,0,1,1,1,0,1,1,0,0,1,1,1,0],
  [1,1,0,1,1,1,0,0,0,0,0,1,1,1,0,1,0,0,0,1,1,1,1,1,0],
  [1,0,1,0,1,0,1,1,1,1,1,0,1,0,0,1,0,1,0,0,0,1,0,1,1],
  [0,1,1,1,1,0,0,1,0,0,1,1,0,0,1,0,0,0,1,0,0,1,0,0,1],
  [1,1,0,1,1,0,1,1,1,0,0,1,1,0,1,1,0,0,1,0,0,0,0,0,1],
  [1,1,1,0,1,0,0,1,1,0,0,0,0,1,0,1,1,0,0,1,0,0,0,1,0],
  [1,0,1,1,0,0,1,1,1,1,0,1,1,1,1,1,0,0,0,1,1,1,0,1,1],
  [1,0,1,1,1,1,0,0,1,1,0,1,0,0,1,1,1,0,0,1,0,1,1,0,1],
  [1,0,0,1,0,1,1,1,1,0,1,1,0,1,1,1,1,1,1,1,1,0,1,0,0],
  [0,0,0,0,0,0,0,0,1,0,1,0,1,0,1,1,1,0,0,0,1,0,0,0,0],
  [1,1,1,1,1,1,1,0,0,0,0,1,0,1,0,0,1,0,1,0,1,0,0,0,1],
  [1,0,0,0,0,0,1,0,0,0,1,0,1,0,1,1,1,0,0,0,1,0,0,1,0],
  [1,0,1,1,1,0,1,0,0,1,1,0,1,1,1,1,1,1,1,1,1,0,1,1,1],
  [1,0,1,1,1,0,1,0,0,1,0,0,0,0,0,1,1,1,1,0,0,0,0,1,1],
  [1,0,1,1,1,0,1,0,0,0,0,1,1,1,0,1,0,0,0,0,0,1,1,0,1],
  [1,0,0,0,0,0,1,0,0,0,0,1,0,0,1,0,1,0,1,1,1,0,0,0,1],
  [1,1,1,1,1,1,1,0,1,1,0,0,1,1,1,0,1,0,0,0,0,1,0,0,1]
];

// ---------- Verso: logo pequeno + texto (inlay flush, sem interferir na leather) ----------
BACK_LOGO_CX = 42.5;
BACK_LOGO_CY = 37.0;
BACK_LOGO_R  = 6.0;
BACK_TEXT_Y  = 23.5;
BACK_INLAY_D = 0.15; // profundidade do inlay dourado no verso (flush, nao interfere na cama)

// ---------- Leather texture (verso) ----------
LEATHER_DEPTH   = 0.10;  // 0.08-0.12mm
LEATHER_PITCH   = 3.4;
LEATHER_DOT_R   = 0.70;

// ---------- Uniao robusta (evita solidos "encostados" / nao-manifold) ----------
// Toda peca de relevo penetra OVERLAP mm no corpo abaixo dela, garantindo uma
// uniao booleana solida (nao apenas um contato num plano, que o CGAL pode
// deixar como 2 volumes separados/nao-manifold).
OVERLAP = 0.06;

// =====================================================================
// Helpers 2D
// =====================================================================
module rounded_rect(w, h, r) {
    offset(r = r) square([w - 2 * r, h - 2 * r], center = true);
}

module card_outline_2d() {
    translate([CARD_W / 2, CARD_H / 2]) rounded_rect(CARD_W, CARD_H, CORNER_R);
}

module card_outline_inset_2d(inset) {
    translate([CARD_W / 2, CARD_H / 2]) offset(delta = -inset) rounded_rect(CARD_W, CARD_H, CORNER_R);
}

// Serra circular (SEM circulo/anel externo continuo) - dentes triangulares assimetricos
function saw_teeth_points(cx, cy, r_outer, r_root, teeth, bias) =
    [ for (i = [0 : teeth - 1]) each [
        [cx + r_root  * cos(360 * i / teeth),               cy + r_root  * sin(360 * i / teeth)],
        [cx + r_outer * cos(360 * (i + bias) / teeth),      cy + r_outer * sin(360 * (i + bias) / teeth)],
        [cx + r_root  * cos(360 * (i + 1) / teeth),         cy + r_root  * sin(360 * (i + 1) / teeth)]
    ] ];

module saw_blade_2d(cx, cy, r_outer, teeth = 18) {
    r_root = r_outer * 0.78;
    polygon(points = saw_teeth_points(cx, cy, r_outer, r_root, teeth, 0.62));
}

module saw_ring_2d(cx, cy, r_outer) {
    r_hole_ring = r_outer * 0.42;
    ring_w = r_outer * 0.09;
    translate([cx, cy])
        difference() {
            circle(r = r_hole_ring + ring_w);
            circle(r = r_hole_ring - ring_w);
        }
}

// =====================================================================
// Corpo chanfrado (base preta) - chanfro 45 graus em todas as bordas
// =====================================================================
module chamfered_box(w, h, thickness, corner_r, chamfer) {
    union() {
        hull() {
            translate([0, 0, 0])
                linear_extrude(height = 0.001) translate([w/2, h/2]) offset(delta = -chamfer) rounded_rect(w, h, corner_r);
            translate([0, 0, chamfer])
                linear_extrude(height = 0.001) translate([w/2, h/2]) rounded_rect(w, h, corner_r);
        }
        translate([0, 0, chamfer])
            linear_extrude(height = thickness - 2 * chamfer) translate([w/2, h/2]) rounded_rect(w, h, corner_r);
        hull() {
            translate([0, 0, thickness - chamfer])
                linear_extrude(height = 0.001) translate([w/2, h/2]) rounded_rect(w, h, corner_r);
            translate([0, 0, thickness - 0.001])
                linear_extrude(height = 0.001) translate([w/2, h/2]) offset(delta = -chamfer) rounded_rect(w, h, corner_r);
        }
    }
}

// =====================================================================
// Textura leather (verso) - dimples subtraidos, exclui area do logo/texto do verso
// =====================================================================
module leather_dimples() {
    // Cones de baixa resolucao (rapido para booleana CGAL) - suficiente para textura sutil 0.08-0.12mm
    for (gx = [4 : LEATHER_PITCH : CARD_W - 4]) {
        for (gy = [4 : LEATHER_PITCH : CARD_H - 4]) {
            offx = (round(gy / LEATHER_PITCH) % 2 == 0) ? 0 : LEATHER_PITCH / 2;
            x = gx + offx;
            y = gy;
            d_logo = sqrt((x - BACK_LOGO_CX) * (x - BACK_LOGO_CX) + (y - BACK_LOGO_CY) * (y - BACK_LOGO_CY));
            in_text_band = (y > BACK_TEXT_Y - 3.5) && (y < BACK_TEXT_Y + 1.5) && (x > CARD_W/2 - 26) && (x < CARD_W/2 + 26);
            if (x > 3 && x < CARD_W - 3 && y > 3 && y < CARD_H - 3 && d_logo > BACK_LOGO_R + 1.5 && !in_text_band) {
                translate([x, y, -0.01])
                    cylinder(h = LEATHER_DEPTH + 0.02, r1 = LEATHER_DOT_R, r2 = 0, $fn = 6);
            }
        }
    }
}

// =====================================================================
// Grupo PRETO (base) -> Bambu PLA Matte Black
// =====================================================================
module black_base() {
    difference() {
        chamfered_box(CARD_W, CARD_H, THICK, CORNER_R, CHAMFER);

        // Bolso (rebaixo) do QR Code
        translate([QR_X, QR_Y, THICK - QR_POCKET_D])
            linear_extrude(height = QR_POCKET_D + 0.02) square([QR_SIDE, QR_SIDE]);

        // Textura leather no verso (dimples rasos, nao atinge o texto/logo do verso)
        leather_dimples();

        // Inlay (bolso raso) para o logo pequeno + texto do verso, preenchido por gold_details()
        translate([0, 0, -0.01]) linear_extrude(height = BACK_INLAY_D + 0.01)
            saw_blade_2d(BACK_LOGO_CX, BACK_LOGO_CY, BACK_LOGO_R);
        translate([0, 0, -0.01]) linear_extrude(height = BACK_INLAY_D + 0.01)
            translate([CARD_W/2, BACK_TEXT_Y, 0])
                text("PLJCARPENTRY.US", size = 4.6, halign = "center", valign = "baseline",
                     font = "Liberation Sans:style=Bold", spacing = 1.15);
    }
}

// =====================================================================
// Grupo DOURADO (detalhes) -> Bambu PLA Silk Gold
// =====================================================================
module gold_details() {
    union() {
        // Moldura externa
        translate([0, 0, THICK - OVERLAP])
            linear_extrude(height = FRAME_H + OVERLAP)
                difference() {
                    card_outline_inset_2d(FRAME_INSET);
                    card_outline_inset_2d(FRAME_INSET + FRAME_W);
                }

        // Logo - nivel 1: silhueta da serra
        translate([0, 0, THICK - OVERLAP])
            linear_extrude(height = LOGO_TIER1_H + OVERLAP)
                saw_blade_2d(LOGO_CX, LOGO_CY, LOGO_R, LOGO_TEETH);

        // Logo - nivel 2: anel medio
        translate([0, 0, THICK - OVERLAP])
            linear_extrude(height = LOGO_TIER2_H + OVERLAP)
                saw_ring_2d(LOGO_CX, LOGO_CY, LOGO_R);

        // Logo - nivel 3: mancal central
        translate([0, 0, THICK - OVERLAP])
            linear_extrude(height = LOGO_TIER3_H + OVERLAP)
                translate([LOGO_CX, LOGO_CY]) circle(r = LOGO_R * 0.10);

        // Texto principal
        translate([0, 0, THICK - OVERLAP])
            linear_extrude(height = TEXT_MAIN_H + OVERLAP)
                translate([TEXT_X, CARD_H - 13.0])
                    text("PLJ CARPENTRY", size = TITLE_SIZE, halign = "left", valign = "baseline",
                         font = "Liberation Sans:style=Bold");

        // Texto secundario
        translate([0, 0, THICK - OVERLAP])
            linear_extrude(height = TEXT_SECONDARY_H + OVERLAP)
                translate([TEXT_X, CARD_H - 19.2])
                    text("CAPE COD * MA", size = SUBTITLE_SIZE, halign = "left", valign = "baseline",
                         font = "Liberation Sans:style=Bold");

        // Telefone
        translate([0, 0, THICK - OVERLAP])
            linear_extrude(height = TEXT_SECONDARY_H + OVERLAP)
                translate([TEXT_X + 6.4, CARD_H - 31.7])
                    text("(508) 123-4567", size = PHONE_SIZE, halign = "left", valign = "baseline",
                         font = "Liberation Sans:style=Bold");

        // Icone de telefone simplificado (disco + fenda)
        translate([0, 0, THICK - OVERLAP])
            linear_extrude(height = TEXT_SECONDARY_H + OVERLAP)
                translate([TEXT_X + 2.0, CARD_H - 29.0]) circle(r = 1.6);

        // Divisoria vertical
        translate([0, 0, THICK - OVERLAP])
            linear_extrude(height = DIVIDER_H + OVERLAP)
                translate([DIVIDER_X - DIVIDER_W/2, 7.5]) square([DIVIDER_W, CARD_H - 15.0]);

        // SCAN HERE
        translate([0, 0, THICK - OVERLAP])
            linear_extrude(height = TEXT_SECONDARY_H + OVERLAP)
                translate([QR_X + QR_SIDE/2, QR_Y - 4.6])
                    text("SCAN HERE", size = SCAN_SIZE, halign = "center", valign = "baseline",
                         font = "Liberation Sans:style=Bold");

        // QR Code em relevo (a partir do fundo do rebaixo, com overlap para uniao solida)
        translate([0, 0, THICK - QR_POCKET_D - OVERLAP])
            for (r = [0 : QR_N - 1])
                for (c = [0 : QR_N - 1])
                    if (QR_MATRIX[r][c] == 1)
                        translate([QR_X + QR_QUIET + c * QR_MODULE,
                                    QR_Y + QR_QUIET + (QR_N - 1 - r) * QR_MODULE, 0])
                            cube([QR_MODULE, QR_MODULE, QR_BUMP_H + OVERLAP]);

        // Inlay dourado do verso (logo pequeno + texto) - preenche exatamente o bolso raso do black_base()
        linear_extrude(height = BACK_INLAY_D)
            saw_blade_2d(BACK_LOGO_CX, BACK_LOGO_CY, BACK_LOGO_R);
        linear_extrude(height = BACK_INLAY_D)
            translate([CARD_W/2, BACK_TEXT_Y, 0])
                text("PLJCARPENTRY.US", size = 4.6, halign = "center", valign = "baseline",
                     font = "Liberation Sans:style=Bold", spacing = 1.15);
    }
}

// =====================================================================
// Render final (controlado por PART)
// =====================================================================
if (PART == "front") {
    gold_details();
} else if (PART == "back") {
    black_base();
} else {
    union() {
        black_base();
        gold_details();
    }
}
