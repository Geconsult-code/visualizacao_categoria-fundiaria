# visualizacao_categoria-fundiaria

Atributos de visualização (filtros) sobre o cômputo Planaveg 2026, seguindo o
modelo do exemplo ES 2025 (`Planaveg_Categorias_Visualizacao.gpkg`).

## Execução (env `geo`, a partir da raiz deste repo)

```
python 0_inventario_fontes_visualizacao.py  # diagnóstico das fontes (opcional)
python 1_checar_fontes.py                    # confere fontes, camadas e filtros
python 2_fragmentar_e_atribuir.py --uf ES    # teste
python 3_validar.py --uf ES
python 2_fragmentar_e_atribuir.py --todas    # Brasil (inclui FORA)
python 3_validar.py --todas
python 4_consolidar_brasil.py
```

Os dados não ficam no repo: entradas e saídas estão em
`Dropbox\#CONSULTANCY\PLANAVEG\GEODATABASE\GEOPACKAGE` (ver `viz_comum.py`).
Saídas em `Computo_Planaveg_2026\Visualizacao\` (`_por_uf`, `_logs` e o gpkg final).

## Regras

- Entrada: `Reporte_Final/Planaveg_2026_Total.gpkg`, versões vs22q e vs2224q;
  hierarquia, tier e categoria de 2026.
- Fragmentação por UF, município (IBGE) e bacia (IBGE micro/meso/macro RH).
- Flags por identity (valor = rótulo ou vazio):
  - CAR_Habilitado / CAR_Analisado / CAR_Nao_Analisado (CAR Maio26 dissolvido por UF);
    CAR = qualquer das três
  - CAR_regularizacao (CAR Junho26, elegíveis; só AC, MT, PB, RJ, SP)
  - APP/RL/AUR por categoria (recortes P1 do cômputo, já cortados pela VS)
  - Licenciamento_Ambiental, Reparacao_Danos, Area_Embargada, Outras_Areas
    (Recooperar 2026 elegível), Embargo_PANGIA, ORR (só OR 2026), Manguezal
    (Pró-Manguezal); PROJ = qualquer desses
  - APA, RPPN, UC (demais categorias) e esferas (CNUC); TI (4 fases do cômputo);
    AS_ (assentamentos) e QL (quilombolas) do INCRA
  - Sobreposicao: PROJ, CAR, APA, RPPN, UC, TI, AS, QL (ordem de 2025)
- Área planar em Albers IBGE (SRS do exemplo 2025); slivers < 1 m² descartados
  e registrados; `computo` = soma nacional por classe.
- Limitação conhecida: flags APP/RL/AUR só existem onde há VS (regra do cômputo
  para os CARs); classes com polígono inteiro (Recooperar, ORR) não recebem essas
  flags fora da VS.

## Desempenho

- Máscaras grandes (ex.: CAR dissolvido por UF) são recortadas pela janela da UF
  e subdivididas em quadrantes (> 2.000 vértices) antes dos cruzamentos.
- `--bloco-km N` processa a UF em blocos (menos memória, mais lento); a UF FORA
  usa blocos de 200 km automaticamente.
- O script 2 pula UFs já processadas (use `--sobrescrever` para refazer).

## Validação ES (30/09/2026)

Conservação de área OK, Albers vs geodésica ≤ 0,002%, 0 geometrias inválidas,
100% da área de cada classe com a flag própria. vs22q = vs2224q no ES (sem VS 2024).
