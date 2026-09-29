"""
1_checar_fontes.py - Atributos de visualização do cômputo Planaveg 2026
Etapa 1: confere se todas as fontes existem, se as camadas e os filtros
(where) funcionam e quantas feições cada flag vai usar. Só lê; não grava
nada além do relatório CSV em Visualizacao/_logs.

Uso (env geo):  python 1_checar_fontes.py
"""
import pandas as pd
import pyogrio

import viz_comum as vc


def contar(arquivo, camada, where=None):
    sql = f'SELECT COUNT(*) AS n FROM "{camada}"' + (f" WHERE {where}" if where else "")
    return int(pyogrio.read_dataframe(arquivo, sql=sql, read_geometry=False)["n"][0])


def main():
    vc.LOGS.mkdir(parents=True, exist_ok=True)
    linhas, problemas = [], 0

    print("== Hierarquia final (Total)")
    for ver in vc.VERSOES:
        camada = vc.TOTAL_CAMADA.format(ver=ver)
        sql = (f'SELECT uf, COUNT(*) AS n, SUM(Area_ha) AS area_ha FROM "{camada}" '
               f"GROUP BY uf ORDER BY uf")
        df = pyogrio.read_dataframe(vc.TOTAL_ARQ, sql=sql, read_geometry=False)
        print(f"  {ver}: {len(df)} UFs, {df['n'].sum()} feições, "
              f"{df['area_ha'].sum():,.0f} ha (geodésica)")
        linhas.append(dict(item=f"Total {ver}", arquivo=vc.TOTAL_ARQ.name, camada=camada,
                           where="", n=int(df["n"].sum()), status="ok"))

    print("== Municípios e bacias")
    cam_mun = vc.camada_de(vc.MUNICIPIOS_ARQ)
    nome = vc.campo_real(vc.MUNICIPIOS_ARQ, cam_mun, vc.MUN_NOME_CANDIDATOS)
    cod = vc.campo_real(vc.MUNICIPIOS_ARQ, cam_mun, vc.MUN_COD_CANDIDATOS)
    n = contar(vc.MUNICIPIOS_ARQ, cam_mun)
    print(f"  municípios: camada {cam_mun}, campos {nome}/{cod}, {n} feições")
    linhas.append(dict(item="Municipios", arquivo=vc.MUNICIPIOS_ARQ.name, camada=cam_mun,
                       where=f"{nome}/{cod}", n=n, status="ok"))
    info = pyogrio.read_info(vc.BACIAS_ARQ, layer=vc.BACIAS_CAMADA)
    faltam = [c for c in vc.BACIAS_CAMPOS if c not in info["fields"]]
    status = "ok" if not faltam else f"FALTAM {faltam}"
    problemas += bool(faltam)
    print(f"  bacias: {info['features']} feições, {status}")
    linhas.append(dict(item="Bacias", arquivo=vc.BACIAS_ARQ.name, camada=vc.BACIAS_CAMADA,
                       where="", n=info["features"], status=status))

    print("== Fontes das flags")
    for f in vc.FONTES:
        for ver in (vc.VERSOES if "{ver}" in (f["camada"] or "") else (None,)):
            item = f["campo"] + (f" [{ver}]" if ver else "")
            try:
                if not f["arquivo"].exists():
                    raise FileNotFoundError("arquivo não encontrado")
                camada = vc.camada_de(f["arquivo"], f["camada"], ver)
                n = contar(f["arquivo"], camada, f["where"])
                status = "ok" if n > 0 else "VAZIA"
            except Exception as e:  # noqa: BLE001
                camada, n, status = f["camada"], -1, f"ERRO: {e}"
            problemas += status != "ok"
            print(f"  {item:32s} {n:>10,}  {status}")
            linhas.append(dict(item=item, arquivo=f["arquivo"].name, camada=camada,
                               where=f["where"] or "", n=n, status=status))

    saida = vc.LOGS / "1_checagem_fontes.csv"
    pd.DataFrame(linhas).to_csv(saida, index=False, encoding="utf-8-sig")
    print(f"\n{problemas} problema(s). Relatório: {saida}")


if __name__ == "__main__":
    main()
