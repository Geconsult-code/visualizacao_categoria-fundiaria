"""
3_validar.py - Atributos de visualização do cômputo Planaveg 2026
Etapa 3: valida as saídas da etapa 2 por UF e versão.

  A. Conservação de área por classe: entrada (Albers) = saída + slivers
  B. Diferença para a área geodésica do cômputo (informativa)
  C. Geometrias: inválidas, vazias, menor feição
  D. % da área de cada classe sem nenhuma violação da matriz
  E. Tabela cruzada classe x flag (ha) para conferência visual
  F. Matriz de preenchimento (regras M1 a M9, ver MATRIZ abaixo): peças e
     área que violam cada regra (v2.0.0); a meta é zero em todas

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

# Matriz de preenchimento v2.0.0 (código, descrição). As regras estão em matriz().
MATRIZ = [
    ("M1", "Hierarquia, nomes e localização preenchidos (hierarquia_planaveg, tier, Nome_Abreviado, Nome_Detalhado, "
           "Area_ha, UF, Bioma, Municipio, cod_municipio, Bacia, Bacia_meso, Regiao_Hidrografica)"),
    ("M2", "CAR e CAR_Condicao preenchidos nas classes 3, 9, 10 e 11 e vazios nas demais"),
    ("M3", "PROJ e PROJ_Categoria preenchidos nas classes 1, 2, 4 e 5 e vazios nas demais"),
    ("M4", "UC, UC_Nome, UC_Manejo e UC_Esfera preenchidos na classe 7 e vazios nas demais"),
    ("M5", "TI e TI_Nome preenchidos na classe 6 e vazios nas demais"),
    ("M6", "Manguezal preenchido na classe 8 e vazio nas demais"),
    ("M7", "Textos coerentes com a classe (hierarquia, nomes, CAR_Condicao, PROJ_Categoria na lista da planilha)"),
    ("M8", "Sobreposicao preenchida e com o token da própria classe (PROJ, CAR, UC/APA/RPPN, TI, MANG)"),
]


def _permitidos():
    """{tier: (hierarquias, (abreviado, detalhado) possíveis, condições, categorias de projeto)}."""
    p = {}
    for t in range(1, 12):
        hier = set(vc.FONTES_T4.values()) if t == 4 else {vc.HIERARQUIA[t]}
        nomes = ({(a, d) for a, d, _ in vc.NOMES_RECOOPERAR.values()} if t == 1 else {vc.NOMES[t]})
        cond = ({vc.CAR_CONDICAO_T3} if t == 3 else set(vc.CAR_CONDICAO.values()) if t in (9, 10, 11) else {""})
        pc = ({x for _, _, x in vc.NOMES_RECOOPERAR.values()} if t == 1 else {vc.PROJ_CATEGORIA.get(t, "")})
        p[t] = (hier, nomes, cond, pc)
    return p


TOKEN_PROPRIO = {1: ["PROJ"], 2: ["PROJ"], 4: ["PROJ"], 5: ["PROJ"], 3: ["CAR"], 9: ["CAR"], 10: ["CAR"], 11: ["CAR"],
                 6: ["TI"], 7: ["UC", "APA", "RPPN"], 8: ["MANG"]}


def matriz(gdf):
    """DataFrame booleano: True onde a peça viola a regra."""
    s = lambda c: gdf[c].fillna("").astype(str)  # noqa: E731
    cheio = lambda cs: pd.concat([s(c) != "" for c in cs], axis=1).all(axis=1)  # noqa: E731
    vazio = lambda cs: pd.concat([s(c) == "" for c in cs], axis=1).all(axis=1)  # noqa: E731
    tier = pd.to_numeric(gdf["tier"], errors="coerce").round()
    v = pd.DataFrame(index=gdf.index)
    v["M1"] = ~cheio(["hierarquia_planaveg", "Nome_Abreviado", "Nome_Detalhado"] + vc.CAMPOS_LOCAL) | tier.isna() | gdf["Area_ha"].isna()
    for cod, tiers, campos in (("M2", vc.TIERS_CAR, ["CAR", "CAR_Condicao"]), ("M3", vc.TIERS_PROJ, ["PROJ", "PROJ_Categoria"]),
                               ("M4", (7,), ["UC", "UC_Nome", "UC_Manejo", "UC_Esfera"]), ("M5", (6,), ["TI", "TI_Nome"]),
                               ("M6", (8,), ["Manguezal"])):
        dentro = tier.isin(tiers)
        v[cod] = (dentro & ~cheio(campos)) | (~dentro & ~vazio(campos))
    perm = _permitidos()
    m7 = pd.Series(False, index=gdf.index)
    for t, (hier, nomes, cond, pc) in perm.items():
        sel = tier == t
        if not sel.any():
            continue
        par = list(zip(s("Nome_Abreviado")[sel], s("Nome_Detalhado")[sel]))
        m7[sel] = (~s("hierarquia_planaveg")[sel].isin(hier) | ~pd.Series([x in nomes for x in par], index=sel[sel].index)
                   | ~s("CAR_Condicao")[sel].isin(cond) | ~s("PROJ_Categoria")[sel].isin(pc))
    m7 |= ~tier.isin(range(1, 12))
    v["M7"] = m7
    sob = s("Sobreposicao")
    m8 = sob == ""
    for t, toks in TOKEN_PROPRIO.items():
        sel = tier == t
        if sel.any():
            m8[sel] |= ~pd.concat([sob[sel].str.contains(k, regex=False) for k in toks], axis=1).any(axis=1)
    v["M8"] = m8
    return v


def validar(ver, uf):
    arq = vc.arquivo_uf(ver, uf)
    log = vc.LOGS / f"2_{ver}_{uf}.csv"
    if not arq.exists() or not log.exists():
        print(f"-- {ver} {uf}: saída da etapa 2 não encontrada")
        return None
    gdf = vc.completar_colunas(pyogrio.read_dataframe(arq, layer=vc.camada_uf(ver, uf)))
    ent = pd.read_csv(log, keep_default_na=False).drop(columns=["versao", "UF"])
    chave = ["tier", "categoria"]
    gdf["tier"] = pd.to_numeric(gdf["tier"]).round().astype(int)
    gdf["categoria"] = gdf["CAR_Condicao"].map(vc.CATEGORIA_DE_CONDICAO).fillna("")
    ent["categoria"] = ent["categoria"].fillna("").astype(str)
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
        sel = (gdf["tier"] == r["tier"]) & (gdf["categoria"] == r["categoria"])
        if not sel.any():
            coer.append(np.nan)
            continue
        a = gdf.loc[sel, "Area_ha"]
        coer.append(100 * a[~viol.loc[sel].any(axis=1)].sum() / a.sum())
    t["pct_area_sem_violacao"] = coer
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

    flags = ["CAR", "PROJ", "Manguezal", "APA", "RPPN", "UC", "TI", "AS", "QL"]
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
    print("   D. % da área da classe sem violação da matriz:")
    for _, r in t.iterrows():
        cat = f" [{r['categoria']}]" if r["categoria"] else ""
        print(f"      {r['pct_area_sem_violacao']:6.2f}%  classe {int(r['tier'])}{cat}")
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
