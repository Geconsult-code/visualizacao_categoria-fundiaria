# Changelog

## [1.0.0] - 2026-10
### Produto
- `Planaveg_2026_Categorias_Visualizacao.gpkg` gerado para o Brasil nas duas
  versões da VS (vs22q e vs2224q), 28 UFs, validado.

### Desempenho
- Validação de geometria feita depois de separar os multipolígonos em partes.
- Municípios, bacias e máscaras das flags recortados pela janela da UF e
  subdivididos em quadrantes (> 2.000 vértices).
- Modo em blocos (`--bloco-km`) para UFs grandes; `FORA` em blocos de 200 km.

## [0.2.0] - 2026-09-30
### Adicionado
- Flags de APP/RL/AUR separadas por categoria de imóvel (9 colunas).
- Validação do ES: conservação de área, Albers × geodésica, coerência
  classe × flag.

## [0.1.0] - 2026-09-29
### Adicionado
- `0_inventario_fontes_visualizacao.py`: diagnóstico das fontes.
- Scripts 1 a 4 (checagem, fragmentação/atribuição, validação, consolidação) e
  `viz_comum.py`.
