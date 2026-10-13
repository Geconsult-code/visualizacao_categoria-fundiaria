"""
quarentena_geopackage.py - move para a quarentena os temporários, logs e intermediários
da pasta GEOPACKAGE, mantendo a mesma estrutura de pastas (para restaurar se preciso).

Itens (decididos em 02/10/2026):
  - marcadores _done_*.txt
  - logs (_log*.txt, _progresso*.json, pastas _logs): antes de mover, são copiados para
    GEOPACKAGE\\Registros_Processamento.zip, que FICA na pasta
  - pastas _por_uf (Visualizacao, Tier9_APP, Tier10_AUR, Tier11_RL) e _apoio_nuvem
  - OR 2025 substituído pelo ORR 2026 (IN_OR_2025*, P2_OR_2025.gpkg)
  - ORR_Observatorio_Restauracao_2025_com_area.gpkg (conteúdo idêntico ao original)
  - Planaveg_2025_Projetos_ORR/Outros/Recooperar_com_area.gpkg (Area_ha recalculado;
    os originais são o reporte 2025 entregue)
Mantidos por decisão: CAR_Brasil_Junho26_Habilitado... e os cruzamentos VS sem qualificação.

Uso (feche QGIS/ArcGIS antes):
  python quarentena_geopackage.py              # SIMULAÇÃO: só mostra o que faria
  python quarentena_geopackage.py --executar   # cria o zip e move para F:\\PLANAVEG_quarentena
  python quarentena_geopackage.py --restaurar  # devolve tudo à origem, pelo manifesto
Cada item é copiado, conferido (nº de arquivos e bytes) e só então apagado da origem.
"""
import argparse
import csv
import os
import shutil
import sys
import time
import zipfile
from pathlib import Path

ORIGEM = Path(r"C:\Users\User\Dropbox\#CONSULTANCY\PLANAVEG\GEODATABASE\GEOPACKAGE")
DESTINO = Path(r"F:\PLANAVEG_quarentena")
C26 = "Computo_Planaveg_2026"

PASTAS = [
    f"{C26}/Visualizacao/_por_uf",
    f"{C26}/Tier9_APP/_por_uf",
    f"{C26}/Tier10_AUR/_por_uf",
    f"{C26}/Tier11_RL/_por_uf",
    f"{C26}/_apoio_nuvem",
]
ARQUIVOS = [
    f"{C26}/Insumos/IN_OR_2025.gpkg",
    f"{C26}/Insumos/IN_OR_2025_VS.gpkg",
    f"{C26}/Insumos/IN_OR_2025_excluidos.csv",
    f"{C26}/Insumos/IN_OR_2025_resumo.csv",
    f"{C26}/Tier5_OR/P2_OR_2025.gpkg",
    "ORR_Observatorio_Restauracao_2025_com_area.gpkg",
    "Computo_Planaveg_2025/Planaveg_2025_Projetos_ORR_com_area.gpkg",
    "Computo_Planaveg_2025/Planaveg_2025_Projetos_Outros_com_area.gpkg",
    "Computo_Planaveg_2025/Planaveg_2025_Projetos_Recooperar_com_area.gpkg",
]
PADROES_MARCADOR = ["_done_*.txt"]
PADROES_LOG = ["_log*.txt", "_progresso*.json"]
PASTAS_LOG = ["_logs"]
NOME_ZIP = "Registros_Processamento.zip"
NOME_MANIFESTO = "_manifesto_quarentena.csv"


def medir(p):
    if p.is_file():
        return 1, p.stat().st_size
    n = b = 0
    for r, _, fs in os.walk(p):
        for f in fs:
            n += 1
            b += os.path.getsize(os.path.join(r, f))
    return n, b


def dentro_de(p, pastas):
    return any(q == p or q in p.parents for q in pastas)


def montar_lista(origem):
    pastas_inteiras = [origem / p for p in PASTAS if (origem / p).exists()]
    itens = [(p, "intermediario") for p in pastas_inteiras]
    itens += [(origem / a, "intermediario") for a in ARQUIVOS if (origem / a).exists()]
    faltam = [p for p in PASTAS + ARQUIVOS if not (origem / p).exists()]
    logs = []
    for padrao in PADROES_MARCADOR:
        for p in origem.rglob(padrao):
            if not dentro_de(p, pastas_inteiras):
                itens.append((p, "marcador"))
    for padrao in PADROES_LOG:
        for p in origem.rglob(padrao):
            if not dentro_de(p, pastas_inteiras):
                itens.append((p, "log")); logs.append(p)
    for nome in PASTAS_LOG:
        for p in origem.rglob(nome):
            if p.is_dir() and not dentro_de(p, pastas_inteiras):
                itens.append((p, "log")); logs.append(p)
    # remove itens contidos em outros itens já listados
    pastas_lista = [p for p, _ in itens if p.is_dir()]
    itens = [(p, t) for p, t in itens if not dentro_de(p, [q for q in pastas_lista if q != p])]
    return sorted(set(itens)), logs, faltam


def criar_zip(origem, logs):
    destino_zip = origem / NOME_ZIP
    with zipfile.ZipFile(destino_zip, "a" if destino_zip.exists() else "w",
                         compression=zipfile.ZIP_DEFLATED) as z:
        ja = set(z.namelist())
        for p in logs:
            arquivos = [p] if p.is_file() else [Path(r) / f for r, _, fs in os.walk(p) for f in fs]
            for a in arquivos:
                nome = a.relative_to(origem).as_posix()
                if nome not in ja:
                    z.write(a, nome)
    return destino_zip


def mover(src, dst):
    """Copia, confere nº de arquivos e bytes, e só então apaga a origem."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)
    if medir(src) != medir(dst):
        raise IOError(f"cópia não confere: {medir(src)} x {medir(dst)}")
    if src.is_dir():
        shutil.rmtree(src)
    else:
        src.unlink()


def executar(origem, destino, simular):
    itens, logs, faltam = montar_lista(origem)
    total = sum(medir(p)[1] for p, _ in itens)
    print(f"Origem:  {origem}\nDestino: {destino}\n")
    for p, t in itens:
        n, b = medir(p)
        print(f"  [{t:13s}] {b / 1024**2:10.1f} MB  {p.relative_to(origem)}"
              + ("  (pasta, %d arquivos)" % n if p.is_dir() else ""))
    print(f"\n{len(itens)} itens, {total / 1024**3:.2f} GB")
    if faltam:
        print("Não encontrados (já removidos?): " + ", ".join(faltam))
    if simular:
        print("\nSIMULAÇÃO: nada foi alterado. Rode com --executar para mover.")
        return
    livre = shutil.disk_usage(destino.anchor).free
    if livre < total * 1.05:
        raise SystemExit(f"Espaço insuficiente em {destino.anchor}: "
                         f"{livre / 1024**3:.1f} GB livres, precisa de {total / 1024**3:.1f} GB")
    destino.mkdir(parents=True, exist_ok=True)
    if logs:
        z = criar_zip(origem, logs)
        print(f"\nLogs copiados para {z.name} ({z.stat().st_size / 1024**2:.1f} MB), que fica na origem.")
    manifesto = destino / NOME_MANIFESTO
    novo = not manifesto.exists()
    ok = falhas = 0
    with open(manifesto, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        if novo:
            w.writerow(["origem", "destino", "tipo", "categoria", "tamanho_MB", "data"])
        for p, t in itens:
            alvo = destino / p.relative_to(origem)
            n, b = medir(p)
            try:
                mover(p, alvo)
                w.writerow([p, alvo, "pasta" if n > 1 or alvo.is_dir() else "arquivo", t,
                            round(b / 1024**2, 2), time.strftime("%Y-%m-%d %H:%M")])
                f.flush()
                ok += 1
                print(f"  movido: {p.relative_to(origem)}")
            except Exception as e:  # noqa: BLE001
                falhas += 1
                print(f"  FALHOU: {p.relative_to(origem)} -> {e}  (arquivo aberto em QGIS/ArcGIS?)")
    print(f"\n{ok} itens movidos, {falhas} falhas. Manifesto: {manifesto}")


def restaurar(destino):
    manifesto = destino / NOME_MANIFESTO
    if not manifesto.exists():
        raise SystemExit(f"Manifesto não encontrado: {manifesto}")
    with open(manifesto, encoding="utf-8-sig") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    for l in linhas:
        src, dst = Path(l["destino"]), Path(l["origem"])
        if src.exists():
            mover(src, dst)
            print(f"  restaurado: {dst}")
        else:
            print(f"  já não está na quarentena: {src}")
    print("Restauração concluída.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--executar", action="store_true")
    ap.add_argument("--restaurar", action="store_true")
    ap.add_argument("--origem", default=str(ORIGEM))
    ap.add_argument("--destino", default=str(DESTINO))
    a = ap.parse_args()
    origem, destino = Path(a.origem), Path(a.destino)
    if a.restaurar:
        restaurar(destino)
    else:
        if not origem.exists():
            raise SystemExit(f"Origem não encontrada: {origem}")
        executar(origem, destino, simular=not a.executar)


if __name__ == "__main__":
    main()
