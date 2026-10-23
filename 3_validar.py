"""
3_validar.py - Atributos de visualização do cômputo Planaveg 2026
Etapa 3: valida as saídas da etapa 2 por UF e versão.

  A. Conservação de área por classe: entrada (Albers) = saída + slivers
  B. Diferença para a área geodésica do cômputo (informativa)
  C. Geometrias: inválidas, vazias, menor feição
  D. Coerência classe x flag própria (ex.: classe TI deveria ter flag TI)
  E. Tabela cruzada classe x flag (ha) para conferência visual
  F. Matriz de preenchimento (regras M1 a M9, ver MATRIZ abaixo): peças e
     área que violam cada regra; a meta é zero em todas

Uso (env geo):  python 3_validar.py --uf ES
                python 3_validar.py --todas
Saída: Visualizacao/_logs/3_validacao_<ver>_<UF>.csv, 3_flags_<ver>_<UF>.csv,
       3_matriz_<ver>_<UF>.csv e 3_matriz_consolidada.csv (com --todas)
"""
import argparse

import numpy as np
import pandas as pd
import pyogrio
import shapely

import viz_comum as vc

TOL_CONSERVACAO = 1e-4  # 0,01 %

RECOOPERAR = vc.RECOOPERAR

# Matriz de preenchimento: (código, descrição). As regras estão em matriz().
MATRIZ = [
    ("M1", "Colunas de hierarquia e localização preenchidas (hierarquia_planaveg, tier, "
           "computo, Area_ha, UF, Bioma, Municipio, cod_municipio, Bacia, Bacia_meso, "
           "Regiao_Hidrografica)"),
    ("M2", "categoria preenchida nas classes 9-11 (APP/AUR/RL) e vazia nas demais"),
    ("M3", "Pelo menos um tema: CAR, PROJ, UC, TI ou Manguezal"),
    ("M4", "CAR exige situação: CAR_Habilitado, CAR_Analisado, CAR_Nao_Analisado ou "
           "CAR_regularizacao; e situação/APP/RL/AUR implica CAR"),
    ("M5", "APP/RL/AUR_<situação> implica CAR_<situação>"),
    ("M6", "PROJ exige subcategoria (Recooperar, MonitoRAD, Embargo_PANGIA, GEF_Terrestre, "
           "Restauracao_Ecologica, ORR) e subcategoria implica PROJ"),
    ("M7", "UC exige esfera (UC_federal, UC_estadual, UC_municipal); APA e RPPN "
           "implicam UC"),
    ("M8", "Flags próprias da classe (ver flags_proprias)"),
    ("M9", "Sobreposicao preenchida"),
]


def flags_proprias(hier, tier, categoria):
    """Lista de grupos; a peça precisa ter pelo menos um campo de cada grupo."""
    t = int(round(float(tier)))
    suf = {"Habilitados": "Habilitado", "Analisados": "Analisado",
           "Nao_Analisados": "Nao_Analisado"}.get(categoria, "")
    tema = {9: "APP", 10: "AUR", 11: "RL"}.get(t)
    if tema:
        return [[f"{tema}_{suf}"], [f"CAR_{suf}"], ["CAR"]]
    return {1: [RECOOPERAR, ["PROJ"]], 2: [["MonitoRAD"], ["PROJ"]], 3: [["CAR_regularizacao"], ["CAR"]],
            4: [vc.OUTROS_PROJETOS, ["PROJ"]], 5: [["ORR"], ["PROJ"]], 6: [["TI"]],
            7: [["UC"], vc.UC_ESFERAS], 8: [["Manguezal"]]}.get(t, [])


def matriz(gdf):
    """DataFrame booleano: True onde a peça viola a regra."""
    vazio = lambda c: (gdf[c].fillna("").astype(str) == "")  # noqa: E731
    tem = lambda cs: (gdf[cs].fillna("").astype(str) != "").any(axis=1)  # noqa: E731
    tier = pd.to_numeric(gdf["tier"], errors="coerce").round()
    car_classe = tier.isin([9, 10, 11])
    v = pd.DataFrame(index=gdf.index)
    v["M1"] = (gdf[["hierarquia_planaveg", "UF", "Bioma", "Municipio", "cod_municipio",
                    "Bacia", "Bacia_meso", "Regiao_Hidrografica"]].fillna("").astype(str) == ""
               ).any(axis=1) | tier.isna() | gdf["Area_ha"].isna() | (
                   gdf["computo"].isna() if gdf["computo"].notna().any() else False)
    v["M2"] = (car_classe & vazio("categoria")) | (~car_classe & ~vazio("categoria"))
    v["M3"] = ~tem(["CAR", "PROJ", "UC", "TI", "Manguezal"])
    v["M4"] = (~vazio("CAR") & ~tem(vc.CAR_SITUACOES)) | (
        vazio("CAR") & tem(vc.CAR_SITUACOES + vc.TEMAS_CAR))
    m5 = pd.Series(False, index=gdf.index)
    for c in vc.TEMAS_CAR:
        m5 |= ~vazio(c) & vazio("CAR_" + c.split("_", 1)[1])
    v["M5"] = m5
    v["M6"] = (~vazio("PROJ") & ~tem(vc.PROJ_COMPONENTES)) | (
        vazio("PROJ") & tem(vc.PROJ_COMPONENTES))
    v["M7"] = (~vazio("UC") & ~tem(vc.UC_ESFERAS)) | (
        vazio("UC") & tem(["APA", "RPPN"]))
    m8 = pd.Series(False, index=gdf.index)
    for (h, t, c), idx in gdf.groupby(["hierarquia_planaveg", "tier", "categoria"]).groups.items():
        for grupo in flags_proprias(h, t, c):
            m8.loc[idx] |= ~tem(grupo).loc[idx]
    v["M8"] = m8
    v["M9"] = vazio("Sobreposicao")
    return v


def validar(ver, uf):
    arq = vc.arquivo_uf(ver, uf)
    log = vc.LOGS / f"2_{ver}_{uf}.csv"
    if not arq.exists() or not log.exists():
        print(f"-- {ver} {uf}: saída da etapa 2 não encontrada")
        return None
    gdf = vc.completar_colunas(pyogrio.read_dataframe(arq, layer=vc.camada_uf(ver, uf)))
    ent = pd.read_csv(log, keep_default_na=False).drop(columns=["versao", "UF"])
    chave = ["hierarquia_planaveg", "categoria"]
    said = gdf.groupby(chave)["Area_ha"].sum().rename("area_saida_ha").reset_index()
    t = ent.merge(said, on=chave, how="outer").fillna(0)
    t["dif_conservacao_ha"] = (t["area_entrada_albers_ha"] - t["area_saida_ha"]
                               - t["area_slivers_ha"])
    t["dif_conservacao_pct"] = 100 * t["dif_conservacao_ha"] / t["area_entrada_albers_ha"].where(
        t["area_entrada_albers_ha"] > 0)
    t["dif_albers_vs_geodesica_pct"] = 100 * (t["area_saida_ha"] / t["area_geodesica_ha"].where(
        t["area_geodesica_ha"] > 0) - 1)

    viol = matriz(gdf)
    coer = []
    for _, r in t.iterrows():
        sel = ((gdf["hierarquia_planaveg"] == r["hierarquia_planaveg"])
               & (gdf["categoria"] == r["categoria"]))
        if not sel.any():
            coer.append(np.nan)
            continue
        a = gdf.loc[sel, "Area_ha"]
        coer.append(100 * a[~viol.loc[sel, "M8"]].sum() / a.sum())
    t["pct_area_com_flag_propria"] = coer
    mat = pd.DataFrame([dict(versao=ver, UF=uf, regra=cod, descricao=desc,
                             pecas_violando=int(viol[cod].sum()),
                             area_violando_ha=round(float(gdf.loc[viol[cod], "Area_ha"].sum()), 4))
                        for cod, desc in MATRIZ])
    t.insert(0, "UF", uf)
    t.insert(0, "versao", ver)

    geom = gdf.geometry.values
    n_inval = int((~shapely.is_valid(geom)).sum())
    n_vazia = int(shapely.is_empty(geom).sum())
    menor = gdf["Area_ha"].min()

    flags = [c for c in vc.COLUNAS_SAIDA
             if c not in vc.CAMPOS_HIER + vc.CAMPOS_LOCAL + ["computo", "Area_ha", "Sobreposicao"]]
    cruz = pd.DataFrame({f: gdf.loc[gdf[f] != ""].groupby("hierarquia_planaveg")["Area_ha"].sum()
                         for f in flags}).fillna(0).round(2)
    cruz.insert(0, "total_ha", gdf.groupby("hierarquia_planaveg")["Area_ha"].sum().round(2))

    t.to_csv(vc.LOGS / f"3_validacao_{ver}_{uf}.csv", index=False, encoding="utf-8-sig")
    cruz.to_csv(vc.LOGS / f"3_flags_{ver}_{uf}.csv", encoding="utf-8-sig")
    mat.to_csv(vc.LOGS / f"3_matriz_{ver}_{uf}.csv", index=False, encoding="utf-8-sig")
    if viol.any(axis=1).any():
        exemplos = gdf.loc[viol.any(axis=1)].drop(columns="geometry").copy()
        exemplos.insert(0, "regras_violadas",
                        viol.loc[viol.any(axis=1)].apply(lambda r: ",".join(r.index[r]), axis=1))
        exemplos.to_csv(vc.LOGS / f"3_matriz_pecas_{ver}_{uf}.csv", index=False,
                        encoding="utf-8-sig")

    ok_cons = (t["dif_conservacao_pct"].abs().fillna(0) <= 100 * TOL_CONSERVACAO).all()
    print(f"== {ver} {uf}: {len(gdf):,} feições, {gdf['Area_ha'].sum():,.1f} ha")
    print(f"   A. conservação de área: {'OK' if ok_cons else 'FALHOU'} "
          f"(máx {t['dif_conservacao_ha'].abs().max():.4f} ha); "
          f"slivers {t['area_slivers_ha'].sum():.4f} ha")
    print(f"   B. Albers vs geodésica: {t['dif_albers_vs_geodesica_pct'].min():+.3f}% a "
          f"{t['dif_albers_vs_geodesica_pct'].max():+.3f}%")
    print(f"   C. geometrias inválidas {n_inval}, vazias {n_vazia}, menor feição {menor:.6f} ha")
    print("   D. % da área da classe com a flag própria:")
    for _, r in t.iterrows():
        cat = f" [{r['categoria']}]" if r["categoria"] else ""
        print(f"      {r['pct_area_com_flag_propria']:6.2f}%  {r['hierarquia_planaveg']}{cat}")
    print("   F. matriz de preenchimento (peças / ha violando):")
    for _, r in mat.iterrows():
        marca = "OK " if r["pecas_violando"] == 0 else "!! "
        print(f"      {marca}{r['regra']}: {r['pecas_violando']:,} / {r['area_violando_ha']:,.4f} ha")
    return t, mat


def main():
    ap = argparse.ArgumentParser()
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--uf", nargs="+")
    grp.add_argument("--todas", action="store_true")
    ap.add_argument("--versao", nargs="+", choices=vc.VERSOES, default=list(vc.VERSOES))
    a = ap.parse_args()
    tabelas, matrizes = [], []
    for ver in a.versao:
        ufs = ([p.stem.split("_", 2)[-1] for p in sorted(vc.SAIDA_UF.glob(f"Visualizacao_{ver}_*.gpkg"))]
               if a.todas else [u.upper() for u in a.uf])
        for uf in ufs:
            r = validar(ver, uf)
            if r is not None:
                tabelas.append(r[0])
                matrizes.append(r[1])
    if len(tabelas) > 1:
        pd.concat(tabelas).to_csv(vc.LOGS / "3_validacao_consolidada.csv",
                                  index=False, encoding="utf-8-sig")
        m = pd.concat(matrizes)
        m.to_csv(vc.LOGS / "3_matriz_consolidada.csv", index=False, encoding="utf-8-sig")
        res = m.groupby(["versao", "regra"])[["pecas_violando", "area_violando_ha"]].sum()
        print("\n== Matriz de preenchimento, todas as UFs\n" + res.to_string())


if __name__ == "__main__":
    main()
