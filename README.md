# visualizacao_categoria-fundiaria

Atributos de visualização (filtros por categoria fundiária, instrumento e
localização) sobre o **cômputo Planaveg 2026** das áreas em processo de
recuperação da vegetação nativa.

Este repositório é a última etapa da cadeia de processamento do PLANAVEG 2026:

| # | Repositório | Produto |
|---|---|---|
| 1 | [analise_conformidade_sicar-incra](https://github.com/Geconsult-code/analise_conformidade_sicar-incra) | Imóveis do CAR selecionados (Habilitados, Analisados, Não Analisados) e recortes de APP/RL/AUR |
| 2 | [cruzamento_vegetacao-secundaria](https://github.com/Geconsult-code/cruzamento_vegetacao-secundaria) | Cruzamento da vegetação secundária (VS) qualificada com APP/RL/AUR |
| 3 | [computo_hierarquia-planaveg](https://github.com/Geconsult-code/computo_hierarquia-planaveg) | Cômputo 2026 com a hierarquia de sobreposições (`Planaveg_2026_Total.gpkg`) |
| 4 | **visualizacao_categoria-fundiaria** (este) | Cômputo 2026 fragmentado e com atributos de filtro (`Planaveg_2026_Categorias_Visualizacao.gpkg`) |

O modelo de atributos é o exemplo do Espírito Santo gerado sobre o cômputo 2025
(`Planaveg_2025_Categorias_Fundiarias/Planaveg_Categorias_Visualizacao.gpkg`),
adaptado às camadas novas ou alteradas de 2026. A metodologia completa está em
[metodologia.md](metodologia.md).

## Produto (v2.0.0, outubro/2026)

`GEOPACKAGE/Computo_Planaveg_2026/Visualizacao/Planaveg_2026_Categorias_Visualizacao.gpkg`, sobre o cômputo
v1.2.0 (sem os embargos PANGIA, com a FUNBIO na classe 4):

| Camada | Versão da vegetação secundária | Feições | Área total |
|---|---|---:|---:|
| `Planaveg_2026_Visualizacao_vs22q` | VS 2022 qualificada | 50.361 | 8.610.039 ha |
| `Planaveg_2026_Visualizacao_vs2224q` | VS 2022-2024 qualificada | 50.515 | 8.834.276 ha |

Cada feição é um fragmento do cômputo com uma combinação única de classe, localização e atributos.
Sistema de referência: Albers IBGE / SIRGAS 2000, geometria 2D. O esquema segue a planilha
`Planaveg_2026_total_VS2224_mapeamento_atributos_visualizacao.xlsx` e as respostas de 23/10/2026
(detalhes em [metodologia.md](metodologia.md), seção 8).

### Atributos

| Campo | Conteúdo | Preenchido em |
|---|---|---|
| `hierarquia_planaveg` | nome da classe (ex.: "Projetos do Programa Recooperar"); na classe 4, um nome por origem: "Outros Projetos ICMBio_GEF Terrestre", "Outros Projetos ICMBio_Restauração Ecológica", "Outros Projetos FUNBIO" | todas |
| `tier` | ordem da classe na hierarquia (1 a 11) | todas |
| `Nome_Abreviado`, `Nome_Detalhado` | nome curto e texto de tool tip da classe; na classe 1, pela categoria do projeto Recooperar | todas |
| `Area_ha` | área do fragmento (Albers, ha) | todas |
| `UF`, `Bioma`, `Municipio`, `cod_municipio`, `Bacia`, `Bacia_meso`, `Regiao_Hidrografica` | localização (UF e bioma do cômputo; município IBGE 2020; micro, meso e macro região hidrográfica) | todas |
| `CAR`, `CAR_Condicao` | "CAR" e a condição do imóvel (texto da planilha) | tiers 3, 9, 10, 11 |
| `PROJ`, `PROJ_Categoria` | "PROJ" e Licenciamento_Ambiental, Reparação_Danos, Área_Embargada ou Outras_Áreas (tier 1 pela categoria do Recooperar; tier 2 Área_Embargada; tiers 4 e 5 Outras_Áreas) | tiers 1, 2, 4, 5 |
| `Manguezal` | "Pró-Manguezal" | tier 8 |
| `APA`, `RPPN` | sobreposição com APA / RPPN do CNUC | qualquer tier |
| `UC`, `UC_Nome`, `UC_Manejo`, `UC_Esfera` | "UC" e, de **todas** as UCs que contêm o trecho, separados por "; ": nome, manejo (Proteção_Integral / Uso_Sustentável) e esfera (UC_Federal / UC_Estadual / UC_Municipal), na ordem: proteção integral, fora da APA, federal > estadual > municipal, mais antiga | tier 7 |
| `TI`, `TI_Nome` | "TI" e o nome de todas as TIs que contêm o trecho ("; ") | tier 6 |
| `AS`, `QL` | sobreposição com assentamento / território quilombola do INCRA | qualquer tier |
| `Sobreposicao` | concatenação de PROJ, CAR, APA, RPPN, UC, MANG, TI, AS, QL pela sobreposição em **qualquer** tier (o token UC só para UCs que não são APA/RPPN) | todas |

Os campos de cada tier ficam vazios nos demais (por exemplo, uma APP dentro de uma UC tem `UC` vazio, mas
`Sobreposicao` contém UC ou APA). Exemplos de filtro: `"UC_Nome" LIKE '%PARQUE NACIONAL DO ITATIAIA%'`,
`"TI_Nome" LIKE '%Évare I%'`, `"PROJ_Categoria" = 'Área_Embargada'`, `"Sobreposicao" LIKE '%TI%' AND "tier" = 11`.

Os nomes de TI vêm do `Terras_Indigenas_FUNAI20260507.gpkg`, que tem a acentuação corrompida em cerca de 190 nomes
(e 3 vazios); esses nomes são substituídos pela tabela corrigida `dados/TI_nomes_corrigidos_FUNAI20260507.csv`
(por `terrai_cod`, 194 TIs, revisada pelo usuário em 24/10/2026).

### Matriz de preenchimento (v2.0.0)

Conferida na etapa 3 (`_logs/3_matriz_*.csv`; meta: zero violações em todas):

| Regra | Conteúdo |
|---|---|
| M1 | Hierarquia, nomes e localização sempre preenchidos; município e bacia vazios (litoral, `FORA`) recebem o polígono mais próximo |
| M2 | `CAR` e `CAR_Condicao` preenchidos nos tiers 3, 9, 10 e 11 e vazios nos demais |
| M3 | `PROJ` e `PROJ_Categoria` preenchidos nos tiers 1, 2, 4 e 5 e vazios nos demais |
| M4 | `UC`, `UC_Nome`, `UC_Manejo` e `UC_Esfera` preenchidos no tier 7 e vazios nos demais |
| M5 | `TI` e `TI_Nome` preenchidos no tier 6 e vazios nos demais |
| M6 | `Manguezal` preenchido no tier 8 e vazio nos demais |
| M7 | Textos coerentes com o tier (hierarquia, nomes, `CAR_Condicao`, `PROJ_Categoria` na lista da planilha) |
| M8 | `Sobreposicao` preenchida e com o token do próprio tier (PROJ, CAR, UC/APA/RPPN, TI, MANG) |

Quando a peça está numa classe mas escapou do identity na borda (diferença de precisão), o token próprio é
garantido pela classe; a categoria do Recooperar (tier 1), a origem do tier 4 e o nome da UC (tier 7) ou TI (tier 6)
vêm da fonte mais próxima. Tudo isso fica em `_logs/2_imputacoes_<versão>_<UF>.csv` (peças, área e distância máxima;
no Brasil, cerca de 500 ha nas UCs e 50 ha nas TIs, a menos de 16 m).

## Dados: restaurar o backup

Os dados de entrada e os intermediários que este repositório lê estão no backup do projeto
(`F:\BKP_PLANAVEG`, organizado e documentado no repositório
[`backup_planaveg_2026`](https://github.com/Geconsult-code/backup_planaveg_2026)). Para rodar
os scripts em outro computador ou em outra pasta, restaure só o que este repositório usa
(cerca de 20 GB descompactados) e aponte os scripts para a pasta restaurada:

```powershell
git clone https://github.com/Geconsult-code/backup_planaveg_2026
cd backup_planaveg_2026
# simulação: mostra o volume por pasta e o espaço necessário
python restaurar_backup.py --backup F:\BKP_PLANAVEG --destino D:\PLANAVEG_DADOS --repo visualizacao
# restauração (pode ser interrompida e retomada)
python restaurar_backup.py --backup F:\BKP_PLANAVEG --destino D:\PLANAVEG_DADOS --repo visualizacao --executar
# uma vez só; abra um terminal novo depois
setx PLANAVEG_GEO "D:\PLANAVEG_DADOS"
```

Para apontar só o cômputo para outra pasta, apenas no terminal atual (PowerShell; no `cmd` use
`set PLANAVEG_C26=...`):

```powershell
$env:PLANAVEG_C26 = "D:\PLANAVEG_TEMP\Computo_Planaveg_2026"
```

O `viz_comum.py` lê `PLANAVEG_GEO`; nenhum script precisa ser editado. Se o cômputo foi
regerado em outra pasta, `PLANAVEG_C26` aponta para a sua `Computo_Planaveg_2026` (a saída
`Visualizacao` vai para lá); o CAR dissolvido por UF é procurado em `PLANAVEG_GEO` e, se não
estiver lá, ao lado dessa pasta. A restauração inclui o
`Planaveg_2026_Total` do cômputo, que é a entrada desta etapa.

Sem a variável, os scripts usam a pasta original no Dropbox (`GEODATABASE\GEOPACKAGE`), que hoje
guarda só uma cópia reduzida dos dados. Detalhes, opções e o inventário completo do backup
(`_manifesto_backup.csv`) estão no README do `backup_planaveg_2026`.

## Requisitos

- Ambiente conda `geo` (conda-forge): Python ≥ 3.10, GeoPandas ≥ 1.0,
  Shapely ≥ 2.0, pyogrio, pyproj, pandas, numpy.
- Dados em `C:\Users\User\Dropbox\#CONSULTANCY\PLANAVEG\GEODATABASE\GEOPACKAGE`
  (caminho definido em `viz_comum.py`; pode ser trocado pela variável de ambiente
  `PLANAVEG_GEO`). Os dados não ficam no repositório.

```powershell
conda activate geo
cd C:\Users\User\OneDrive\Documentos\GitHub\visualizacao_categoria-fundiaria
```

## Estrutura

```
visualizacao_categoria-fundiaria/
├── viz_comum.py                          # configuração, fontes das flags e funções geométricas
├── 0_inventario_fontes_visualizacao.py   # diagnóstico: lista camadas, campos e valores das fontes
├── 1_checar_fontes.py                    # confere arquivos, camadas, filtros e contagens
├── 2_fragmentar_e_atribuir.py            # processamento por UF e versão da VS
├── 3_validar.py                          # validação por UF (área, geometria, coerência)
├── 4_consolidar_brasil.py                # junta as UFs (área nacional por classe no log 4_area_por_classe_*.csv)
├── dados/TI_nomes_corrigidos_FUNAI20260507.csv   # nomes de TI corrigidos (terrai_cod -> terrai_nom)
├── metodologia.md
├── CHANGELOG.md
└── README.md
```

## Execução

```powershell
python 1_checar_fontes.py                           # deve terminar com "0 problema(s)"
python 2_fragmentar_e_atribuir.py --uf ES           # teste numa UF pequena
python 3_validar.py --uf ES

# Brasil: MT e PA em blocos de 200 km (~1h30), demais UFs (~2h45), validação e consolidação
python 2_fragmentar_e_atribuir.py --uf MT PA --bloco-km 200
python 2_fragmentar_e_atribuir.py --uf AC AL AM AP BA CE DF ES FORA GO MA MG MS PB PE PI PR RJ RN RO RR RS SC SE SP TO
python 3_validar.py --todas
python 4_consolidar_brasil.py          # recusa se o Brasil já existir: renomeie o arquivo anterior antes
```

Opções do script 2:

| Opção | Efeito |
|---|---|
| `--uf XX YY` / `--todas` | UFs a processar (`--todas` inclui a UF `FORA`) |
| `--versao vs22q vs2224q` | versões da VS (padrão: as duas) |
| `--bloco-km N` | processa a UF em blocos de N km: menos memória por etapa e progresso visível; a UF `FORA` usa 200 km automaticamente |
| `--sobrescrever` | refaz UFs já gravadas (por padrão são puladas, o que permite interromper e retomar) |

Saídas intermediárias:

- `Visualizacao/_por_uf/Visualizacao_<versao>_<UF>.gpkg`: uma UF por arquivo.
- `Visualizacao/_logs/`: checagem das fontes (`1_`), áreas de entrada e slivers
  por UF e imputações (`2_`), validação, tabela classe × flag e matriz (`3_`), área nacional por classe (`4_`).

## Validação (rodada nacional v2.0.0, 23 e 24/10/2026)

28 UFs (27 + `FORA`) nas duas versões, sem falhas; matriz M1 a M8 com zero violações.

| Teste | Resultado |
|---|---|
| Conservação de área por classe (entrada = saída + slivers) | diferença máxima de 0,001 ha |
| Slivers descartados (< 1 m²) | 13,7 ha (vs22q) e 14,0 ha (vs2224q) |
| Albers × geodésica GRS80 (classes > 1 ha por UF) | entre −0,015% e +0,004% |
| Geometrias inválidas ou vazias | 0 |
| Área de cada classe sem violação da matriz | 100% em todas as classes e UFs |

Nas UFs sem VS 2024 qualificada (AL, CE, ES, PB, PE, RJ, RN, RS, SC, SE) as duas
versões são idênticas.

## Limitações conhecidas

- O token CAR da `Sobreposicao` vem do CAR dissolvido por UF (Maio/2026) e do CAR em regularização; nos tiers 9 a 11
  ele é garantido pela classe (cerca de 29 mil ha de APP/AUR/RL ficam fora do CAR dissolvido, por diferença entre as
  bases do cruzamento e a dissolvida).
- O CAR em regularização (tier 3) só existe em AC, MT, PB, RJ e SP (cobertura da fonte).
- UC: só o limite da UC (`limite = 'uc'` no CNUC), sem a zona de amortecimento, como no cômputo.
- A malha municipal é a do IBGE 2020; as bacias são a divisão hidrográfica
  nacional do IBGE e não reproduzem as bacias estaduais usadas no exemplo ES 2025.
