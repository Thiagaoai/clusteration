# Perfil de Impressão — Bambu Lab A1 Mini — Nozzle 0.2 mm

Perfil principal do projeto. Crie um novo perfil de processo no Bambu Studio
com base em "0.08mm High Quality @BBL A1 mini" e ajuste os campos abaixo.

## Camadas
| Parâmetro | Valor |
|---|---|
| Layer Height | 0.08 mm |
| Initial Layer Height | 0.16 mm |

## Larguras de linha
| Parâmetro | Valor |
|---|---|
| Line Width (Default) | 0.22 mm |
| Outer Wall Line Width | 0.20 mm |
| Inner Wall Line Width | 0.22 mm |
| Top Surface Line Width | 0.20 mm |

## Paredes e topo/fundo
| Parâmetro | Valor |
|---|---|
| Wall Loops | 6 |
| Detect Thin Walls | ON |
| Arachne Wall Generator | ON |
| Top Layers | 16 |
| Bottom Layers | 12 |
| Infill Density | 100% |
| Infill Pattern | Rectilinear |
| Top Surface Pattern | Monotonic Line |
| Bottom Pattern | Monotonic |
| Seam Position | Aligned Rear |

## Velocidades
| Parâmetro | Valor |
|---|---|
| Outer Wall Speed | 20 mm/s |
| Inner Wall Speed | 40 mm/s |
| Top Surface Speed | 15 mm/s |
| Small Perimeter Speed | 12 mm/s |
| Travel Speed | 250 mm/s |
| Initial Layer Speed | 15 mm/s |

## Acelerações
| Parâmetro | Valor |
|---|---|
| Outer Wall Acceleration | 600 mm/s² |
| Inner Wall Acceleration | 1800 mm/s² |
| Top Surface Acceleration | 400 mm/s² |
| Travel Acceleration | 2500 mm/s² |

## Temperaturas
| Parâmetro | Valor |
|---|---|
| Matte Black Nozzle Temp | 215 °C |
| Silk Gold Nozzle Temp | 220 °C |
| Bed Temp | 55 °C |
| Cooling | 100% após a camada 3 |

## Retração / Z-Hop
| Parâmetro | Valor |
|---|---|
| Retraction Length | 0.80 mm |
| Retraction Speed | 30 mm/s |
| Z Hop | 0.20 mm |

## Acabamento de superfície
| Parâmetro | Valor |
|---|---|
| Ironing | ON |
| Ironing Type | Top Surface Only |
| Ironing Flow | 10% |
| Ironing Speed | 10 mm/s |
| Ironing Spacing | 0.08 mm |
| Elephant Foot Compensation | 0.12 mm |

## AMS
| Parâmetro | Valor |
|---|---|
| Smart Purge | ON |
| Flush Volume | 0.55 |
| Prime Tower | OFF |

## Validação de traço mínimo (nozzle 0.2 mm)
Com bico de 0.2 mm e largura de linha externa 0.20 mm, o traço mínimo
imprimível confiável é de ~0.40 mm (2 perímetros finos) até 0.55 mm (parede
sólida sem espaços). O texto principal ("PLJ CARPENTRY") foi dimensionado
para largura de traço ≥0.55 mm — confirme no preview do slicer (modo
"Line Type") que nenhum traço aparece pontilhado ou descontínuo antes de
imprimir. Veja `makerworld/print_settings.txt` para a tabela de verificação.
