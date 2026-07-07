# Perfil de Impressão — Nozzle 0.4 mm (alternativo)

Versão alternativa para quem não possui bico 0.2 mm instalado. Baseie-se no
perfil "0.20mm Standard @BBL A1 mini" (ou impressora Bambu equivalente) e
ajuste:

| Parâmetro | Valor |
|---|---|
| Layer Height | 0.16 mm |
| Initial Layer Height | 0.20 mm |
| Line Width (Default) | 0.42 mm |
| Outer Wall Line Width | 0.40 mm |
| Inner Wall Line Width | 0.42 mm |
| Top Surface Line Width | 0.40 mm |
| Wall Loops | 4 |
| Detect Thin Walls | ON |
| Arachne Wall Generator | ON |
| Top Layers | 9 |
| Bottom Layers | 7 |
| Infill Density | 100% |
| Infill Pattern | Rectilinear |
| Top Surface Pattern | Monotonic Line |
| Outer Wall Speed | 25 mm/s |
| Inner Wall Speed | 45 mm/s |
| Top Surface Speed | 18 mm/s |
| Travel Speed | 250 mm/s |
| Ironing | ON (Top Surface Only, Flow 10%, Speed 10 mm/s, Spacing 0.10 mm) |
| Elephant Foot Compensation | 0.12 mm |
| Matte Black Nozzle Temp | 215 °C |
| Silk Gold Nozzle Temp | 220 °C |
| Bed Temp | 55 °C |
| AMS: Smart Purge | ON |
| AMS: Flush Volume | 0.55 |
| Prime Tower | OFF |

## ⚠️ Atenção — validação obrigatória com bico 0.4 mm

Com um bico de 0.4 mm, a **largura mínima de traço confiável sobe para
~0.80–0.85 mm** (2× o diâmetro do bico). Vários elementos deste cartão foram
dimensionados para o bico de 0.2 mm (traço mínimo 0.55 mm), incluindo:

- Texto secundário ("CAPE COD • MA", telefone, "SCAN HERE") — traço fino,
  pode ficar ilegível ou sumir com 0.4 mm.
- Módulo do QR Code (0.85 mm) — no limite; ainda imprimível, mas com menos
  definição de borda.
- Moldura (1.20 mm de largura) — OK com 0.4 mm.

**Recomendação:** para imprimir com bico 0.4 mm, aumente a escala dos textos
secundários em pelo menos 1.4× no arquivo `models/plj_card_complete.scad`
(variável `TEXT_SECONDARY_H`/`size` dos `text()`) antes de exportar o STL, ou
utilize preferencialmente o perfil de 0.2 mm, que é o pensado para este
design premium com detalhes finos.
