"""
viz_comum.py - Atributos de visualização do cômputo Planaveg 2026
Configuração (caminhos, fontes, textos, esquema de saída) e funções geométricas
compartilhadas pelos scripts 1 a 4.

v2.0.0 (23/10/2026) - esquema da planilha "Planaveg_2026_total_VS2224_mapeamento_atributos_visualizacao"
e respostas de 23/10/2026 (Instrucoes_Visualizacao.docx):
- Entrada: Reporte_Final/Planaveg_2026_Total.gpkg (vs22q e vs2224q; sem PANGIA, com FUNBIO na classe 4).
- Fragmentação por UF, município e bacia (micro/meso/macro RH); área planar Albers IBGE; saída 2D;
  slivers < 1 m² descartados e registrados.
- hierarquia_planaveg com os nomes novos; na classe 4, um nome por origem (ICMBio GEF Terrestre,
  ICMBio Restauração Ecológica, FUNBIO). Nome_Abreviado e Nome_Detalhado (tool tip) por classe;
  na classe 1, pela categoria do projeto Recooperar.
- Flags do próprio tier (leitura B): CAR só nas classes 3, 9, 10 e 11; PROJ só nas 1, 2, 4 e 5; UC só na 7;
  TI só na 6; Manguezal só na 8. APA, RPPN, AS e QL continuam marcando a sobreposição em qualquer classe.
- CAR_Condicao (era categoria) nas classes 3 e 9-11; PROJ_Categoria nas 1, 2, 4 e 5; UC_Nome, UC_Manejo e
  UC_Esfera na 7 e TI_Nome na 6, com TODAS as UCs/TIs que contêm a peça, separadas por "; ".
- Sobreposicao: como antes (sobreposição em qualquer classe), tokens PROJ, CAR, APA, RPPN, UC, MANG, TI, AS, QL.
- Eliminados: computo, categoria e as flags de componente (CAR_<situação>, APP/RL/AUR_<situação>,
  Recooperar por categoria, MonitoRAD, Embargo_PANGIA, GEF_Terrestre, Restauracao_Ecologica, ORR,
  UC_federal/estadual/municipal). Campos internos (prefixo _) só existem durante o processamento.
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
# PLANAVEG_C26 permite usar um cômputo regerado em outra pasta (ex.: D:\PLANAVEG_TEMP)
C26 = Path(os.environ.get("PLANAVEG_C26", str(GEO / "Computo_Planaveg_2026")))
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
# Fontes do identity. Cada fonte marca um campo (valor = rótulo onde há sobreposição, '' onde não há);
# várias fontes podem marcar o mesmo campo. Campos com prefixo _ são internos. '{ver}' -> vs22q / vs2224q.
# ----------------------------------------------------------------------------
def _fonte(campo, valor, arquivo, camada=None, where=None):
    return dict(campo=campo, valor=valor, arquivo=Path(arquivo), camada=camada, where=where)


_CAR_DISS = next((p / "Analise_Territorial_CAR-INCRA_dissolvido" for p in (GEO, C26.parent)
                  if (p / "Analise_Territorial_CAR-INCRA_dissolvido").is_dir()),
                 GEO / "Analise_Territorial_CAR-INCRA_dissolvido")
_RECOOP = C26 / "Tier1_Recooperar" / "P2_Recooperar_2026.gpkg"
_T4 = C26 / "Tier4_Outros_Projetos" / "P2_Outros_Projetos_2026.gpkg"
_CNUC = GEO / "Unidades_Conservacao_CNUC20260507.gpkg"
_FUNAI = GEO / "Terras_Indigenas_FUNAI20260507.gpkg"
_APA = "Área de Proteção Ambiental"
_RPPN = "Reserva Particular do Patrimônio Natural"
_UC_WHERE = "limite = 'uc'"            # sem zona de amortecimento, como no cômputo
_TI_WHERE = "fase_ti IN ('Regularizada', 'Homologada', 'Declarada', 'Delimitada')"
FONTES_T4 = {"ICMBio_GEF_Terrestre_2026": "Outros Projetos ICMBio_GEF Terrestre",
             "ICMBio_Restauracao_2026": "Outros Projetos ICMBio_Restauração Ecológica",
             "FUNBIO_2026": "Outros Projetos FUNBIO"}
CATEGORIAS_RECOOPERAR = ("licenciamento", "reparacao", "embargo", "outras")

FONTES = [
    # --- CAR (qualquer situação) - só para o token CAR da Sobreposicao
    _fonte("_CAR", "CAR", _CAR_DISS / "CAR_Brasil_Maio26_Habilitado_Planaveg_dissolvido_UF.gpkg"),
    _fonte("_CAR", "CAR", _CAR_DISS / "CAR_Brasil_Maio26_Selecionado_Analisado_dissolvido_UF.gpkg"),
    _fonte("_CAR", "CAR", _CAR_DISS / "CAR_Brasil_Maio26_Selecionado_Não_Analisado_dissolvido_UF.gpkg"),
    _fonte("_CAR", "CAR", C26 / "Tier3_CAR_Regularizacao" / "P2_CAR_Regularizacao_Junho26.gpkg",
           "P2_CAR_REGULARIZACAO_poligonos", "elegivel_computo = 1"),
    # --- projetos (qualquer camada de projeto da hierarquia 2026) - token PROJ
    _fonte("_PROJ", "PROJ", _RECOOP, "P2_RECOOPERAR_poligonos", "elegivel_computo = 1"),
    _fonte("_PROJ", "PROJ", C26 / "Tier2_MonitoRAD" / "P2_MonitoRAD_2026.gpkg", "P2_MONITORAD_poligonos",
           "elegivel_computo = 1"),
    _fonte("_PROJ", "PROJ", C26 / "Insumos" / "IN_ICMBio_2026.gpkg", "IN_ICMBIO"),
    _fonte("_PROJ", "PROJ", C26 / "Insumos" / "IN_FUNBIO_2026.gpkg", "IN_FUNBIO"),
    _fonte("_PROJ", "PROJ", C26 / "Tier5_OR" / "P2_OR_2026.gpkg", "P2_OR_poligonos", "elegivel_computo = 1"),
]
# --- categoria do Recooperar (classe 1): polígonos líquidos da própria classe, disjuntos
FONTES += [_fonte("_rec_cat", c, _RECOOP, "P2_RECOOPERAR", f"categoria = '{c}'") for c in CATEGORIAS_RECOOPERAR]
# --- origem da classe 4: polígonos líquidos da própria classe, por fonte
FONTES += [_fonte("_t4_fonte", f, _T4, "P2_OUTROS_PROJETOS_{ver}", f"fonte = '{f}'") for f in FONTES_T4]
FONTES += [
    _fonte("_MANG", "MANG", GEO / "Pro-Manguezal_IBAMA20260508.gpkg"),
    _fonte("APA", "APA", _CNUC, None, f"{_UC_WHERE} AND categoria = '{_APA}'"),
    _fonte("RPPN", "RPPN", _CNUC, None, f"{_UC_WHERE} AND categoria = '{_RPPN}'"),
    _fonte("_UC_outras", "UC", _CNUC, None, f"{_UC_WHERE} AND categoria NOT IN ('{_APA}', '{_RPPN}')"),
    _fonte("_TI", "TI", _FUNAI, None, _TI_WHERE),
    _fonte("AS", "AS", GEO / "Assentamentos_Rurais_INCRA20260610.gpkg"),
    _fonte("QL", "QL", GEO / "Territorios_Quilombolas_INCRA20260610.gpkg"),
]
CAMPOS_FLAG = list(dict.fromkeys(f["campo"] for f in FONTES))

# Rótulos individuais (classe 7: UCs; classe 6: TIs) - todos os polígonos que contêm a peça
ROTULOS = {
    "UC": dict(arquivo=_CNUC, camada=None, where=_UC_WHERE, tier=7,
               campos=["cd_cnuc", "nome_uc", "grupo", "esfera", "categoria", "cria_ano"]),
    "TI": dict(arquivo=_FUNAI, camada=None, where=_TI_WHERE, tier=6,
               campos=["terrai_cod", "terrai_nom", "fase_ti"]),
}
SEP = "; "

# ----------------------------------------------------------------------------
# Textos (planilha de mapeamento, com a ortografia corrigida em 23/10/2026)
# ----------------------------------------------------------------------------
HIERARQUIA = {
    1: "Projetos do Programa Recooperar",
    2: "Projetos do Programa MonitoRAD",
    3: "Projetos de Regularização Ambiental em Imóvel Rural - CAR",
    5: "Projetos do Observatório da Restauração",
    6: "Vegetação Secundária em Territórios Indígenas",
    7: "Vegetação Secundária em Unidades de Conservação",
    8: "Vegetação Secundária em Área de Manguezais",
    9: "Vegetação Secundária em Área de Preservação Permanente - APP",
    10: "Vegetação Secundária em Área de Uso Restrito - AUR",
    11: "Vegetação Secundária em Reserva Legal - RL",
}   # classe 4: FONTES_T4 (um nome por origem)
_DET_EMB = "Áreas em recuperação por Processos de Embargo"
NOMES_RECOOPERAR = {   # categoria -> (abreviado, detalhado, PROJ_Categoria)
    "licenciamento": ("Licenciamento Ambiental", "Áreas em recuperação por Processos de Licenciamento Ambiental",
                      "Licenciamento_Ambiental"),
    "reparacao": ("Reparação por Danos", "Áreas em recuperação por Processos de Reparação de Danos", "Reparação_Danos"),
    "embargo": ("Embargadas", _DET_EMB, "Área_Embargada"),
    "outras": ("Outras Áreas", "Áreas em recuperação por outros instrumentos do Recooperar", "Outras_Áreas"),
}
NOMES = {   # tier -> (abreviado, detalhado)
    2: ("Embargadas", _DET_EMB),
    3: ("Regularização Ambiental - CAR", "Área de APP, AUR e RL em Imóveis Rurais na condição "
                                         "\"Analisado, em regularização ambiental (Lei nº 12.651/2012)\""),
    4: ("Outros Projetos", "Outras áreas de projetos não incluídas nas demais categorias"),
    5: ("Outros Projetos", "Outras áreas de projetos não incluídas nas demais categorias"),
    6: ("Territórios Indígenas", "Terras Indígenas e Reservas Indígenas cadastradas na FUNAI"),
    7: ("Unidades de Conservação", "Unidades de Conservação cadastradas no CNUC"),
    8: ("Manguezais", "Manguezais mapeados pelo Programa Pró-Manguezal"),
    9: ("APP", "Área de Preservação Permanente"),
    10: ("AUR", "Área de Uso Restrito"),
    11: ("RL", "Reserva Legal"),
}
PROJ_CATEGORIA = {2: "Área_Embargada", 4: "Outras_Áreas", 5: "Outras_Áreas"}   # classe 1: NOMES_RECOOPERAR
CAR_CONDICAO_T3 = "Imóveis Rurais na seguinte condição: Analisado, em regularização ambiental (Lei nº 12.651/2012)"
CAR_CONDICAO = {   # categoria do cômputo (classes 9-11) -> texto
    "Habilitados": ("Imóveis Rurais nas seguintes condições: Analisado, aguardando regularização ambiental "
                    "(Lei nº 12.651/2012); ou Analisado, em conformidade com a Lei nº 12.651/2012, e analisado sem "
                    "pendências; ou Analisado, em conformidade com a Lei nº 12.651/2012, com ativos ambientais; ou "
                    "Analisado em regularização"),
    "Analisados": "Imóveis Rurais na seguinte condição: Analisado, aguardando atendimento a notificação",
    "Nao_Analisados": "Imóveis Rurais na seguinte condição: Aguardando Análise ou Em Análise",
}
CATEGORIA_DE_CONDICAO = {v: k for k, v in CAR_CONDICAO.items()}
UC_MANEJO = {"Proteção Integral": "Proteção_Integral", "Uso Sustentável": "Uso_Sustentável"}
UC_ESFERA = {"Federal": "UC_Federal", "Estadual": "UC_Estadual", "Municipal": "UC_Municipal"}
TIERS_CAR, TIERS_PROJ = (3, 9, 10, 11), (1, 2, 4, 5)

TOKENS_SOBREPOSICAO = [("_PROJ", "PROJ"), ("_CAR", "CAR"), ("APA", "APA"), ("RPPN", "RPPN"),
                       ("_UC_outras", "UC"), ("_MANG", "MANG"), ("_TI", "TI"), ("AS", "AS"), ("QL", "QL")]

CAMPOS_LOCAL = ["UF", "Bioma", "Municipio", "cod_municipio", "Bacia", "Bacia_meso", "Regiao_Hidrografica"]
COLUNAS_SAIDA = (["hierarquia_planaveg", "tier", "Nome_Abreviado", "Nome_Detalhado", "Area_ha"] + CAMPOS_LOCAL
                 + ["CAR", "CAR_Condicao", "PROJ", "PROJ_Categoria", "Manguezal", "APA", "RPPN",
                    "UC", "UC_Nome", "UC_Manejo", "UC_Esfera", "TI", "TI_Nome", "AS", "QL", "Sobreposicao"])
CAMPOS_TEXTO = [c for c in COLUNAS_SAIDA if c not in ("tier", "Area_ha")]
CHAVES_DISSOLVE = [c for c in COLUNAS_SAIDA if c != "Area_ha"]

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


def subdividir_gdf(gdf, janela=None, max_vert=MAX_VERTICES):
    """subdividir() para camadas com atributos (municípios, bacias)."""
    if gdf.empty:
        return gdf
    linhas, geoms = [], []
    for i, g in enumerate(gdf.geometry.values):
        partes = subdividir([g], janela, max_vert)
        linhas += [i] * len(partes)
        geoms += list(partes)
    out = gdf.iloc[linhas].copy()
    return out.set_geometry(gpd.GeoSeries(geoms, index=out.index, crs=gdf.crs)).reset_index(drop=True)


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




def mais_proximo(geoms, alvos):
    """Para cada geometria, (índice do alvo mais próximo, distância); -1/inf se não houver."""
    geoms = np.asarray(geoms, dtype=object)
    idx = np.full(len(geoms), -1)
    dist = np.full(len(geoms), np.inf)
    if len(alvos) == 0 or len(geoms) == 0:
        return idx, dist
    (gi, ai), d = shapely.STRtree(alvos).query_nearest(geoms, return_distance=True,
                                                       all_matches=False)
    idx[gi], dist[gi] = ai, d
    return idx, dist


def _poligonos_fonte(fonte, ver, bbox):
    camada = camada_de(fonte["arquivo"], fonte["camada"], ver)
    gdf = ler_camada(fonte["arquivo"], camada, fonte["where"], bbox, columns=[])
    if gdf.empty:
        return np.empty(0, dtype=object)
    if gdf.crs is None:
        gdf = gdf.set_crs(CRS_GEO)
    return np.asarray(poligonos(gdf.to_crs(ALBERS)).geometry.values, dtype=object)


FOLGAS_BUSCA_M = (2_000, 50_000, 500_000, 5_000_000)


def imputar_mais_proximo(gdf, selecao, campos, ver):
    """Nas peças selecionadas, marca o campo cuja fonte tem o polígono mais
    próximo (distância 0 = toca). Amplia a busca até achar alguma fonte.
    Devolve DataFrame com campo, n_pecas, area_ha, dist_max_m."""
    idx = np.flatnonzero(selecao)
    if idx.size == 0:
        return pd.DataFrame()
    geoms = np.asarray(gdf.geometry.values, dtype=object)[idx]
    caixa = shapely.total_bounds(geoms)
    fontes = [f for f in FONTES if f["campo"] in campos]
    for folga in FOLGAS_BUSCA_M:
        bbox = bbox_geo(caixa, folga)
        dists = np.vstack([mais_proximo(geoms, _poligonos_fonte(f, ver, bbox))[1]
                           for f in fontes])
        dmin = dists.min(axis=0)
        # só é o mais próximo de fato se nada mais perto pode estar fora da caixa
        if np.isfinite(dmin).all() and dmin.max() <= folga:
            break
    escolha = dists.argmin(axis=0)
    ok = np.isfinite(dists.min(axis=0))
    linhas = []
    for k, f in enumerate(fontes):
        m = ok & (escolha == k)
        if m.any():
            gdf.loc[gdf.index[idx[m]], f["campo"]] = f["valor"]
            linhas.append(dict(campo=f["campo"], n_pecas=int(m.sum()),
                               area_ha=float(shapely.area(geoms[m]).sum() / 1e4),
                               dist_max_m=float(dists[k, m].max())))
    if (~ok).any():
        linhas.append(dict(campo="(nenhuma fonte encontrada)", n_pecas=int((~ok).sum()),
                           area_ha=float(shapely.area(geoms[~ok]).sum() / 1e4),
                           dist_max_m=np.nan))
    return pd.DataFrame(linhas)




def _tier(gdf):
    return pd.to_numeric(gdf["tier"], errors="coerce").round().fillna(-1).astype(int).to_numpy()


def _marcar(gdf, sel, campo, valor):
    m = np.asarray(sel) & (gdf[campo].to_numpy() == "")
    if m.any():
        gdf.loc[m, campo] = valor
    return int(m.sum())


def forcar_flags_internas(gdf):
    """A peça está na classe porque está na fonte: garante o token do próprio tier (bordas podem escapar do
    identity por diferença de projeção). Devolve {(campo, tier): (n, ha)}."""
    tier = _tier(gdf)
    cont = {}
    area = shapely.area(np.asarray(gdf.geometry.values, dtype=object)) / 1e4
    for campo, valor, tiers in (("_PROJ", "PROJ", TIERS_PROJ), ("_CAR", "CAR", TIERS_CAR), ("_TI", "TI", (6,)),
                                ("_MANG", "MANG", (8,))):
        for t in tiers:
            sel = (tier == t) & (gdf[campo].to_numpy() == "")
            if sel.any():
                cont[(campo, t)] = (int(sel.sum()), float(area[sel].sum()))
                gdf.loc[sel, campo] = valor
    return gdf, cont


def grupos_de_imputacao(gdf):
    """(nome, seleção, campo): peças da classe sem a origem própria recebem a fonte mais próxima."""
    tier = _tier(gdf)
    return [("classe 1 sem categoria do Recooperar", (tier == 1) & (gdf["_rec_cat"] == "").to_numpy(), "_rec_cat"),
            ("classe 4 sem origem", (tier == 4) & (gdf["_t4_fonte"] == "").to_numpy(), "_t4_fonte")]


# ----------------------------------------------------------------------------
# Rótulos individuais (UC_Nome, TI_Nome): todos os polígonos que contêm cada trecho
# ----------------------------------------------------------------------------
def carregar_rotulos(chave, bbox):
    """(geoms em Albers - partes simples -, id do polígono de origem por parte, tabela de atributos por id)."""
    r = ROTULOS[chave]
    camada = camada_de(r["arquivo"], r["camada"])
    gdf = ler_camada(r["arquivo"], camada, r["where"], bbox, columns=r["campos"])
    if gdf.empty:
        return np.empty(0, dtype=object), np.empty(0, dtype=int), gdf.drop(columns="geometry")
    if gdf.crs is None:
        gdf = gdf.set_crs(CRS_GEO)
    gdf = gdf.reset_index(drop=True)
    gdf["_id"] = np.arange(len(gdf))
    tab = gdf.drop(columns="geometry").set_index("_id")
    p = poligonos(gdf.to_crs(ALBERS))
    return np.asarray(p.geometry.values, dtype=object), p["_id"].to_numpy(), tab


def rotular(base, sel, alvos, ids):
    """Divide as peças selecionadas pela sobreposição com os polígonos `alvos` (partes de origem `ids`) e grava em
    `_lab` a tupla (ordenada) dos ids que contêm cada trecho. Peças não selecionadas ficam com (). Conserva a área."""
    base = base.copy()
    base["_lab"] = [()] * len(base)
    idx = np.flatnonzero(sel)
    if idx.size == 0 or len(alvos) == 0:
        return base
    geoms = np.asarray(base.geometry.values, dtype=object)
    shapely.prepare(alvos)
    pi, ai = shapely.STRtree(alvos).query(geoms[idx], predicate="intersects")
    if pi.size == 0:
        return base
    bi = idx[pi]
    cobre = shapely.covers(alvos[ai], geoms[bi])
    ordem = np.argsort(bi, kind="stable")
    bi, ai, cobre = bi[ordem], ai[ordem], cobre[ordem]
    cortes = np.flatnonzero(np.diff(bi)) + 1
    lab = base["_lab"].to_numpy(copy=True)
    divididas, novas_idx, novas_geo, novas_lab = [], [], [], []
    for b, a_s, c_s in zip(bi[np.r_[0, cortes]], np.split(ai, cortes), np.split(cobre, cortes)):
        inteiros = set(ids[a_s[c_s]].tolist())
        parciais = sorted(set(ids[a_s[~c_s]].tolist()) - inteiros)
        if not parciais:
            lab[b] = tuple(sorted(inteiros))
            continue
        bx = shapely.bounds(geoms[b])
        partes = [(geoms[b], inteiros)]
        for uid in parciais:
            mask = uniao_segura(recorte(alvos[a_s[ids[a_s] == uid]], bx))
            novo = []
            for g, ls in partes:
                dentro = _op_segura(shapely.intersection, [g], [mask])[0]
                fora = _op_segura(shapely.difference, [g], [mask])[0]
                if not shapely.is_empty(dentro) and shapely.area(dentro) > 0:
                    novo.append((dentro, ls | {uid}))
                if not shapely.is_empty(fora) and shapely.area(fora) > 0:
                    novo.append((fora, ls))
            partes = novo
        divididas.append(b)
        for g, ls in partes:
            novas_idx.append(b); novas_geo.append(g); novas_lab.append(tuple(sorted(ls)))
    base["_lab"] = lab
    if not divididas:
        return base
    manter = base.drop(index=base.index[divididas])
    novo = _novas_linhas(base, np.array(novas_idx), np.array(novas_geo, dtype=object))
    novo["_lab"] = novas_lab
    out = pd.concat([manter, novo], ignore_index=True)
    return poligonos(gpd.GeoDataFrame(out, geometry="geometry", crs=base.crs))


def rotular_vazios_mais_proximo(base, sel, alvos, ids):
    """Peças selecionadas sem rótulo (bordas) recebem o polígono mais próximo. Devolve (base, n, ha, dist_max)."""
    vaz = np.flatnonzero(np.asarray(sel) & np.array([len(x) == 0 for x in base["_lab"]]))
    if vaz.size == 0 or len(alvos) == 0:
        return base, int(vaz.size), 0.0, np.nan
    geoms = np.asarray(base.geometry.values, dtype=object)[vaz]
    i, d = mais_proximo(geoms, alvos)
    lab = base["_lab"].to_numpy(copy=True)
    for k, j in zip(vaz, i):
        if j >= 0:
            lab[k] = (int(ids[j]),)
    base = base.copy()
    base["_lab"] = lab
    return base, int(vaz.size), float(shapely.area(geoms).sum() / 1e4), float(d[i >= 0].max()) if (i >= 0).any() else np.nan


def textos_uc(tab, labs):
    """(UC_Nome, UC_Manejo, UC_Esfera, tem_APA, tem_RPPN, tem_outras) por tupla de ids; ordem: proteção integral,
    fora da APA, federal > estadual > municipal, mais antiga, nome."""
    cache = {}
    ordem_g = {"Proteção Integral": 0, "Uso Sustentável": 1}
    ordem_e = {"Federal": 0, "Estadual": 1, "Municipal": 2}
    out = []
    for t in labs:
        if t not in cache:
            if not t:
                cache[t] = ("", "", "", False, False, False)
            else:
                s = tab.loc[list(t)].copy()
                s["_k"] = list(zip(s["grupo"].map(ordem_g).fillna(9), (s["categoria"] == _APA).astype(int),
                                   s["esfera"].map(ordem_e).fillna(9), pd.to_numeric(s["cria_ano"], errors="coerce").fillna(9999),
                                   s["nome_uc"].astype(str)))
                s = s.sort_values("_k")
                uniq = lambda v: SEP.join(dict.fromkeys(x for x in v if x))  # noqa: E731
                cache[t] = (uniq(s["nome_uc"].astype(str).str.strip()), uniq(s["grupo"].map(UC_MANEJO).fillna("")),
                            uniq(s["esfera"].map(UC_ESFERA).fillna("")), bool((s["categoria"] == _APA).any()),
                            bool((s["categoria"] == _RPPN).any()), bool((~s["categoria"].isin([_APA, _RPPN])).any()))
        out.append(cache[t])
    return out


def textos_ti(tab, labs):
    cache = {}
    out = []
    for t in labs:
        if t not in cache:
            cache[t] = SEP.join(dict.fromkeys(tab.loc[list(t), "terrai_nom"].astype(str).str.strip().sort_values())) if t else ""
        out.append(cache[t])
    return out


def derivar_saida(gdf):
    """Colunas de saída a partir do tier, da categoria do cômputo e dos campos internos."""
    tier = _tier(gdf)
    cat = gdf["categoria"].to_numpy()
    rec = gdf["_rec_cat"].to_numpy()
    t4 = gdf["_t4_fonte"].to_numpy()
    n = len(gdf)
    hier = np.array([HIERARQUIA.get(t, "") for t in tier], dtype=object)
    hier[tier == 4] = [FONTES_T4.get(x, "") for x in t4[tier == 4]]
    ab = np.array([NOMES.get(t, ("", ""))[0] for t in tier], dtype=object)
    de = np.array([NOMES.get(t, ("", ""))[1] for t in tier], dtype=object)
    pc = np.array([PROJ_CATEGORIA.get(t, "") for t in tier], dtype=object)
    m1 = tier == 1
    ab[m1] = [NOMES_RECOOPERAR.get(x, ("", "", ""))[0] for x in rec[m1]]
    de[m1] = [NOMES_RECOOPERAR.get(x, ("", "", ""))[1] for x in rec[m1]]
    pc[m1] = [NOMES_RECOOPERAR.get(x, ("", "", ""))[2] for x in rec[m1]]
    cond = np.full(n, "", dtype=object)
    cond[tier == 3] = CAR_CONDICAO_T3
    mc = np.isin(tier, (9, 10, 11))
    cond[mc] = [CAR_CONDICAO.get(x, "") for x in cat[mc]]
    gdf["hierarquia_planaveg"] = hier
    gdf["Nome_Abreviado"] = ab
    gdf["Nome_Detalhado"] = de
    gdf["CAR"] = np.where(np.isin(tier, TIERS_CAR), "CAR", "")
    gdf["CAR_Condicao"] = cond
    gdf["PROJ"] = np.where(np.isin(tier, TIERS_PROJ), "PROJ", "")
    gdf["PROJ_Categoria"] = pc
    gdf["Manguezal"] = np.where(tier == 8, "Pró-Manguezal", "")
    gdf["UC"] = np.where(tier == 7, "UC", "")
    gdf["TI"] = np.where(tier == 6, "TI", "")
    sob = pd.Series("", index=gdf.index)
    for campo, token in TOKENS_SOBREPOSICAO:
        sob = sob + np.where(gdf[campo] != "", token, "")
    gdf["Sobreposicao"] = sob
    return gdf


def completar_colunas(gdf):
    for c in COLUNAS_SAIDA:
        if c not in gdf.columns:
            gdf[c] = ""
    return gdf[COLUNAS_SAIDA + [gdf.geometry.name]]


def arquivo_uf(ver, uf):
    return SAIDA_UF / f"Visualizacao_{ver}_{uf}.gpkg"


def camada_uf(ver, uf):
    return f"Visualizacao_{ver}_{uf}"
