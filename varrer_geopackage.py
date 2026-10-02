"""
varrer_geopackage.py - Varredura da pasta GEOPACKAGE antes da organização para entrega

SÓ LÊ. Não apaga, não move, não altera nada. Percorre a pasta inteira (inclusive as
pastas de vegetação secundária) e classifica cada arquivo candidato em:

  1_TEMPORARIO    pode ser apagado com o QGIS/ArcGIS e os scripts FECHADOS
                  (-wal/-shm/-journal do SQLite, travas do Office, .tmp, marcadores
                  de retomada, heartbeat, __pycache__, cópias em conflito do Dropbox)
  2_LOG           registros de execução: arquivar (zip) ou apagar depois da entrega
  3_INTERMEDIARIO pastas/arquivos de apoio ou versões substituídas: REVISAR antes
  4_DUPLICADO     mesmo nome-base com sufixo "_com_area" e MESMO tamanho: REVISAR
  5_VAZIO         arquivos de 0 byte e pastas vazias
  6_GRANDE_2GB    GeoPackages > 2 GB (o ArcGIS falha acima de ~2 GB): avaliar
                  divisão antes da entrega ao cliente (não é para apagar)

Uso (qualquer ambiente com Python 3):
  python varrer_geopackage.py
  python varrer_geopackage.py "D:\\outra\\pasta"
Saída: varredura_geopackage.csv (na pasta do script) + resumo no console.
"""
import csv
import fnmatch
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

RAIZ = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"C:\Users\User\Dropbox\#CONSULTANCY\PLANAVEG\GEODATABASE\GEOPACKAGE")
SAIDA = Path(__file__).with_name("varredura_geopackage.csv")
LIMITE_GRANDE = 2 * 1024**3

TEMPORARIOS = ["*.gpkg-wal", "*.gpkg-shm", "*.sqlite-wal", "*.sqlite-shm", "*-journal",
               "*.tmp", "*.temp", "~$*", ".~lock.*", "*.lock", "*.bak", "*.pyc",
               "heartbeat_*.txt", "_done_*.txt", "Thumbs.db", ".DS_Store",
               "*conflicted copy*", "*cópia em conflito*", "*copia em conflito*"]
PASTAS_TEMPORARIAS = ["__pycache__", ".ipynb_checkpoints"]
LOGS = ["*.log", "_log*.txt", "*_log.txt", "_run_*_stdout.txt", "*stdout*.txt",
        "*stderr*.txt", "_progresso*.json", "inventario_*.txt"]
PASTAS_LOG = ["_logs", "_progresso"]
# pastas e arquivos de apoio do processamento (revisar, não apagar às cegas)
PASTAS_INTERMEDIARIAS = ["_apoio_nuvem", "_por_uf", "_tmp", "tmp", "temp", "_cache"]
ARQUIVOS_INTERMEDIARIOS = [
    ("IN_OR_2025*", "OR 2025 substituído pelo ORR 2026 no cômputo"),
    ("P2_OR_2025*", "OR 2025 substituído pelo ORR 2026 no cômputo"),
    ("CAR_Brasil_Junho26_Habilitado_Planaveg_dissolvido_UF.gpkg",
     "o cômputo e a visualização usaram a versão Maio26"),
]


def casa(nome, padroes):
    n = nome.lower()
    return any(fnmatch.fnmatch(n, p.lower()) for p in padroes)


def tamanho_pasta(p):
    total = 0
    for r, _, fs in os.walk(p):
        for f in fs:
            try:
                total += os.path.getsize(os.path.join(r, f))
            except OSError:
                pass
    return total


def main():
    if not RAIZ.exists():
        raise SystemExit(f"Pasta não encontrada: {RAIZ}")
    linhas = []

    def add(cat, caminho, tam, motivo, tipo="arquivo"):
        try:
            mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(caminho)))
        except OSError:
            mtime = ""
        linhas.append(dict(categoria=cat, tipo=tipo, caminho=str(caminho),
                           tamanho_MB=round(tam / 1024**2, 2), modificado=mtime, motivo=motivo))

    pastas_marcadas = []
    por_dir = defaultdict(list)
    n_arq = 0
    for raiz, dirs, arqs in os.walk(RAIZ):
        r = Path(raiz)
        vazia = not dirs and not arqs
        # pastas inteiras: registra uma vez e não desce nelas
        for d in list(dirs):
            nome = d.lower()
            alvo = r / d
            if nome in [x.lower() for x in PASTAS_TEMPORARIAS]:
                add("1_TEMPORARIO", alvo, tamanho_pasta(alvo), "cache do Python", "pasta")
                dirs.remove(d)
            elif nome in [x.lower() for x in PASTAS_LOG]:
                add("2_LOG", alvo, tamanho_pasta(alvo), "pasta de logs de execução", "pasta")
                pastas_marcadas.append(alvo)
            elif nome in [x.lower() for x in PASTAS_INTERMEDIARIAS]:
                add("3_INTERMEDIARIO", alvo, tamanho_pasta(alvo),
                    "pasta de apoio/parciais do processamento (há versão consolidada?)", "pasta")
                pastas_marcadas.append(alvo)
        if vazia and r != RAIZ:
            add("5_VAZIO", r, 0, "pasta vazia", "pasta")
        dentro_marcada = any(m in r.parents or m == r for m in pastas_marcadas)
        for a in arqs:
            n_arq += 1
            p = r / a
            try:
                tam = p.stat().st_size
            except OSError:
                continue
            por_dir[r].append((a, tam))
            if casa(a, TEMPORARIOS):
                motivo = ("arquivo auxiliar do SQLite: só apagar com o GeoPackage FECHADO"
                          if a.lower().endswith(("-wal", "-shm", "-journal"))
                          else "temporário / trava / marcador de execução")
                if "conflit" in a.lower():
                    motivo = "cópia em conflito do Dropbox: comparar com o original"
                add("1_TEMPORARIO", p, tam, motivo)
            elif dentro_marcada:
                continue  # já contado na pasta
            elif casa(a, LOGS):
                add("2_LOG", p, tam, "registro de execução")
            elif tam == 0:
                add("5_VAZIO", p, 0, "arquivo de 0 byte")
            else:
                for padrao, motivo in ARQUIVOS_INTERMEDIARIOS:
                    if casa(a, [padrao]):
                        add("3_INTERMEDIARIO", p, tam, motivo)
                        break
            if a.lower().endswith(".gpkg") and tam > LIMITE_GRANDE:
                add("6_GRANDE_2GB", p, tam, "GeoPackage > 2 GB: ArcGIS pode não abrir")

    # duplicados "_com_area" com o mesmo tamanho do original
    for r, lista in por_dir.items():
        tam_por_nome = {n.lower(): t for n, t in lista}
        for n, t in lista:
            base, ext = os.path.splitext(n)
            if base.lower().endswith("_com_area"):
                orig = (base[: -len("_com_area")] + ext).lower()
                if orig in tam_por_nome:
                    igual = tam_por_nome[orig] == t
                    add("4_DUPLICADO", r / n, t,
                        f"existe {base[:-9]}{ext} "
                        + ("com o MESMO tamanho (provável cópia)" if igual
                           else "com tamanho diferente (versão com campo de área?)"))

    linhas.sort(key=lambda x: (x["categoria"], x["caminho"]))
    with open(SAIDA, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()) if linhas else ["categoria"],
                           delimiter=";")
        w.writeheader()
        w.writerows(linhas)

    print(f"Pasta: {RAIZ}\n{n_arq:,} arquivos percorridos\n")
    resumo = defaultdict(lambda: [0, 0.0])
    for l in linhas:
        resumo[l["categoria"]][0] += 1
        resumo[l["categoria"]][1] += l["tamanho_MB"]
    for cat in sorted(resumo):
        n, mb = resumo[cat]
        print(f"  {cat:16s} {n:6,} itens  {mb / 1024:8.2f} GB")
    print(f"\nDetalhe: {SAIDA}  (separador ';', abre direto no Excel)")
    print("Nada foi apagado.")


if __name__ == "__main__":
    main()
