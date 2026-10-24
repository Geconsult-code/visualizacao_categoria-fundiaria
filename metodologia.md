# Metodologia: atributos de visualização do cômputo Planaveg 2026

## 1. Objetivo

Acrescentar ao cômputo Planaveg 2026 atributos que permitam filtrar a
visualização por categoria fundiária, instrumento de recuperação e localização,
sem alterar a hierarquia nem as áreas do cômputo.

## 2. Modelo de referência (ES, cômputo 2025)

O exemplo `Planaveg_Categorias_Visualizacao.gpkg` (Espírito Santo, 2.601
fragmentos) foi analisado antes de qualquer processamento. Estrutura identificada:

- o cômputo 2025 retalhado por município e bacia;
- flags de presença com o rótulo ou vazio (PROJ, CAR, APA, UC, TI, AS, QL,
  RPPN, APP, RL, AUR, esferas de UC, componentes de projeto);
- `Sobreposicao` = concatenação das flags fundiárias na ordem
  PROJ, CAR, APA, RPPN, UC, TI, AS, QL (reproduz 2.598 das 2.601 linhas);
- `Area_ha` planar em Albers IBGE; `computo` = total da classe.

Problemas encontrados no exemplo e **não replicados** em 2026:

| Problema no exemplo 2025 | Tratamento em 2026 |
|---|---|
| `CAR_regularizacao` e `CAR_conformidade` com conteúdos trocados | substituídos pelas três categorias de CAR de 2026 + `CAR_regularizacao` correto |
| Esferas de UC sempre marcadas em pares (cálculo invertido) | uma esfera por UC, calculada a partir do campo `esfera` do CNUC |
| 3 fragmentos ORR sem flag de projeto; 14 de "Demais instrumentos" sem PROJ | PROJ derivado sempre dos componentes |
| Campo `Ouras_Areas` | renomeado `Outras_Areas` |
| Campos `area_tnc` e `area_wit_fpnd` | eliminados |
| Geometria Z/M | saída 2D |

## 3. Decisões aprovadas

1. **Entrada:** `Reporte_Final/Planaveg_2026_Total.gpkg`, camadas
   `Reporte_Planaveg_Total_vs22q` e `_vs2224q` (605 feições cada na v1.x; 604 no cômputo v1.2.0; dissolvidas
   por hierarquia × bioma × UF × categoria). Mantêm-se hierarquia, tier e
   categoria de 2026.
2. **Fragmentação:** UF (campo do cômputo, inclui `FORA`), município
   (`IBGE_Limite_Municipios.gpkg`, malha 2020) e bacia
   (`IBGE_Divisao_Hidrografica.gpkg`, camada `micro_RH`, com os nomes de micro,
   meso e macro região hidrográfica).
3. **Flags por identity:** cada fragmento é dividido pela união de cada fonte;
   a parte dentro recebe o rótulo, a parte fora mantém vazio. A área é sempre
   conservada.
4. **Área:** planar em Albers IBGE (SRS do exemplo 2025), calculada depois de
   todos os cruzamentos. Por ser projeção equivalente, difere da geodésica GRS80
   em menos de 0,03% por classe.
5. **Slivers:** fragmentos < 1 m² são descartados, e a área descartada é
   registrada por classe no log.
6. **Dissolve final:** por combinação completa de atributos dentro de cada UF.
7. **`computo`:** soma nacional de `Area_ha` por `hierarquia_planaveg`,
   calculada na consolidação.

## 4. Fontes das flags

Regra geral: as flags usam as camadas **completas** (não as versões `IN_`/`P1_`
cortadas pela VS), exceto APP/RL/AUR, que seguem a regra do cômputo para os CARs.

| Flag | Fonte | Filtro |
|---|---|---|
| `CAR_Habilitado` | `Analise_Territorial_CAR-INCRA_dissolvido/CAR_Brasil_Maio26_Habilitado_Planaveg_dissolvido_UF.gpkg` | — |
| `CAR_Analisado` | `..._Maio26_Selecionado_Analisado_dissolvido_UF.gpkg` | — |
| `CAR_Nao_Analisado` | `..._Maio26_Selecionado_Não_Analisado_dissolvido_UF.gpkg` | — |
| `CAR_regularizacao` | `Tier3_CAR_Regularizacao/P2_CAR_Regularizacao_Junho26.gpkg` (`P2_CAR_REGULARIZACAO_poligonos`) | `elegivel_computo = 1` |
| `APP_<cat>`, `RL_<cat>`, `AUR_<cat>` | `Tier9_APP`, `Tier11_RL`, `Tier10_AUR` / `P1_<tema>_CAR_Maio2026.gpkg` (camada da versão da VS) | `categoria` = Habilitados, Analisados ou Nao_Analisados |
| `Licenciamento_Ambiental`, `Reparacao_Danos`, `Area_Embargada`, `Outras_Areas` | `Tier1_Recooperar/P2_Recooperar_2026.gpkg` (`P2_RECOOPERAR_poligonos`) | `elegivel_computo = 1` e `categoria` do componente (regras D2–D4 do cômputo) |
| `Embargo_PANGIA` | `Tier4_Outros_Projetos/P2_Outros_Projetos_PANGIA_20260920.gpkg` (`P2_OUTROS_PROJETOS_poligonos`) | polígonos completos |
| `ORR` | `Tier5_OR/P2_OR_2026.gpkg` (`P2_OR_poligonos`) | `elegivel_computo = 1`; só OR 2026 |
| `Manguezal` | `Pro-Manguezal_IBAMA20260508.gpkg` | camada original |
| `APA` / `RPPN` / `UC` | `Unidades_Conservacao_CNUC20260507.gpkg` | `categoria` = APA / RPPN / demais categorias |
| `UC_federal`, `UC_estadual`, `UC_municipal` | idem | `esfera` (todas as categorias de UC) |
| `TI` | `Terras_Indigenas_FUNAI20260507.gpkg` | `fase_ti` em Regularizada, Homologada, Declarada, Delimitada (as 4 fases do cômputo) |
| `AS_` | `Assentamentos_Rurais_INCRA20260610.gpkg` | — |
| `QL` | `Territorios_Quilombolas_INCRA20260610.gpkg` | — |

Campos derivados:

- `CAR` = qualquer uma das três categorias de CAR.
- `PROJ` = qualquer um entre Licenciamento, Reparação, Embargo, Outras Áreas,
  Embargo PANGIA, ORR e Manguezal.
- `Sobreposicao` = tokens PROJ, CAR, APA, RPPN, UC, TI, AS, QL, nessa ordem.

Na checagem das fontes (script 1), o filtro `elegivel_computo = 1` não excluiu
nenhuma feição: as camadas P2 já contêm só polígonos elegíveis.

## 5. Algoritmo (script 2)

Para cada versão da VS e cada UF:

1. Lê as feições do `Total` com `uf = '<UF>'`, reprojeta para Albers e separa em
   polígonos simples. A separação acontece **antes** da validação de geometria,
   porque validar multipolígonos gigantes inteiros é muito lento.
2. Opcionalmente divide as peças em blocos pela posição do ponto representativo
   (`--bloco-km`). A peça nunca é cortada pelo bloco; o bloco só define a janela
   de leitura das fontes.
3. Para cada bloco, lê municípios, bacias e cada fonte só na janela (filtro bbox
   do pyogrio) e:
   - recorta as camadas pela janela e subdivide recursivamente em quadrantes
     as partes com mais de 2.000 vértices (não altera a união, só torna os
     recortes locais baratos);
   - **município e bacia:** peças cobertas por um único polígono recebem os
     atributos diretamente; peças na fronteira são cortadas sequencialmente,
     sem duplicar área se houver sobreposição entre polígonos da fonte;
   - **flags:** índice espacial (STRtree) entre peças e partes da fonte; peças
     cobertas recebem o rótulo; peças parciais são divididas em dentro e fora
     da união local das partes candidatas.
4. Descarta slivers < 1 m², deriva `CAR`, `PROJ` e `Sobreposicao`, dissolve por
   combinação de atributos e calcula `Area_ha`.

Operações geométricas usam fallback em caso de erro de topologia do GEOS:
`make_valid` e, em último caso, precisão de 1 cm (`grid_size`).

## 6. Validação (script 3)

Por UF e versão:

- **A. Conservação:** área de entrada (Albers) = área de saída + slivers, por
  classe (tolerância 0,01%).
- **B. Albers × geodésica:** comparação com o `Area_ha` geodésico do cômputo.
- **C. Geometria:** inválidas, vazias e menor feição.
- **D. Coerência:** percentual da área de cada classe com a sua flag própria
  (ex.: classe TI com flag TI).
- **E. Tabela classe × flag** (ha) para conferência visual.

## 7. Histórico de execução

- **Teste ES (30/09/2026):** 1.510 feições, 44.813,0 ha; conservação OK;
  100% de flag própria em todas as 11 classes; vs22q = vs2224q (ES sem VS 2024).
- **Desempenho:** a primeira tentativa no MT levou 78 min só na leitura e mais
  de 2h30 em municípios e bacias. Com a validação após a separação, a
  subdivisão das camadas e o modo em blocos de 200 km, o MT inteiro rodou em
  57 min.
- **Rodada nacional (outubro/2026):** 28 UFs nas duas versões, sem falhas.
  Conservação máxima 0,001 ha; slivers ~14 ha; Albers × geodésica entre
  −0,015% e +0,03% nas classes > 1 ha; flag própria ≥ 99,96%.

### Totais por classe (ha)

| Classe | vs22q | vs2224q |
|---|---:|---:|
| Recooperar (IBAMA) | 107.092,9 | 107.092,9 |
| SICAR - Analisado, em regularização ambiental | 33.519,3 | 33.519,3 |
| Outros projetos (embargos PANGIA × VS) | 356.833,0 | 348.571,2 |
| Observatório da Restauração | 187.268,6 | 187.286,7 |
| VS em Terras Indígenas | 940.580,3 | 978.302,0 |
| VS em Unidades de Conservação | 1.337.569,8 | 1.340.832,3 |
| VS em manguezais (Pró-Manguezal) | 16.436,9 | 16.564,4 |
| VS em APP - Habilitados | 338.257,3 | 350.521,3 |
| VS em APP - Analisados | 141.230,7 | 142.856,8 |
| VS em APP - Não Analisados | 741.618,0 | 748.169,1 |
| VS em AUR - Habilitados | 16.372,5 | 17.502,2 |
| VS em AUR - Analisados | 5.661,5 | 6.129,5 |
| VS em AUR - Não Analisados | 35.058,5 | 36.321,6 |
| VS em RL - Habilitados | 1.164.051,2 | 1.203.690,8 |
| VS em RL - Analisados | 639.238,7 | 658.855,2 |
| VS em RL - Não Analisados | 2.527.946,9 | 2.626.897,4 |
| **Total** | **8.588.736,1** | **8.803.112,7** |

## 8. Esquema v2.0.0 (23 e 24/10/2026)

As seções 3 a 7 descrevem o esquema v1.x (flags de componente). Desde a v2.0.0 a visualização segue a planilha
`Planaveg_2026_total_VS2224_mapeamento_atributos_visualizacao.xlsx` e as respostas de 23/10/2026
(`Instrucoes_Visualizacao.docx`), sobre o cômputo v1.2.0 (sem os embargos PANGIA; FUNBIO na classe 4).

### 8.1 Decisões

1. **Flags do próprio tier:** `CAR` só nos tiers 3, 9, 10 e 11; `PROJ` só nos 1, 2, 4 e 5; `UC` só no 7; `TI` só no 6;
   `Manguezal` só no 8. `APA`, `RPPN`, `AS` (era `AS_`) e `QL` continuam marcando a sobreposição em qualquer tier.
2. **Sobreposicao** mantém a regra anterior (sobreposição em qualquer tier), com os mesmos tokens.
3. **Campos novos:** `Nome_Abreviado`, `Nome_Detalhado`, `CAR_Condicao` (era `categoria`), `PROJ_Categoria`, `UC_Nome`,
   `UC_Manejo`, `UC_Esfera` e `TI_Nome`, cada um só nos tiers indicados.
4. **Eliminados:** `computo`, `categoria`, `CAR_Habilitado/Analisado/Nao_Analisado`, `CAR_regularizacao`,
   `APP/RL/AUR_<categoria>`, `Licenciamento_Ambiental`, `Reparacao_Danos`, `Area_Embargada`, `Outras_Areas`, `MonitoRAD`,
   `Embargo_PANGIA`, `GEF_Terrestre`, `Restauracao_Ecologica`, `ORR`, `UC_federal`, `UC_estadual`, `UC_municipal`.
5. **Hierarquia:** nomes novos; no tier 4, um nome por origem do projeto (ICMBio GEF Terrestre, ICMBio Restauração
   Ecológica, FUNBIO), a partir dos polígonos líquidos da classe 4 (`P2_OUTROS_PROJETOS_<versão>`, campo `fonte`).
6. **Tier 1:** `Nome_Abreviado`, `Nome_Detalhado` e `PROJ_Categoria` pela categoria do projeto Recooperar (licenciamento,
   reparação, embargo, outras), a partir dos polígonos líquidos da classe 1 (`P2_RECOOPERAR`). Tier 2 (MonitoRAD): os mesmos
   nomes do embargo do tier 1. Tiers 4 e 5: "Outros Projetos" e `PROJ_Categoria` = Outras_Áreas.
7. **UC_Nome e TI_Nome:** todas as UCs (CNUC, só `limite = 'uc'`) ou TIs (FUNAI, as 4 fases do cômputo) que contêm o trecho,
   separadas por "; "; o trecho é dividido onde o conjunto de UCs/TIs muda. `UC_Manejo` e `UC_Esfera` listam os valores
   distintos na mesma ordem dos nomes.
8. **Grafia:** textos da planilha com a ortografia corrigida ("Permanente", "seguinte", "regularização", "Lei nº");
   `PROJ_Categoria` acentuado (Reparação_Danos, Área_Embargada, Outras_Áreas).
9. **Nomes de TI:** o arquivo da FUNAI de 07/05/2026 tem a acentuação corrompida em cerca de 190 nomes e 3 nomes vazios;
   a tabela `dados/TI_nomes_corrigidos_FUNAI20260507.csv` (revisada pelo usuário em 24/10/2026) substitui esses nomes
   pelo `terrai_cod`.

### 8.2 Algoritmo (mudanças no script 2)

- As fontes do identity passaram a ser campos internos (prefixo `_`): `_CAR` (CAR dissolvido das três categorias e CAR em
  regularização), `_PROJ` (Recooperar, MonitoRAD, ICMBio, FUNBIO e ORR), `_rec_cat` (categoria do Recooperar), `_t4_fonte`
  (origem do tier 4), `_MANG`, `_UC_outras` e `_TI`; servem à `Sobreposicao` e às colunas de saída e não são gravados.
  Saíram as fontes APP/RL/AUR por categoria, as mais pesadas: o Brasil roda em cerca de 4 h (antes, 10 h ou mais).
- Rótulos individuais (`rotular`): para as peças do tier 7 (e do 6), índice espacial com as partes de cada UC (TI); peças
  cobertas recebem os ids diretamente, as demais são divididas pela sobreposição com cada UC parcial. Peças de borda sem
  UC/TI recebem a mais próxima.
- No tier 7, `APA`, `RPPN` e o token UC são marcados também pelos rótulos, para ficarem coerentes com `UC_Nome`.

### 8.3 Validação (script 3)

Matriz M1 a M8 (ver README), conservação de área por tier e categoria do CAR, Albers x geodésica e geometrias.
Rodada nacional: zero violações em todas as regras, conservação máxima de 0,001 ha, slivers de 13,7 ha (vs22q) e
14,0 ha (vs2224q), Albers x geodésica entre -0,015% e +0,004%.

### 8.4 Totais por classe (ha, cômputo v1.2.0)

| Tier | Classe | vs22q | vs2224q |
|---:|---|---:|---:|
| 1 | Projetos do Programa Recooperar | 107.092,9 | 107.092,9 |
| 2 | Projetos do Programa MonitoRAD | 286.250,0 | 286.250,0 |
| 3 | Projetos de Regularização Ambiental em Imóvel Rural - CAR | 33.519,3 | 33.519,3 |
| 4 | Outros Projetos ICMBio_GEF Terrestre | 4.588,5 | 4.588,5 |
| 4 | Outros Projetos ICMBio_Restauração Ecológica | 32.707,1 | 32.707,1 |
| 4 | Outros Projetos FUNBIO | 10.135,8 | 10.135,8 |
| 5 | Projetos do Observatório da Restauração | 163.651,9 | 163.651,9 |
| 6 | Vegetação Secundária em Territórios Indígenas | 953.415,1 | 991.600,7 |
| 7 | Vegetação Secundária em Unidades de Conservação | 1.361.981,0 | 1.365.439,0 |
| 8 | Vegetação Secundária em Área de Manguezais | 16.436,2 | 16.563,7 |
| 9 | APP - Habilitados / Analisados / Não Analisados | 340.416,0 / 141.882,6 / 743.520,8 | 352.582,4 / 143.509,6 / 750.450,6 |
| 10 | AUR - Habilitados / Analisados / Não Analisados | 16.372,5 / 5.706,8 / 35.316,4 | 17.535,4 / 6.171,8 / 36.504,3 |
| 11 | RL - Habilitados / Analisados / Não Analisados | 1.173.043,1 / 644.235,5 / 2.539.767,5 | 1.213.160,0 / 663.388,7 / 2.639.424,8 |
| | **Total** | **8.610.039,0** | **8.834.276,3** |
