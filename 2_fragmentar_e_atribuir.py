"""
2_fragmentar_e_atribuir.py - Atributos de visualização do cômputo Planaveg 2026
Etapa 2: para cada UF e versão da VS, recorta o Total, fragmenta por
município e bacia, aplica as flags (identity), descarta slivers < 1 m²,
deriva CAR / PROJ / Sobreposicao, dissolve por combinação de atributos e
calcula Area_ha planar em Albers IBGE.

Saída: Visualizacao/_por_uf/Visualizacao_<ver>_<UF>.gpkg
Log:   Visualizacao/_logs/2_<ver>_<UF>.csv (áreas de entrada e slivers)

Uso (env geo):
  python 2_fragmentar_e_atribuir.py --uf ES                 # teste
  python 2_fragmentar_e_atribuir.py --uf MG BA --versao vs22q
  python 2_fragmentar_e_atribuir.py --todas                 # Brasil (inclui FORA)
Opções: --bloco-km N  processa em blocos de N km (padrão: UF inteira;
        FORA sempre em blocos de 200 km); --sobrescrever
"""
import argparse
import traceback

import numpy as np
import pandas as pd
import geopandas as gpd
import pyogrio

import viz_comum as vc


def ler_total(ver, uf):
    camada = vc.TOTAL_CAMADA.format(ver=ver)
    gdf = vc.ler_camada(vc.TOTAL_ARQ, camada, where=f"uf = '{uf}'")
    if gdf.empty:
        return gdf, pd.DataFrame()
    gdf = gdf.rename(columns={"hierarquia": "hierarquia_planaveg", "uf": "UF"})
    gdf["categoria"] = gdf["categoria"].fillna("").astype(str).replace("<NA>", "")
    area_geod = (gdf.groupby(["hierarquia_planaveg", "categoria"])["Area_ha"].sum()
                 .rename("area_geodesica_ha"))
    gdf = gdf[["hierarquia_planaveg", "tier", "categoria", "Bioma", "UF", "geometry"]]
    gdf["Bioma"] = gdf["Bioma"].fillna("")
    return vc.poligonos(gdf.to_crs(vc.ALBERS)), area_geod


def carregar_municipios(bbox):
    camada = vc.camada_de(vc.MUNICIPIOS_ARQ)
    nome = vc.campo_real(vc.MUNICIPIOS_ARQ, camada, vc.MUN_NOME_CANDIDATOS)
    cod = vc.campo_real(vc.MUNICIPIOS_ARQ, camada, vc.MUN_COD_CANDIDATOS)
    gdf = vc.ler_camada(vc.MUNICIPIOS_ARQ, camada, bbox=bbox, columns=[nome, cod])
    gdf = gdf.rename(columns={nome: "Municipio", cod: "cod_municipio"})
    gdf[["Municipio", "cod_municipio"]] = gdf[["Municipio", "cod_municipio"]].astype(str)
    return vc.poligonos(gdf.to_crs(vc.ALBERS))


def carregar_bacias(bbox):
    gdf = vc.ler_camada(vc.BACIAS_ARQ, vc.BACIAS_CAMADA, bbox=bbox,
                        columns=list(vc.BACIAS_CAMPOS))
    gdf = gdf.rename(columns=vc.BACIAS_CAMPOS)
    for c in vc.BACIAS_CAMPOS.values():
        gdf[c] = gdf[c].fillna("").astype(str)
    return vc.poligonos(gdf.to_crs(vc.ALBERS))


def blocos(base, bloco_km):
    if not bloco_km:
        return [base]
    pts = base.geometry.representative_point()
    chave = (np.floor(pts.x / (bloco_km * 1000)).astype(int).astype(str) + "_"
             + np.floor(pts.y / (bloco_km * 1000)).astype(int).astype(str))
    return [g.reset_index(drop=True) for _, g in base.groupby(chave.values)]


def processar(ver, uf, bloco_km, sobrescrever):
    destino = vc.arquivo_uf(ver, uf)
    if destino.exists() and not sobrescrever:
        print(f"-- {ver} {uf}: já existe ({destino.name}); use --sobrescrever")
        return
    rel = vc.Relogio()
    print(f"== {ver} {uf}", flush=True)
    base, area_geod = ler_total(ver, uf)
    if base.empty:
        print("  sem feições para esta UF")
        return
    area_ent = (base.assign(a=base.area / 1e4)
                .groupby(["hierarquia_planaveg", "categoria"])["a"].sum()
                .rename("area_entrada_albers_ha"))
    rel(f"Total lido: {len(base):,} peças, {area_ent.sum():,.1f} ha (Albers)")

    for c in vc.CAMPOS_FLAG:
        base[c] = ""
    resultado = []
    lista = blocos(base, bloco_km or (200 if uf == "FORA" else 0))
    for k, sub in enumerate(lista, 1):
        janela = tuple(sub.total_bounds + np.array([-100, -100, 100, 100]))
        bbox = vc.bbox_geo(sub.total_bounds)
        pref = f"bloco {k}/{len(lista)}: " if len(lista) > 1 else ""
        sub = vc.atribuir_categorias(sub, carregar_municipios(bbox),
                                     ["Municipio", "cod_municipio"])
        sub = vc.atribuir_categorias(sub, carregar_bacias(bbox),
                                     list(vc.BACIAS_CAMPOS.values()))
        rel(f"{pref}municípios e bacias: {len(sub):,} peças")
        for f in vc.FONTES:
            mascara = vc.carregar_mascara(f, ver, bbox, janela)
            sub = vc.dividir_por_mascara(sub, mascara, f["campo"], f["valor"])
            n_flag = int((sub[f["campo"]] != "").sum())
            rel(f"{pref}{f['campo']}: {len(mascara):,} polígonos na janela, "
                f"{n_flag:,} peças marcadas, {len(sub):,} peças")
        resultado.append(sub)

    res = pd.concat(resultado, ignore_index=True)
    res = gpd.GeoDataFrame(res, geometry="geometry", crs=vc.ALBERS)
    area_m2 = res.area
    sliver = area_m2 < vc.MIN_AREA_M2
    area_sliver = (res[sliver].assign(a=area_m2[sliver] / 1e4)
                   .groupby(["hierarquia_planaveg", "categoria"])["a"].sum()
                   .rename("area_slivers_ha"))
    rel(f"slivers descartados: {int(sliver.sum()):,} peças, {area_sliver.sum():.4f} ha")
    res = vc.derivar_campos(res[~sliver].copy())

    for c in vc.CHAVES_DISSOLVE:
        if c != "tier":
            res[c] = res[c].fillna("").astype(str)
    res = res.dissolve(by=vc.CHAVES_DISSOLVE, as_index=False, dropna=False)
    res["Area_ha"] = res.area / 1e4
    res["computo"] = np.nan  # preenchido na etapa 4 (soma nacional por classe)
    res = res[vc.COLUNAS_SAIDA + ["geometry"]]
    rel(f"dissolvido: {len(res):,} feições, {res['Area_ha'].sum():,.1f} ha")

    vc.SAIDA_UF.mkdir(parents=True, exist_ok=True)
    vc.LOGS.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        destino.unlink()
    pyogrio.write_dataframe(res, destino, layer=vc.camada_uf(ver, uf),
                            driver="GPKG", promote_to_multi=True)
    log = pd.concat([area_geod, area_ent, area_sliver], axis=1).fillna(0).reset_index()
    log.insert(0, "UF", uf)
    log.insert(0, "versao", ver)
    log.to_csv(vc.LOGS / f"2_{ver}_{uf}.csv", index=False, encoding="utf-8-sig")
    rel(f"gravado {destino.name}")


def ufs_do_total():
    camada = vc.TOTAL_CAMADA.format(ver=vc.VERSOES[0])
    sql = f'SELECT DISTINCT uf FROM "{camada}" ORDER BY uf'
    return pyogrio.read_dataframe(vc.TOTAL_ARQ, sql=sql, read_geometry=False)["uf"].tolist()


def main():
    ap = argparse.ArgumentParser()
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--uf", nargs="+")
    grp.add_argument("--todas", action="store_true")
    ap.add_argument("--versao", nargs="+", choices=vc.VERSOES, default=list(vc.VERSOES))
    ap.add_argument("--bloco-km", type=float, default=0)
    ap.add_argument("--sobrescrever", action="store_true")
    a = ap.parse_args()
    ufs = ufs_do_total() if a.todas else [u.upper() for u in a.uf]
    falhas = []
    for ver in a.versao:
        for uf in ufs:
            try:
                processar(ver, uf, a.bloco_km, a.sobrescrever)
            except Exception:  # noqa: BLE001 - segue para a próxima UF
                traceback.print_exc()
                falhas.append(f"{ver} {uf}")
    print("\nFalhas: " + (", ".join(falhas) if falhas else "nenhuma"))


if __name__ == "__main__":
    main()
