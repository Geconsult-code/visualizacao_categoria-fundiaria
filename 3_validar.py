"""
3_validar.py - Atributos de visualização do cômputo Planaveg 2026
Etapa 3: valida as saídas da etapa 2 por UF e versão.

  A. Conservação de área por classe: entrada (Albers) = saída + slivers
  B. Diferença para a área geodésica do cômputo (informativa)
  C. Geometrias: inválidas, vazias, menor feição
  D. Coerência classe x flag própria (ex.: classe TI deveria ter flag TI)
  E. Tabela cruzada classe x flag (ha) para conferência visual

Uso (env geo):  python 3_validar.py --uf ES
                python 3_validar.py --todas
Saída: Visualizacao/_logs/3_validacao_<ver>_<UF>.csv e 3_flags_<ver>_<UF>.csv
"""
import argparse

import numpy as np
import pandas as pd
import pyogrio
import shapely

import viz_comum as vc

TOL_CONSERVACAO = 1e-4  # 0,01 %

RECOOPERAR = ["Licenciamento_Ambiental", "Reparacao_Danos", "Area_Embargada", "Outras_Areas"]


def flags_proprias(hier):
    h = hier.lower()
    for tema in ("APP", "AUR", "RL"):
        if h.startswith(f"vs em {tema.lower()} (sicar)"):
            suf = hier.rsplit("- ", 1)[-1].strip().replace("Nao Analisados", "Nao_Analisado")
            suf = {"Habilitados": "Habilitado", "Analisados": "Analisado"}.get(suf, suf)
            return [f"{tema}_{suf}"]
    regras = [("recooperar", RECOOPERAR), ("regularização ambiental", ["CAR_regularizacao"]),
              ("outros projetos", ["Embargo_PANGIA"]), ("observatório", ["ORR"]),
              ("terras indígenas", ["TI"]), ("unidades de conservação", ["UC", "APA", "RPPN"]),
              ("manguezais", ["Manguezal"])]
    for chave, campos in regras:
        if chave in h:
            return campos
    return []


def validar(ver, uf):
    arq = vc.arquivo_uf(ver, uf)
    log = vc.LOGS / f"2_{ver}_{uf}.csv"
    if not arq.exists() or not log.exists():
        print(f"-- {ver} {uf}: saída da etapa 2 não encontrada")
        return None
    gdf = pyogrio.read_dataframe(arq, layer=vc.camada_uf(ver, uf))
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

    coer = []
    for _, r in t.iterrows():
        campos = flags_proprias(r["hierarquia_planaveg"])
        sub = gdf[(gdf["hierarquia_planaveg"] == r["hierarquia_planaveg"])
                  & (gdf["categoria"] == r["categoria"])]
        if not campos or sub.empty:
            coer.append(np.nan)
            continue
        marc = (sub[campos] != "").any(axis=1)
        coer.append(100 * sub.loc[marc, "Area_ha"].sum() / sub["Area_ha"].sum())
    t["pct_area_com_flag_propria"] = coer
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
    return t


def main():
    ap = argparse.ArgumentParser()
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--uf", nargs="+")
    grp.add_argument("--todas", action="store_true")
    ap.add_argument("--versao", nargs="+", choices=vc.VERSOES, default=list(vc.VERSOES))
    a = ap.parse_args()
    tabelas = []
    for ver in a.versao:
        ufs = ([p.stem.split("_", 2)[-1] for p in sorted(vc.SAIDA_UF.glob(f"Visualizacao_{ver}_*.gpkg"))]
               if a.todas else [u.upper() for u in a.uf])
        for uf in ufs:
            t = validar(ver, uf)
            if t is not None:
                tabelas.append(t)
    if len(tabelas) > 1:
        pd.concat(tabelas).to_csv(vc.LOGS / "3_validacao_consolidada.csv",
                                  index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
