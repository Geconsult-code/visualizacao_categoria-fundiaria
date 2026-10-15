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
[docs/metodologia.md](docs/metodologia.md).

## Produto

`GEOPACKAGE/Computo_Planaveg_2026/Visualizacao/Planaveg_2026_Categorias_Visualizacao.gpkg`

| Camada | Versão da vegetação secundária | Área total |
|---|---|---|
| `Planaveg_2026_Visualizacao_vs22q` | VS 2022 qualificada | 8.588.736 ha |
| `Planaveg_2026_Visualizacao_vs2224q` | VS 2022-2024 qualificada | 8.803.113 ha |

Cada feição é um fragmento do cômputo com uma combinação única de classe,
localização e flags. Sistema de referência: Albers IBGE / SIRGAS 2000 (o mesmo do
exemplo 2025), geometria 2D.

### Atributos

| Grupo | Campos |
|---|---|
| Classe do cômputo | `hierarquia_planaveg`, `tier`, `categoria`, `computo` (total nacional da classe, ha), `Area_ha` (área do fragmento, ha) |
| Localização | `UF`, `Bioma`, `Municipio`, `cod_municipio`, `Bacia` (micro RH), `Bacia_meso`, `Regiao_Hidrografica` (macro RH) |
| CAR | `CAR` (tema), `CAR_Habilitado`, `CAR_Analisado`, `CAR_Nao_Analisado`, `CAR_regularizacao` (situação) |
| APP / RL / AUR | `APP_Habilitado`, `APP_Analisado`, `APP_Nao_Analisado`, `RL_*`, `AUR_*` (mesmas três categorias) |
| Projetos | `PROJ` (tema), `Licenciamento_Ambiental`, `Reparacao_Danos`, `Area_Embargada`, `Outras_Areas`, `Embargo_PANGIA`, `GEF_Terrestre`, `Restauracao_Ecologica`, `ORR` (subcategorias) |
| Manguezal | `Manguezal` (tema isolado, Pró-Manguezal) |
| Unidades de conservação | `APA`, `RPPN` (subcategorias e detalhe), `UC` (tema), `UC_federal`, `UC_estadual`, `UC_municipal` (esfera) |
| Territórios | `TI`, `AS_`, `QL` |
| Síntese | `Sobreposicao` (concatenação de PROJ, CAR, APA, RPPN, UC, MANG, TI, AS, QL; o token UC só aparece para UCs que não são APA/RPPN) |

Cada flag contém o rótulo (ex.: `"TI"`, `"Habilitado"`, `"Federal"`) quando o
fragmento se sobrepõe à fonte, ou texto vazio quando não se sobrepõe. Exemplos de
filtro: `"Sobreposicao" = 'PROJCAR'`, `"UF" = 'MT' AND "TI" <> ''`,
`"APP_Nao_Analisado" <> '' AND "Bacia_meso" = '...'`.

### Matriz de preenchimento

Regras aplicadas na etapa 2 e conferidas na etapa 3 (`_logs/3_matriz_*.csv`; meta: zero
violações em todas):

| Regra | Conteúdo |
|---|---|
| M1 | Hierarquia e localização sempre preenchidas; município e bacia vazios (litoral, `FORA`) recebem o polígono mais próximo |
| M2 | `categoria` preenchida só nas classes do CAR (APP, AUR, RL) |
| M3 | Toda peça tem pelo menos um tema: `CAR`, `PROJ`, `UC`, `TI` ou `Manguezal` |
| M4 | `CAR` exige situação: `CAR_Habilitado`, `CAR_Analisado`, `CAR_Nao_Analisado` ou `CAR_regularizacao` |
| M5 | `APP/RL/AUR_<situação>` implica `CAR_<situação>` (a sobreposição real de situações do SICAR é mantida) |
| M6 | `PROJ` exige subcategoria (Recooperar, `Embargo_PANGIA`, `GEF_Terrestre`, `Restauracao_Ecologica`, `ORR`) |
| M7 | `UC` exige esfera; `APA` e `RPPN` implicam `UC` |
| M8 | Flags próprias da classe: 1 Recooperar; 3 `CAR_regularizacao`; 4 PANGIA/GEF/Restauração; 5 `ORR`; 6 `TI`; 7 `UC` + esfera; 8 `Manguezal`; 9-11 `<tema>_<situação>` + `CAR_<situação>` |
| M9 | `Sobreposicao` sempre preenchida |

Quando a peça está numa classe mas escapou do identity (borda, diferença de precisão), a flag
própria é marcada pela classe. Onde a subcategoria é ambígua (classes 1, 4 e 7, e a esfera da
UC) vale a fonte mais próxima. Tudo o que foi preenchido assim fica em
`_logs/2_imputacoes_<versão>_<UF>.csv`, com número de peças, área e distância máxima.

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
├── 4_consolidar_brasil.py                # junta as UFs e preenche o computo nacional
├── docs/metodologia.md
├── CHANGELOG.md
└── README.md
```

## Execução

```powershell
python 1_checar_fontes.py                           # deve terminar com "0 problema(s)"
python 2_fragmentar_e_atribuir.py --uf ES           # teste numa UF pequena
python 3_validar.py --uf ES

# Brasil (UFs grandes em blocos de 200 km)
python 2_fragmentar_e_atribuir.py --uf MT PA MG BA --versao vs22q --bloco-km 200
python 2_fragmentar_e_atribuir.py --todas --versao vs22q
python 2_fragmentar_e_atribuir.py --uf MT PA MG BA --versao vs2224q --bloco-km 200
python 2_fragmentar_e_atribuir.py --todas --versao vs2224q
python 3_validar.py --todas
python 4_consolidar_brasil.py
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
  por UF (`2_`), validação e tabela classe × flag (`3_`), computo nacional (`4_`).

## Validação (rodada nacional, outubro/2026)

28 UFs (27 + `FORA`) nas duas versões, sem falhas.

| Teste | Resultado |
|---|---|
| Conservação de área por classe (entrada = saída + slivers) | diferença máxima de 0,001 ha |
| Slivers descartados (< 1 m²) | ~14 ha no Brasil |
| Albers × geodésica GRS80 (classes > 1 ha) | entre −0,015% e +0,03%; total nacional +0,0004% |
| Geometrias inválidas ou vazias | 0 |
| Área de cada classe com a flag própria | ≥ 99,96% em todas as classes e UFs |

Nas UFs sem VS 2024 qualificada (AL, CE, ES, PB, PE, RJ, RN, RS, SC, SE) as duas
versões são idênticas.

## Limitações conhecidas

- As flags de APP, RL e AUR vêm dos recortes do cômputo, que só existem onde há
  VS. Classes que entram pelo polígono inteiro (Recooperar, ORR) não recebem
  essas flags fora da VS.
- `CAR_regularizacao` só existe em AC, MT, PB, RJ e SP (cobertura da fonte).
- A malha municipal é a do IBGE 2020; as bacias são a divisão hidrográfica
  nacional do IBGE e não reproduzem as bacias estaduais usadas no exemplo ES 2025.
