"""
viz_comum.py - Atributos de visualização do cômputo Planaveg 2026
Configuração (caminhos, fontes das flags, esquema de saída) e funções
geométricas compartilhadas pelos scripts 1 a 4.

Regras aprovadas (29/09/2026):
- Entrada: Reporte_Final/Planaveg_2026_Total.gpkg, versões vs22q e vs2224q,
  mantendo hierarquia, tier e categoria de 2026.
- Fragmentação por UF (campo do cômputo), município e bacia (micro/meso/macro RH).
- Flags por identity: valor = rótulo ou '' (vazio).
- Área planar em Albers IBGE (mesmo SRS do exemplo 2025); saída 2D.
- Slivers < 1 m² são descartados e a área descartada é registrada.
"""
from pathlib import Path
import os
import time

import numpy as np
import pandas as pd
import geopandas as gpd
import shapely
import pyogrio
from pyproj import CRS, Transformer

# ----------------------------------------------------------------------------
# Caminhos (PLANAVEG_GEO permite apontar para outra pasta em testes)
# ----------------------------------------------------------------------------
GEO = Path(os.environ.get(
    "PLANAVEG_GEO",
    r"C:\Users\User\Dropbox\#CONSULTANCY\PLANAVEG\GEODATABASE\GEOPACKAGE"))
C26 = GEO / "Computo_Planaveg_2026"
SAIDA = C26 / "Visualizacao"
SAIDA_UF = SAIDA / "_por_uf"
LOGS = SAIDA / "_logs"

VERSOES = ("vs22q", "vs2224q")
MIN_AREA_M2 = 1.0  # slivers abaixo disso são descartados (e registrados)

ALBERS_WKT = (
    'PROJCS["IBGE_South_America_Albers_Equal_Area_Conic",'
    'GEOGCS["GCS_SIRGAS_2000",DATUM["D_SIRGAS_2000",'
    'SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],'
    'UNIT["Degree",0.0174532925199433]],PROJECTION["Albers"],'
    'PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],'
    'PARAMETER["Central_Meridian",-54.0],PARAMETER["Standard_Parallel_1",-2.0],'
    'PARAMETER["Standard_Parallel_2",-22.0],PARAMETER["Latitude_Of_Origin",-12.0],'
    'UNIT["Meter",1.0]]')
ALBERS = CRS.from_wkt(ALBERS_WKT)
CRS_GEO = CRS.from_epsg(4674)
_ALB_PARA_GEO = Transformer.from_crs(ALBERS, CRS_GEO, always_xy=True)

# ----------------------------------------------------------------------------
# Entrada: hierarquia final do cômputo 2026
# ----------------------------------------------------------------------------
TOTAL_ARQ = C26 / "Reporte_Final" / "Planaveg_2026_Total.gpkg"
TOTAL_CAMADA = "Reporte_Planaveg_Total_{ver}"

MUNICIPIOS_ARQ = GEO / "IBGE_Limite_Municipios.gpkg"
MUN_NOME_CANDIDATOS = ("NM_MUN", "NM_MUNICIP", "NM_MUNICIPIO", "NOME", "NM_MUNICIPIO_2022")
MUN_COD_CANDIDATOS = ("CD_MUN", "CD_GEOCMU", "CD_MUNICIP", "GEOCODIGO", "CD_MUNICIPIO")

BACIAS_ARQ = GEO / "IBGE_Divisao_Hidrografica.gpkg"
BACIAS_CAMADA = "micro_RH"
BACIAS_CAMPOS = {"nm_microRH": "Bacia", "nm_mesoRH": "Bacia_meso",
                 "nm_macroRH": "Regiao_Hidrografica"}

# ----------------------------------------------------------------------------
# Fontes das flags. Cada fonte vira uma coluna: valor = rótulo onde há
# sobreposição, '' onde não há. '{ver}' é trocado por vs22q / vs2224q.
# ----------------------------------------------------------------------------
def _fonte(campo, valor, arquivo, camada=None, where=None):
    return dict(campo=campo, valor=valor, arquivo=Path(arquivo),
                camada=camada, where=where)

_CAR_DISS = GEO / "Analise_Territorial_CAR-INCRA_dissolvido"
_CATS = (("Habilitado", "Habilitados", "Habilitado"),
         ("Analisado", "Analisados", "Analisado"),
         ("Nao_Analisado", "Nao_Analisados", "Não Analisado"))
_TEMAS = (("APP", "Tier9_APP"), ("RL", "Tier11_RL"), ("AUR", "Tier10_AUR"))
_RECOOP = C26 / "Tier1_Recooperar" / "P2_Recooperar_2026.gpkg"
_CNUC = GEO / "Unidades_Conservacao_CNUC20260507.gpkg"
_APA = "Área de Proteção Ambiental"
_RPPN = "Reserva Particular do Patrimônio Natural"

FONTES = [
    # --- CAR: três categorias (imóveis dissolvidos por UF, Maio/2026)
    _fonte("CAR_Habilitado", "Habilitado",
           _CAR_DISS / "CAR_Brasil_Maio26_Habilitado_Planaveg_dissolvido_UF.gpkg"),
    _fonte("CAR_Analisado", "Analisado",
           _CAR_DISS / "CAR_Brasil_Maio26_Selecionado_Analisado_dissolvido_UF.gpkg"),
    _fonte("CAR_Nao_Analisado", "Não Analisado",
           _CAR_DISS / "CAR_Brasil_Maio26_Selecionado_Não_Analisado_dissolvido_UF.gpkg"),
    # --- CAR em regularização ambiental (Junho/26; só AC, MT, PB, RJ, SP)
    _fonte("CAR_regularizacao", "Em regularização",
           C26 / "Tier3_CAR_Regularizacao" / "P2_CAR_Regularizacao_Junho26.gpkg",
           "P2_CAR_REGULARIZACAO_poligonos", "elegivel_computo = 1"),
]
# --- APP / RL / AUR por categoria (recortes P1 do cômputo, já cortados pela VS)
for _tema, _pasta in _TEMAS:
    for _suf, _cat, _rot in _CATS:
        FONTES.append(_fonte(
            f"{_tema}_{_suf}", f"{_tema} - {_rot}",
            C26 / _pasta / f"P1_{_tema}_CAR_Maio2026.gpkg",
            f"P1_{_tema}_{{ver}}", f"categoria = '{_cat}'"))
FONTES += [
    # --- Recooperar 2026 (elegíveis, regras D2-D4), por componente
    _fonte("Licenciamento_Ambiental", "Licenciamento", _RECOOP,
           "P2_RECOOPERAR_poligonos", "elegivel_computo = 1 AND categoria = 'licenciamento'"),
    _fonte("Reparacao_Danos", "Reparação", _RECOOP,
           "P2_RECOOPERAR_poligonos", "elegivel_computo = 1 AND categoria = 'reparacao'"),
    _fonte("Area_Embargada", "Embargo", _RECOOP,
           "P2_RECOOPERAR_poligonos", "elegivel_computo = 1 AND categoria = 'embargo'"),
    _fonte("Outras_Areas", "Outras Areas", _RECOOP,
           "P2_RECOOPERAR_poligonos", "elegivel_computo = 1 AND categoria = 'outras'"),
    # --- Outros projetos: embargos PANGIA (polígonos completos)
    _fonte("Embargo_PANGIA", "Embargo PANGIA",
           C26 / "Tier4_Outros_Projetos" / "P2_Outros_Projetos_PANGIA_20260920.gpkg",
           "P2_OUTROS_PROJETOS_poligonos"),
    # --- Observatório da Restauração: só OR 2026, elegíveis
    _fonte("ORR", "ORR", C26 / "Tier5_OR" / "P2_OR_2026.gpkg",
           "P2_OR_poligonos", "elegivel_computo = 1"),
    # --- Pró-Manguezal (camada original, não cortada pela VS)
    _fonte("Manguezal", "Pró-Manguezal", GEO / "Pro-Manguezal_IBAMA20260508.gpkg"),
    # --- Unidades de conservação (CNUC original)
    _fonte("APA", "APA", _CNUC, None, f"categoria = '{_APA}'"),
    _fonte("RPPN", "RPPN", _CNUC, None, f"categoria = '{_RPPN}'"),
    _fonte("UC", "UC", _CNUC, None, f"categoria NOT IN ('{_APA}', '{_RPPN}')"),
    _fonte("UC_federal", "Federal", _CNUC, None, "esfera = 'Federal'"),
    _fonte("UC_estadual", "Estadual", _CNUC, None, "esfera = 'Estadual'"),
    _fonte("UC_municipal", "Municipal", _CNUC, None, "esfera = 'Municipal'"),
    # --- Terras indígenas: mesmas 4 fases do cômputo
    _fonte("TI", "TI", GEO / "Terras_Indigenas_FUNAI20260507.gpkg", None,
           "fase_ti IN ('Regularizada', 'Homologada', 'Declarada', 'Delimitada')"),
    # --- INCRA
    _fonte("AS_", "AS", GEO / "Assentamentos_Rurais_INCRA20260610.gpkg"),
    _fonte("QL", "QL", GEO / "Territorios_Quilombolas_INCRA20260610.gpkg"),
]

CAR_COMPONENTES = ["CAR_Habilitado", "CAR_Analisado", "CAR_Nao_Analisado"]
PROJ_COMPONENTES = ["Licenciamento_Ambiental", "Reparacao_Danos", "Area_Embargada",
                    "Outras_Areas", "Embargo_PANGIA", "ORR", "Manguezal"]
# Mesma ordem de 2025 no campo Sobreposicao
TOKENS_SOBREPOSICAO = [("PROJ", "PROJ"), ("CAR", "CAR"), ("APA", "APA"),
                       ("RPPN", "RPPN"), ("UC", "UC"), ("TI", "TI"),
                       ("AS_", "AS"), ("QL", "QL")]

CAMPOS_HIER = ["hierarquia_planaveg", "tier", "categoria"]
CAMPOS_LOCAL = ["UF", "Bioma", "Municipio", "cod_municipio",
                "Bacia", "Bacia_meso", "Regiao_Hidrografica"]
CAMPOS_FLAG = [f["campo"] for f in FONTES]
COLUNAS_SAIDA = (CAMPOS_HIER + ["computo", "Area_ha"] + CAMPOS_LOCAL
                 + ["CAR"] + CAR_COMPONENTES + ["CAR_regularizacao"]
                 + [f"{t}_{s}" for t, _ in _TEMAS for s, _, _ in _CATS]
                 + ["PROJ"] + PROJ_COMPONENTES
                 + ["APA", "RPPN", "UC", "UC_federal", "UC_estadual", "UC_municipal",
                    "TI", "AS_", "QL", "Sobreposicao"])
CHAVES_DISSOLVE = [c for c in COLUNAS_SAIDA if c not in ("computo", "Area_ha")]


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
class Relogio:
    def __init__(self):
        self.t0 = time.time()

    def __call__(self, msg):
        print(f"  [{time.time() - self.t0:7.1f}s] {msg}", flush=True)


def camada_de(arquivo, camada=None, ver=None):
    if camada:
        return camada.format(ver=ver) if ver else camada
    return pyogrio.list_layers(arquivo)[0][0]


def campo_real(arquivo, camada, candidatos):
    campos = pyogrio.read_info(arquivo, layer=camada)["fields"]
    mapa = {c.upper(): c for c in campos}
    for cand in candidatos:
        if cand.upper() in mapa:
            return mapa[cand.upper()]
    raise KeyError(f"Nenhum de {candidatos} em {arquivo.name}:{camada} ({list(campos)})")


def bbox_geo(bounds_albers, folga_m=100.0):
    x0, y0, x1, y1 = bounds_albers
    return _ALB_PARA_GEO.transform_bounds(x0 - folga_m, y0 - folga_m,
                                          x1 + folga_m, y1 + folga_m, densify_pts=21)


def _explodir_poligonos(geom):
    """Desmonta Multi*/GeometryCollection (inclusive aninhadas) e devolve
    (partes, índice de origem) apenas com Polygon de área > 0."""
    geom = np.asarray(geom, dtype=object)
    idx = np.arange(len(geom))
    while True:
        tid = shapely.get_type_id(geom)
        multi = np.isin(tid, (4, 5, 6, 7))
        if not multi.any():
            break
        partes, pi = shapely.get_parts(geom[multi], return_index=True)
        geom = np.concatenate([geom[~multi], partes])
        idx = np.concatenate([idx[~multi], idx[multi][pi]])
    ok = (shapely.get_type_id(geom) == 3) & (shapely.area(geom) > 0)
    return geom[ok], idx[ok]


def _validar(geom):
    geom = np.asarray(shapely.force_2d(np.asarray(geom, dtype=object)), dtype=object)
    inval = ~shapely.is_valid(geom)
    if inval.any():
        geom[inval] = shapely.make_valid(geom[inval])
    return geom


def poligonos(gdf):
    """Explode para Polygon simples, válido, 2D e com área > 0."""
    gdf = gdf[~(gdf.geometry.isna() | gdf.geometry.is_empty)]
    # explode ANTES de validar: checar/corrigir milhões de partes pequenas é
    # muito mais rápido que validar um multipolígono gigante inteiro
    geom = np.asarray(shapely.force_2d(np.asarray(gdf.geometry.values, dtype=object)),
                      dtype=object)
    partes, idx = _explodir_poligonos(geom)
    partes, idx2 = _explodir_poligonos(_validar(partes))
    idx = idx[idx2]
    out = gdf.iloc[idx].copy()
    out = out.set_geometry(gpd.GeoSeries(partes, index=out.index, crs=gdf.crs))
    return out.reset_index(drop=True)


def uniao_segura(geoms):
    geoms = np.asarray(geoms, dtype=object)
    if len(geoms) == 1:
        g = geoms[0]
        return g if shapely.is_valid(g) else shapely.make_valid(g)
    try:
        return shapely.union_all(_validar(geoms))
    except shapely.errors.GEOSException:
        return shapely.union_all(_validar(geoms), grid_size=0.001)


def recorte(geoms, bounds):
    """clip_by_rect com fallback para intersection com a caixa (mais lento, robusto)."""
    geoms = np.asarray(geoms, dtype=object)
    try:
        return shapely.clip_by_rect(geoms, *bounds)
    except shapely.errors.GEOSException:
        caixa = shapely.box(*bounds)
        return np.array([_op_segura(shapely.intersection, [g], [caixa])[0] for g in geoms],
                        dtype=object)


MAX_VERTICES = 2000  # partes de máscara maiores que isso são subdivididas


def subdividir(geoms, janela=None, max_vert=MAX_VERTICES):
    """Recorta as partes pela janela (se dada) e subdivide recursivamente em
    quadrantes as que têm mais de max_vert vértices. Não altera a união da
    máscara; só a torna barata para recortes locais."""
    geoms = np.asarray(geoms, dtype=object)
    if janela is not None:
        fora = ~shapely.intersects(geoms, shapely.box(*janela))
        geoms = geoms[~fora]
        grandes = shapely.get_num_coordinates(geoms) > max_vert
        if grandes.any():
            geoms = np.concatenate([geoms[~grandes], recorte(geoms[grandes], janela)])
        geoms, _ = _explodir_poligonos(_validar(geoms))
    prontas, fila = [], [geoms]
    while fila:
        g = fila.pop()
        if len(g) == 0:
            continue
        grandes = shapely.get_num_coordinates(g) > max_vert
        prontas.append(g[~grandes])
        for geo in g[grandes]:
            x0, y0, x1, y1 = shapely.bounds(geo)
            xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
            quads = [(x0, y0, xm, ym), (xm, y0, x1, ym), (x0, ym, xm, y1), (xm, ym, x1, y1)]
            partes = np.concatenate([recorte([geo], q) for q in quads])
            partes, _ = _explodir_poligonos(_validar(partes))
            fila.append(partes)
    return np.concatenate(prontas) if prontas else np.empty(0, dtype=object)


def ler_camada(arquivo, camada, where=None, bbox=None, columns=None):
    return pyogrio.read_dataframe(arquivo, layer=camada, where=where, bbox=bbox,
                                  columns=columns)


def carregar_mascara(fonte, ver, bbox, janela_albers=None):
    """Polígonos da fonte na janela bbox (EPSG:4674), em Albers, como array shapely."""
    if not fonte["arquivo"].exists():
        raise FileNotFoundError(fonte["arquivo"])
    camada = camada_de(fonte["arquivo"], fonte["camada"], ver)
    gdf = ler_camada(fonte["arquivo"], camada, fonte["where"], bbox, columns=[])
    if gdf.empty:
        return np.empty(0, dtype=object)
    if gdf.crs is None:
        gdf = gdf.set_crs(CRS_GEO)
    gdf = poligonos(gdf.to_crs(ALBERS))
    return subdividir(np.asarray(gdf.geometry.values, dtype=object), janela_albers)


# ----------------------------------------------------------------------------
# Operações geométricas robustas
# ----------------------------------------------------------------------------
def _op_segura(func, a, b):
    """Aplica intersection/difference vetorizado; se falhar, elemento a elemento
    com make_valid e, em último caso, grid de 1 cm."""
    try:
        return func(a, b)
    except shapely.errors.GEOSException:
        out = np.empty(len(a), dtype=object)
        for i, (x, y) in enumerate(zip(a, b)):
            try:
                out[i] = func(x, y)
            except shapely.errors.GEOSException:
                x, y = shapely.make_valid(x), shapely.make_valid(y)
                try:
                    out[i] = func(x, y)
                except shapely.errors.GEOSException:
                    out[i] = func(x, y, grid_size=0.01)
        return out


def _novas_linhas(base, idx, geoms, campo=None, valor=None):
    novo = base.iloc[idx].copy()
    novo = novo.set_geometry(gpd.GeoSeries(geoms, index=novo.index, crs=base.crs))
    if campo is not None:
        novo[campo] = valor
    return novo


def dividir_por_mascara(base, mascara, campo, valor):
    """Identity de `base` com a união de `mascara`: partes dentro recebem
    campo=valor, partes fora mantêm o valor anterior. Conserva a área."""
    if len(base) == 0 or len(mascara) == 0:
        return base
    geoms = np.asarray(base.geometry.values, dtype=object)
    shapely.prepare(mascara)
    arvore = shapely.STRtree(mascara)
    bi, mi = arvore.query(geoms, predicate="intersects")
    if bi.size == 0:
        return base
    cobre = shapely.covers(mascara[mi], geoms[bi])
    inteiros = np.unique(bi[cobre])
    parciais = np.setdiff1d(np.unique(bi), inteiros)

    rotulo = base[campo].to_numpy(copy=True)
    rotulo[inteiros] = valor
    base = base.copy()
    base[campo] = rotulo
    if parciais.size == 0:
        return base

    sel = np.isin(bi, parciais)
    b2, m2 = bi[sel], mi[sel]
    ordem = np.argsort(b2, kind="stable")
    b2, m2 = b2[ordem], m2[ordem]
    cortes = np.flatnonzero(np.diff(b2)) + 1
    grupos_b = b2[np.r_[0, cortes]]
    grupos_m = np.split(m2, cortes)

    # máscara local de cada peça: partes candidatas recortadas pelo bbox da peça
    g = geoms[grupos_b]
    bx = shapely.bounds(g)
    locais = np.empty(len(grupos_b), dtype=object)
    for k, ms in enumerate(grupos_m):
        locais[k] = uniao_segura(recorte(mascara[ms], bx[k]))
    dentro = _op_segura(shapely.intersection, g, locais)
    fora = _op_segura(shapely.difference, g, locais)

    manter = base.drop(index=base.index[parciais])
    partes = [manter,
              _novas_linhas(base, grupos_b, dentro, campo, valor),
              _novas_linhas(base, grupos_b, fora)]
    out = pd.concat(partes, ignore_index=True)
    return poligonos(gpd.GeoDataFrame(out, geometry="geometry", crs=base.crs))


def atribuir_categorias(base, cats, campos):
    """Divide `base` pelos polígonos de `cats` (município, bacia) e copia
    `campos`. Sobreposições entre categorias não duplicam área: cada trecho
    vai para a primeira categoria encontrada. Sem categoria -> ''."""
    for c in campos:
        base[c] = ""
    if len(base) == 0 or len(cats) == 0:
        return base
    geoms = np.asarray(base.geometry.values, dtype=object)
    cgeo = np.asarray(cats.geometry.values, dtype=object)
    cval = cats[campos].to_numpy()
    shapely.prepare(cgeo)
    bi, ci = shapely.STRtree(cgeo).query(geoms, predicate="intersects")
    cobre = shapely.covers(cgeo[ci], geoms[bi])

    vals = base[campos].to_numpy(copy=True)
    b_cob, pos = np.unique(bi[cobre], return_index=True)
    vals[b_cob] = cval[ci[cobre][pos]]
    base = base.copy()
    base[campos] = vals

    parciais = np.setdiff1d(np.unique(bi), b_cob)
    if parciais.size == 0:
        return base
    sel = np.isin(bi, parciais)
    b2, c2 = bi[sel], ci[sel]
    ordem = np.argsort(b2, kind="stable")
    b2, c2 = b2[ordem], c2[ordem]
    cortes = np.flatnonzero(np.diff(b2)) + 1

    idx, geo_out, val_out = [], [], []
    for b, cs in zip(b2[np.r_[0, cortes]], np.split(c2, cortes)):
        resto = geoms[b]
        bx = shapely.bounds(resto)
        for c in cs:
            cg = uniao_segura(recorte([cgeo[c]], bx))
            parte = _op_segura(shapely.intersection, [resto], [cg])[0]
            if shapely.area(parte) > 0:
                idx.append(b); geo_out.append(parte); val_out.append(cval[c])
                resto = _op_segura(shapely.difference, [resto], [cg])[0]
            if shapely.is_empty(resto):
                break
        if not shapely.is_empty(resto) and shapely.area(resto) > 0:
            idx.append(b); geo_out.append(resto); val_out.append([""] * len(campos))

    manter = base.drop(index=base.index[parciais])
    novo = _novas_linhas(base, np.array(idx), np.array(geo_out, dtype=object))
    novo[campos] = np.array(val_out, dtype=object)
    out = pd.concat([manter, novo], ignore_index=True)
    return poligonos(gpd.GeoDataFrame(out, geometry="geometry", crs=base.crs))


def derivar_campos(gdf):
    """CAR (qualquer categoria), PROJ (qualquer projeto) e Sobreposicao."""
    gdf["CAR"] = np.where((gdf[CAR_COMPONENTES] != "").any(axis=1), "CAR", "")
    gdf["PROJ"] = np.where((gdf[PROJ_COMPONENTES] != "").any(axis=1), "PROJ", "")
    sob = pd.Series("", index=gdf.index)
    for campo, token in TOKENS_SOBREPOSICAO:
        sob = sob + np.where(gdf[campo] != "", token, "")
    gdf["Sobreposicao"] = sob
    return gdf


def arquivo_uf(ver, uf):
    return SAIDA_UF / f"Visualizacao_{ver}_{uf}.gpkg"


def camada_uf(ver, uf):
    return f"Visualizacao_{ver}_{uf}"
