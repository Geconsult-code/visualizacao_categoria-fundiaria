"""
2_fragmentar_e_atribuir.py - Atributos de visualização do cômputo Planaveg 2026
Etapa 2: para cada UF e versão da VS, recorta o Total, fragmenta por
município e bacia, aplica as flags (identity), descarta slivers < 1 m²,
deriva CAR / PROJ / Sobreposicao, dissolve por combinação de atributos e
calcula Area_ha planar em Albers IBGE.

Depois do identity (v2.0.0, ver viz_comum): token do próprio tier garantido, categoria do Recooperar
(classe 1) e origem da classe 4 pela fonte mais próxima quando a borda escapa, nomes de todas as UCs
(classe 7) e TIs (classe 6) que contêm cada trecho, e município/bacia mais próximos onde ficaram vazios.

Saída: Visualizacao/_por_uf/Visualizacao_<ver>_<UF>.gpkg
Log:   Visualizacao/_logs/2_<ver>_<UF>.csv (áreas de entrada e slivers)
       Visualizacao/_logs/2_imputacoes_<ver>_<UF>.csv (o que foi preenchido
       pela classe ou pela fonte mais próxima)

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
import shapely

import viz_comum as vc


def ler_total(ver, uf):
    camada = vc.TOTAL_CAMADA.format(ver=ver)
    gdf = vc.ler_camada(vc.TOTAL_ARQ, camada, where=f"uf = '{uf}'")
    if gdf.empty:
        return gdf, pd.DataFrame()
    gdf = gdf.rename(columns={"hierarquia": "hierarquia_planaveg", "uf": "UF"})
    gdf["categoria"] = gdf["categoria"].fillna("").astype(str).replace("<NA>", "")
    gdf["tier"] = pd.to_numeric(gdf["tier"]).round().astype(int)
    area_geod = gdf.groupby(["tier", "categoria"])["Area_ha"].sum().rename("area_geodesica_ha")
    gdf = gdf[["tier", "categoria", "Bioma", "UF", "geometry"]]
    gdf["Bioma"] = gdf["Bioma"].fillna("")
    return vc.poligonos(gdf.to_crs(vc.ALBERS)), area_geod


def carregar_municipios(bbox, janela=None):
    camada = vc.camada_de(vc.MUNICIPIOS_ARQ)
    nome = vc.campo_real(vc.MUNICIPIOS_ARQ, camada, vc.MUN_NOME_CANDIDATOS)
    cod = vc.campo_real(vc.MUNICIPIOS_ARQ, camada, vc.MUN_COD_CANDIDATOS)
    gdf = vc.ler_camada(vc.MUNICIPIOS_ARQ, camada, bbox=bbox, columns=[nome, cod])
    gdf = gdf.rename(columns={nome: "Municipio", cod: "cod_municipio"})
    gdf[["Municipio", "cod_municipio"]] = gdf[["Municipio", "cod_municipio"]].astype(str)
    return vc.subdividir_gdf(vc.poligonos(gdf.to_crs(vc.ALBERS)), janela)


def carregar_bacias(bbox, janela=None):
    gdf = vc.ler_camada(vc.BACIAS_ARQ, vc.BACIAS_CAMADA, bbox=bbox,
                        columns=list(vc.BACIAS_CAMPOS))
    gdf = gdf.rename(columns=vc.BACIAS_CAMPOS)
    for c in vc.BACIAS_CAMPOS.values():
        gdf[c] = gdf[c].fillna("").astype(str)
    return vc.subdividir_gdf(vc.poligonos(gdf.to_crs(vc.ALBERS)), janela)


def preencher_mais_proximo(sub, carregar, campos):
    """Peças sem `campos` (fora de qualquer polígono, ex.: litoral, UF FORA)
    recebem os valores do polígono mais próximo."""
    sel = np.flatnonzero((sub[campos[0]] == "").to_numpy())
    if sel.size == 0:
        return sub, None
    geoms = np.asarray(sub.geometry.values, dtype=object)[sel]
    caixa = shapely.total_bounds(geoms)
    for folga in vc.FOLGAS_BUSCA_M:
        cats = carregar(vc.bbox_geo(caixa, folga))
        i, d = vc.mais_proximo(geoms, np.asarray(cats.geometry.values, dtype=object))
        if (i >= 0).all() and d.max() <= folga:
            break
    ok = i >= 0
    if ok.any():
        sub.loc[sub.index[sel[ok]], campos] = cats[campos].to_numpy()[i[ok]]
    return sub, dict(campo=campos[0], n_pecas=int(ok.sum()),
                     area_ha=float(shapely.area(geoms[ok]).sum() / 1e4),
                     dist_max_m=float(d[ok].max()) if ok.any() else np.nan)


def aplicar_matriz(sub, ver, bbox, pref, rel):
    """Token do próprio tier, origem da classe 1/4 pela fonte mais próxima e rótulos de UC (7) e TI (6)."""
    reg = []
    sub, cont = vc.forcar_flags_internas(sub)
    for (campo, tier), (n, area) in cont.items():
        reg.append(dict(regra=f"token próprio da classe {tier}", campo=campo, n_pecas=n, area_ha=area))
    for nome, sel, campo in vc.grupos_de_imputacao(sub):
        df = vc.imputar_mais_proximo(sub, sel, [campo], ver)
        reg += [dict(regra=nome, **r) for r in df.to_dict("records")]
    # UCs (classe 7): todos os nomes; APA/RPPN/UC coerentes com os nomes
    tier = vc._tier(sub)
    alvos, ids, tab = vc.carregar_rotulos("UC", bbox)
    sub = vc.rotular(sub, tier == 7, alvos, ids)
    tier = vc._tier(sub)
    sub, n, ha, d = vc.rotular_vazios_mais_proximo(sub, tier == 7, alvos, ids)
    if n:
        reg.append(dict(regra="classe 7 sem UC (UC mais próxima)", campo="UC_Nome", n_pecas=n, area_ha=ha, dist_max_m=d))
    t = vc.textos_uc(tab, sub["_lab"].tolist()) if len(tab) else [("", "", "", False, False, False)] * len(sub)
    sub["UC_Nome"], sub["UC_Manejo"], sub["UC_Esfera"] = [x[0] for x in t], [x[1] for x in t], [x[2] for x in t]
    m7 = tier == 7
    for k, campo, valor in ((3, "APA", "APA"), (4, "RPPN", "RPPN"), (5, "_UC_outras", "UC")):
        sel = m7 & np.array([x[k] for x in t])
        vc._marcar(sub, sel, campo, valor)
    # TIs (classe 6): todos os nomes
    alvos, ids, tab = vc.carregar_rotulos("TI", bbox)
    sub = vc.rotular(sub.drop(columns="_lab"), tier == 6, alvos, ids)
    tier = vc._tier(sub)
    sub, n, ha, d = vc.rotular_vazios_mais_proximo(sub, tier == 6, alvos, ids)
    if n:
        reg.append(dict(regra="classe 6 sem TI (TI mais próxima)", campo="TI_Nome", n_pecas=n, area_ha=ha, dist_max_m=d))
    sub["TI_Nome"] = vc.textos_ti(tab, sub["_lab"].tolist()) if len(tab) else ""
    sub = sub.drop(columns="_lab")
    if reg:
        rel(f"{pref}matriz: " + "; ".join(f"{r['regra']} -> {r['campo']} ({r['n_pecas']})" for r in reg))
    return sub, reg


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
    area_ent = (base.assign(a=base.area / 1e4).groupby(["tier", "categoria"])["a"].sum()
                .rename("area_entrada_albers_ha"))
    rel(f"Total lido: {len(base):,} peças, {area_ent.sum():,.1f} ha (Albers)")

    for c in vc.CAMPOS_FLAG:
        base[c] = ""
    resultado, imputacoes = [], []
    lista = blocos(base, bloco_km or (200 if uf == "FORA" else 0))
    for k, sub in enumerate(lista, 1):
        janela = tuple(sub.total_bounds + np.array([-100, -100, 100, 100]))
        bbox = vc.bbox_geo(sub.total_bounds)
        pref = f"bloco {k}/{len(lista)}: " if len(lista) > 1 else ""
        sub = vc.atribuir_categorias(sub, carregar_municipios(bbox, janela),
                                     ["Municipio", "cod_municipio"])
        sub = vc.atribuir_categorias(sub, carregar_bacias(bbox, janela),
                                     list(vc.BACIAS_CAMPOS.values()))
        for carregar, campos in ((carregar_municipios, ["Municipio", "cod_municipio"]),
                                 (carregar_bacias, list(vc.BACIAS_CAMPOS.values()))):
            sub, r = preencher_mais_proximo(sub, carregar, campos)
            if r:
                imputacoes.append(dict(regra="local mais próximo", **r))
        rel(f"{pref}municípios e bacias: {len(sub):,} peças")
        for f in vc.FONTES:
            mascara = vc.carregar_mascara(f, ver, bbox, janela)
            sub = vc.dividir_por_mascara(sub, mascara, f["campo"], f["valor"])
            n_flag = int((sub[f["campo"]] != "").sum())
            rel(f"{pref}{f['campo']}: {len(mascara):,} polígonos na janela, "
                f"{n_flag:,} peças marcadas, {len(sub):,} peças")
        sub, reg = aplicar_matriz(sub, ver, bbox, pref, rel)
        imputacoes += reg
        resultado.append(sub)

    res = pd.concat(resultado, ignore_index=True)
    res = gpd.GeoDataFrame(res, geometry="geometry", crs=vc.ALBERS)
    area_m2 = res.area
    sliver = area_m2 < vc.MIN_AREA_M2
    area_sliver = (res[sliver].assign(a=area_m2[sliver] / 1e4).groupby(["tier", "categoria"])["a"].sum()
                   .rename("area_slivers_ha"))
    rel(f"slivers descartados: {int(sliver.sum()):,} peças, {area_sliver.sum():.4f} ha")
    res = vc.derivar_saida(res[~sliver].copy())
    res = res[[c for c in vc.COLUNAS_SAIDA if c != "Area_ha"] + ["geometry"]]
    for c in vc.CAMPOS_TEXTO:
        res[c] = res[c].fillna("").astype(str)
    res = res.dissolve(by=vc.CHAVES_DISSOLVE, as_index=False, dropna=False)
    res["Area_ha"] = res.area / 1e4
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
    imp = pd.DataFrame(imputacoes, columns=["regra", "campo", "n_pecas", "area_ha", "dist_max_m"])
    if not imp.empty:
        imp = (imp.groupby(["regra", "campo"], as_index=False)
               .agg(n_pecas=("n_pecas", "sum"), area_ha=("area_ha", "sum"),
                    dist_max_m=("dist_max_m", "max")))
    imp.insert(0, "UF", uf)
    imp.insert(0, "versao", ver)
    imp.to_csv(vc.LOGS / f"2_imputacoes_{ver}_{uf}.csv", index=False, encoding="utf-8-sig")
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
