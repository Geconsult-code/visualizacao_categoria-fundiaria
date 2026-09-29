"""
4_consolidar_brasil.py - Atributos de visualização do cômputo Planaveg 2026
Etapa 4: junta as UFs de cada versão num único GeoPackage e preenche
`computo` com a soma nacional de Area_ha (Albers) por classe
(hierarquia_planaveg), como no exemplo de 2025.

Saída: Visualizacao/Planaveg_2026_Categorias_Visualizacao.gpkg
       camadas Planaveg_2026_Visualizacao_vs22q e _vs2224q
Uso (env geo):  python 4_consolidar_brasil.py [--versao vs22q]
"""
import argparse

import pandas as pd
import pyogrio

import viz_comum as vc

DESTINO = vc.SAIDA / "Planaveg_2026_Categorias_Visualizacao.gpkg"


def consolidar(ver):
    arquivos = sorted(vc.SAIDA_UF.glob(f"Visualizacao_{ver}_*.gpkg"))
    if not arquivos:
        print(f"-- {ver}: nenhuma UF processada")
        return
    ufs = [p.stem.split("_", 2)[-1] for p in arquivos]
    print(f"== {ver}: {len(arquivos)} UFs ({', '.join(ufs)})")

    # 1ª passada: só atributos, para o computo nacional por classe
    tabs = [pyogrio.read_dataframe(p, layer=vc.camada_uf(ver, uf), read_geometry=False,
                                   columns=["hierarquia_planaveg", "Area_ha"])
            for p, uf in zip(arquivos, ufs)]
    computo = pd.concat(tabs).groupby("hierarquia_planaveg")["Area_ha"].sum()
    for h, v in computo.items():
        print(f"   {v:>16,.1f} ha  {h}")

    # 2ª passada: grava UF por UF (append), sem carregar o Brasil inteiro na memória
    camada = f"Planaveg_2026_Visualizacao_{ver}"
    for i, (p, uf) in enumerate(zip(arquivos, ufs)):
        gdf = pyogrio.read_dataframe(p, layer=vc.camada_uf(ver, uf))
        gdf["computo"] = gdf["hierarquia_planaveg"].map(computo)
        pyogrio.write_dataframe(gdf, DESTINO, layer=camada, driver="GPKG",
                                promote_to_multi=True, append=i > 0)
    print(f"   gravado {DESTINO.name}:{camada}")
    computo.rename("computo_ha").to_csv(vc.LOGS / f"4_computo_{ver}.csv",
                                        encoding="utf-8-sig")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--versao", nargs="+", choices=vc.VERSOES, default=list(vc.VERSOES))
    a = ap.parse_args()
    for ver in a.versao:
        if DESTINO.exists():
            camadas = [c for c, _ in pyogrio.list_layers(DESTINO)]
            if f"Planaveg_2026_Visualizacao_{ver}" in camadas:
                raise SystemExit(f"{DESTINO.name} já tem a camada de {ver}; "
                                 "apague o arquivo antes de reconsolidar.")
        consolidar(ver)


if __name__ == "__main__":
    main()
