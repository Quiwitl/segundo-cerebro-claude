# -*- coding: utf-8 -*-
"""cerrar.py: el cierre de la actualización en un solo comando, en orden, con un reporte corto.

Pasos (se detiene en el primero que falle; nada se sube a git si `verificar` da errores):
    0. hot.md                   deja las 3 entradas más recientes de «Last Updated» (las demás ya están en log.md)
    1. hipocampo.py indexar     ids de notas nuevas + pendientes (resúmenes viejos, duplicados)
    2. vault.py indice          index.md y los _index.md
    3. vault.py verificar       debe dar 0 errores
    4. conectoma.py             Mapa del cerebro (y lo mueve a wiki/meta/)
    5. physarum.py              esqueleto de la red, alimentado por uso.jsonl
   5b. espacio.py               datos de la vista 3D (no detiene el cierre si falla)
    6. hipocampo.py indexar     mapas de wiki/hipocampo/ con las regiones nuevas
    7. hipocampo.py catalogo    .cerebro/salida/catalogo-project.md (para el Project)
   7b. hipocampo.py evaluar --solo-medir   puntería del buscador, sin cambiar el modo
   7c. --costo                 una línea en .cerebro/costos.jsonl (llamadas, tokens, USD de la sesión)
    8. vault.py estado          solo si se pasa --corte
    9. git add, commit y push   salvo --sin-git

Uso, desde la raíz del vault:
    python .cerebro/cerrar.py --corte 2026-10-19T21:46 --chats id1,id2 --nota "Historial ..." -m "actualizacion: ..."
    python .cerebro/cerrar.py --sin-red --sin-git      solo índices y verificación (rápido)
conectoma.py y physarum.py necesitan networkx, numpy y matplotlib: se corren con `uv run` si está
instalado; si no, con este mismo Python (si tiene esas bibliotecas).
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
PY = sys.executable
REPORTE = []


def correr(nombre, cmd, cortar_si_falla=True):
    r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    salida = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0 and cortar_si_falla:
        print("\n".join(REPORTE))
        print(f"✗ {nombre} falló (código {r.returncode}):\n{salida.strip()[-2000:]}")
        sys.exit(1)
    return r.returncode, salida


def con_red(script, libs):
    """Comando para un script que necesita bibliotecas fuera de la estándar."""
    if shutil.which("uv"):
        cmd = ["uv", "run", "--no-project"]
        for lib in libs:
            cmd += ["--with", lib]
        return cmd + ["python", script]
    faltan = [lib for lib in libs if importlib.util.find_spec(lib) is None]
    if faltan:
        return None
    return [PY, script]


def rotar_hot(conservar=3):
    """Deja en «Last Updated» de hot.md solo las entradas más recientes.

    Una entrada vieja solo sale si log.md ya tiene una entrada de ese día; si no, se queda.
    """
    hot = os.path.join(RAIZ, "wiki", "hot.md")
    with open(hot, encoding="utf-8") as f:
        t = f.read()
    with open(os.path.join(RAIZ, "wiki", "log.md"), encoding="utf-8") as f:
        dias_log = set(re.findall(r"^## \[(\d{4}-\d\d-\d\d)\]", f.read(), re.M))
    m = re.search(r"^## Last Updated\n(.*?)(?=^## )", t, re.M | re.S)
    if not m:
        return "sin sección «Last Updated»"
    bloques = [b for b in re.split(r"\n\s*\n", m.group(1).strip()) if b.strip()]
    entradas = [b for b in bloques if re.match(r"\d{4}-\d\d-\d\d\b", b)]
    otros = [b for b in bloques if b not in entradas]
    quedan = entradas[:conservar] + [b for b in entradas[conservar:] if b[:10] not in dias_log]
    salen = len(entradas) - len(quedan)
    if not salen:
        return f"{len(entradas)} entradas, nada que rotar"
    nuevo = "## Last Updated\n\n" + "\n\n".join(otros + quedan) + "\n\n"
    t = t[:m.start()] + nuevo + t[m.end():]
    t = re.sub(r"^updated: .*$", "updated: " + dt.date.today().isoformat(), t, count=1, flags=re.M)
    with open(hot, "w", encoding="utf-8", newline="\n") as f:
        f.write(t)
    return f"{salen} entradas viejas fuera de «Last Updated» (ya estaban en log.md); quedan {len(quedan)}"


def linea(texto, patron):
    m = re.search(patron, texto, re.M)
    return m.group(0).strip() if m else ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corte", help="fecha y hora de esta actualización, p. ej. 2026-10-19T21:46")
    ap.add_argument("--chats", default="", help="ids de chats integrados, separados por comas")
    ap.add_argument("--nota", default="", help="nota fuente donde quedaron esos chats")
    ap.add_argument("-m", "--mensaje", help="mensaje del commit")
    ap.add_argument("--sin-red", action="store_true", help="no correr conectoma ni physarum")
    ap.add_argument("--sin-git", action="store_true", help="no hacer commit ni push")
    ap.add_argument("--costo", help='costo de la sesión en JSON, p. ej. {"llamadas": 37, "usd": 4.18}')
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    REPORTE.append("✓ hot.md: " + rotar_hot())
    _, s = correr("hipocampo indexar", [PY, ".cerebro/hipocampo.py", "indexar"])
    REPORTE.append("✓ hipocampo: " + linea(s, r"^\d+ notas.*$"))
    for patron in (r"^Resúmenes viejos.*$", r"^Sin description: \d+", r"^Posibles duplicados.*$"):
        x = linea(s, patron)
        if x and not x.endswith(": 0"):
            REPORTE.append("  ! " + x + "  → ver `hipocampo.py pendientes`")

    correr("vault indice", [PY, ".cerebro/vault.py", "indice"])
    codigo, s = correr("vault verificar", [PY, ".cerebro/vault.py", "verificar"], cortar_si_falla=False)
    resumen = linea(s, r"^\d+ notas · .*$").split(" · privadas")[0]
    if codigo != 0:
        print("\n".join(REPORTE))
        print("✗ verificar encontró errores; no se sigue (nada se subió):")
        print("\n".join(l for l in s.splitlines() if l.startswith("ERROR"))[:3000])
        sys.exit(1)
    REPORTE.append("✓ índice y verificación: " + resumen)

    if a.sin_red:
        REPORTE.append("· conectoma y physarum: omitidos (--sin-red)")
    else:
        cmd = con_red(".cerebro/conectoma.py", ["networkx"])
        if cmd is None:
            REPORTE.append("! conectoma y physarum: falta networkx (instala uv o `pip install networkx numpy matplotlib`)")
        else:
            _, s = correr("conectoma", cmd + [RAIZ, "--salida", os.path.join(".cerebro", "salida")])
            os.replace(os.path.join(AQUI, "salida", "Mapa del cerebro.md"),
                       os.path.join(RAIZ, "wiki", "meta", "Mapa del cerebro.md"))
            REPORTE.append("✓ conectoma: " + linea(s, r"^notas=.*$"))
            cmd = con_red(".cerebro/physarum.py", ["networkx", "numpy", "matplotlib"])
            if cmd is None:
                REPORTE.append("! physarum: faltan numpy o matplotlib")
            else:
                _, s = correr("physarum", cmd)
                REPORTE.append("✓ " + linea(s, r"^Physarum:.*$"))
                with open(os.path.join(RAIZ, "wiki", "meta", "Physarum del vault.md"), encoding="utf-8") as f:
                    fuentes = linea(f.read(), r"^Fuentes de alimento:.*$")
                if fuentes:
                    REPORTE.append("  " + fuentes.split(";")[0])
        cmd = con_red(".cerebro/espacio.py", ["networkx", "numpy", "scipy"])
        if cmd is None:
            REPORTE.append("! espacio (vista 3D): faltan numpy o scipy")
        else:
            codigo, s = correr("espacio", cmd, cortar_si_falla=False)
            REPORTE.append("✓ espacio: vista 3D al día" if codigo == 0 else
                           "! espacio falló (no detiene el cierre): " + s.strip()[-200:])
        correr("hipocampo indexar (mapas)", [PY, ".cerebro/hipocampo.py", "indexar", "--hook"])
        # el conectoma puede reagrupar regiones y borrar mapas que el índice ya enlazaba
        # (24 y 26 oct): se rehace el índice con los mapas nuevos y se verifica otra vez
        correr("vault indice (tras mapas)", [PY, ".cerebro/vault.py", "indice"])
        codigo, s = correr("vault verificar (tras mapas)", [PY, ".cerebro/vault.py", "verificar"], cortar_si_falla=False)
        if codigo != 0:
            print("\n".join(REPORTE))
            print("✗ verificar encontró errores después de regenerar los mapas; no se sigue (nada se subió):")
            print("\n".join(l for l in s.splitlines() if l.startswith("ERROR"))[:3000])
            sys.exit(1)

    _, s = correr("catálogo", [PY, ".cerebro/hipocampo.py", "catalogo"])
    REPORTE.append("✓ " + linea(s, r"^catálogo.*$"))

    codigo, s = correr("evaluar", [PY, ".cerebro/hipocampo.py", "evaluar", "--solo-medir"], cortar_si_falla=False)
    if codigo == 0:
        partes = re.findall(r"^(\S+)\s+aciertos en top 3: (\d+/\d+)", s, re.M)
        modo = linea(s, r"modo actual: \w+")
        REPORTE.append("✓ puntería (top 3): " + " · ".join(f"{m} {x}" for m, x in partes) + (f" · {modo}" if modo else ""))
    else:
        REPORTE.append("! evaluar falló (no detiene el cierre)")

    if a.costo:
        try:
            costo = json.loads(a.costo)
        except ValueError:
            REPORTE.append("! --costo no es JSON válido; no se registró")
        else:
            costo = {"fecha": a.corte or dt.datetime.now().isoformat(timespec="minutes"), **costo}
            with open(os.path.join(AQUI, "costos.jsonl"), "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(costo, ensure_ascii=False) + "\n")
            REPORTE.append("✓ costo: " + " · ".join(f"{k} {v}" for k, v in costo.items() if k != "fecha"))

    if a.corte:
        cmd = [PY, ".cerebro/vault.py", "estado", "--corte", a.corte]
        if a.chats:
            cmd += ["--chats", a.chats]
        if a.nota:
            cmd += ["--nota", a.nota]
        _, s = correr("estado", cmd)
        REPORTE.append("✓ estado: " + s.strip().splitlines()[-1])

    if a.sin_git:
        REPORTE.append("· git: omitido (--sin-git)")
    else:
        mensaje = a.mensaje or f"actualizacion: cierre {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        correr("git add", ["git", "add", "-A"])
        codigo, s = correr("git commit", ["git", "commit", "-q", "-m", mensaje], cortar_si_falla=False)
        if codigo != 0 and "nothing to commit" not in s and "nada para hacer commit" not in s:
            print("\n".join(REPORTE))
            print("✗ git commit falló:\n" + s.strip()[-1500:])
            sys.exit(1)
        codigo_push, salida_push = correr("git push", ["git", "push", "-q"], cortar_si_falla=False)
        _, s = correr("git status", ["git", "status", "-sb"])
        cabeza = s.splitlines()[0] if s else ""
        if codigo_push != 0 or "ahead" in cabeza or "adelante" in cabeza or "..." not in cabeza:
            REPORTE.append(f"✗ git: commit hecho pero el push falló ({cabeza.strip('# ')}); el vault NO está respaldado"
                           + (f"\n    {salida_push.strip()[-300:]}" if salida_push.strip() else ""))
        else:
            _, h = correr("git log", ["git", "log", "--oneline", "-1"])
            REPORTE.append("✓ git: respaldado en GitHub · " + h.strip())

    print("\n".join(REPORTE))


if __name__ == "__main__":
    main()
