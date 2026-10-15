# Changelog

## [1.1.0] - 2026-10-15
### Adicionado
- Subcategorias de PROJ `GEF_Terrestre` e `Restauracao_Ecologica` (ICMBio 2026,
  `Insumos/IN_ICMBio_2026.gpkg`), na classe 4 do cômputo.
- Matriz de preenchimento (M1 a M9) aplicada na etapa 2 e validada na etapa 3
  (`3_matriz_*.csv`, `3_matriz_pecas_*.csv`); registro das imputações
  (`2_imputacoes_*.csv`).
- Município e bacia pelo polígono mais próximo onde ficavam vazios.
- Variável `PLANAVEG_C26` para usar um cômputo regerado em outra pasta.

### Alterado
- `Manguezal` deixa de ser subcategoria de PROJ e passa a tema isolado
  (token `MANG` na Sobreposicao).
- `UC` passa a ser o tema (APA, RPPN ou demais UCs); APA e RPPN continuam
  como colunas de detalhe.
- `CAR` inclui `CAR_regularizacao` e APP/RL/AUR; APP/RL/AUR_<situação>
  marca `CAR_<situação>`.
- Flags próprias de cada classe garantidas; subcategoria ou esfera ambígua
  pela fonte mais próxima.

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
