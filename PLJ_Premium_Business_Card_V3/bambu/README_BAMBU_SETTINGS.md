# PLJ Carpentry — Premium Business Card V3 — Guia Bambu Studio

## 1. Arquivos e como importar

O modelo é entregue como **dois grupos geométricos nas mesmas coordenadas** (para
impressão bicolor sem pintura manual) mais um arquivo unificado:

| Arquivo | Conteúdo | Filamento sugerido |
|---|---|---|
| `models/plj_card_back.stl`  | Base preta: corpo chanfrado, bolso do QR, textura *leather* no verso | **Bambu PLA Matte Black** |
| `models/plj_card_front.stl` | Detalhes: moldura, logo (3 níveis), textos, QR em relevo, inlay do verso | **Bambu PLA Silk Gold** |
| `models/plj_card_complete.stl` | União dos dois grupos (mesh única) | referência / preview / impressão em 1 cor |

### Passo a passo (impressão bicolor com AMS)
1. Abra o Bambu Studio → **Import** → selecione `plj_card_back.stl` **e**
   `plj_card_front.stl` juntos (import múltiplo). Como ambos foram gerados a
   partir do mesmo sistema de coordenadas, eles já chegam perfeitamente
   alinhados — **não mova nenhum dos dois objetos**.
2. No painel *Objects*, clique com o botão direito em `plj_card_back` →
   **Set filament** → Filamento 1 (Bambu PLA Matte Black).
3. Repita em `plj_card_front` → **Set filament** → Filamento 2 (Bambu PLA
   Silk Gold).
4. Carregue o perfil de impressão (`print_profile_A1Mini_02mm.md` ou
   `print_profile_04mm.md`) conforme o bico instalado.
5. Verifique em **Preview** que o corte por cores mostra preto na base e
   dourado apenas na moldura/logo/textos/QR — se aparecer misturado, confirme
   que os dois STL não foram movidos/rotacionados de forma diferente.

### Alternativa (1 STL + pintura manual)
Se preferir usar apenas `plj_card_complete.stl`, use a ferramenta **Color
Painting** do Bambu Studio (clique direito → *Paint Support/Color*) e pinte
manualmente a moldura, o logo, os textos e o QR com a cor dourada — mais
trabalho manual, mesmo resultado visual.

## 2. Orientação de impressão

Imprimir com o **verso (leather texture) apoiado na mesa** e a frente (moldura
+ logo + textos + QR) voltada para cima. O verso é quase plano (textura de
apenas 0,08–0,12 mm) e garante a melhor aderência de primeira camada; a
frente concentra todo o relevo alto (moldura +0,40 mm, QR +0,80 mm a partir do
rebaixo) e deve ficar visível/para cima.

Não é necessário suporte — todas as geometrias são auto-suportadas
(chanfros ≤45°, relevos baixos, sem balanços).

## 3. Mesa de impressão

- Use **BIQU CryoGrip Pro** ou **Smooth PEI Plate**.
- **Não usar Textured PEI** (deixaria uma textura indesejada no verso, que já
  tem textura própria em relevo controlado).

## 4. Filamento

| Papel | Filamento | Bico |
|---|---|---|
| Base | Bambu PLA Matte Black | 215 °C |
| Detalhes | Bambu PLA Silk Gold | 220 °C |
| Mesa | — | 55 °C |

Seque os filamentos abaixo de 20% de umidade antes de imprimir (PLA Silk é
higroscópico e mais sensível a stringing/perda de brilho quando úmido).

## 5. AMS

- **Smart Purge:** ON
- **Flush Volume:** 0.55
- **Prime Tower:** OFF (as trocas de cor ocorrem por objeto/altura, não em
  torre de purga — reduz desperdício de filamento em uma peça pequena)

## 6. Checklist antes de laminar

- [ ] Os dois STL (`front`/`back`) foram importados juntos e não foram
      movidos individualmente
- [ ] Filamento 1 = Matte Black no `plj_card_back`
- [ ] Filamento 2 = Silk Gold no `plj_card_front`
- [ ] Perfil de impressão do bico correto carregado (0.2 mm ou 0.4 mm)
- [ ] Mesa: Smooth PEI ou CryoGrip Pro selecionada no Bambu Studio
- [ ] 1 cartão por vez, centralizado na mesa
- [ ] Pré-visualização (Preview) confere: preto na base, dourado nos
      detalhes, QR nítido e contrastado

## 7. Validação do QR Code antes de imprimir

O QR foi gerado e **decodificado com sucesso** por um leitor independente
(`zbarimg`) apontando para `https://pljcarpentry.us` — ver
`makerworld/print_settings.txt` e o relatório de validação no resumo do
projeto. Isso garante que os *dados* do QR estão corretos; a **legibilidade
física** depende da qualidade de impressão (contraste preto/dourado sob a
luz do ambiente). Recomenda-se:

- Imprimir 1 peça de teste e escanear com 2–3 celulares diferentes antes de
  produzir em lote.
- Se a leitura falhar por baixo contraste dourado/preto sob luz direta,
  ajuste a iluminação do ambiente ou considere aumentar `QR_BUMP_H` em
  `models/plj_card_complete.scad` para acentuar a sombra dos módulos.

## 8. Ajustes finos recomendados

- **Elephant Foot Compensation 0.12 mm** já compensa o afundamento da
  primeira camada nos chanfros — confirme visualmente na primeira camada.
- **Ironing (Top Surface Only)** suaviza a moldura e os topos dos textos —
  mantenha ligado apenas nas camadas onde a cor dourada está ativa para não
  gastar tempo de mesa desnecessário na base preta.
- Caso os traços dos textos pareçam finos demais no preview do slicer,
  aumente ligeiramente o `size` dos `text()` no `.scad` (ver
  `bambu/print_profile_A1Mini_02mm.md`, seção de validação de traço).
