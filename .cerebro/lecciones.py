# -*- coding: utf-8 -*-
"""lecciones.py: dopamina para la memoria procedimental de Claude.

Cada línea de «Lo esencial» (Claude - método) y de «Correcciones recurrentes» lleva un id
y dos contadores al final, como comentario de Obsidian (no se ve en lectura):

    1. **Acentos**: escribir archivos con Python ... %%E01 +3 -0%%

+n = veces que la línea ayudó; -m = veces que estorbó o llevó a un error. Idea tomada de
ACE (Agentic Context Engineering, ICLR 2026): viñetas con id y contadores, actualizadas por
deltas, nunca reescribiendo la nota entera (reescribirla la colapsa y pierde lo útil).

    python .cerebro/lecciones.py numerar          pone id y contadores a las líneas que no los tienen
    python .cerebro/lecciones.py marcar E01 +     la línea ayudó en esta sesión
    python .cerebro/lecciones.py marcar C04 -     la línea estorbó o llevó a un error
    python .cerebro/lecciones.py listar           todas, con sus contadores
    python .cerebro/lecciones.py listar --alertas solo las que estorbaron más de lo que ayudaron

No cambia `updated`: un contador no es una edición del contenido.
"""
import argparse
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
ARCHIVOS = {
    "E": ("wiki/meta/claude/Claude - método.md", "## Lo esencial", re.compile(r"^\d+\. ")),
    "C": ("wiki/meta/claude/lecciones/Correcciones recurrentes.md", None, re.compile(r"^- ")),
}
MARCA = re.compile(r"\s*%%([EC])(\d+) \+(\d+) -(\d+)%%\s*$")


def _leer(rel):
    with open(os.path.join(RAIZ, rel), encoding="utf-8") as f:
        return f.read().split("\n")


def _escribir(rel, lineas):
    p = os.path.join(RAIZ, rel)
    tmp = p + ".tmp-lecciones"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lineas))
    os.replace(tmp, p)


def _rango(lineas, seccion):
    """Índices de las líneas del cuerpo donde viven las lecciones (sin frontmatter)."""
    inicio = 0
    if lineas and lineas[0].strip() == "---":
        inicio = next(i for i in range(1, len(lineas)) if lineas[i].strip() == "---") + 1
    fin = len(lineas)
    if seccion:
        inicio = next(i for i in range(inicio, len(lineas)) if lineas[i].strip() == seccion) + 1
        fin = next((i for i in range(inicio, len(lineas)) if lineas[i].startswith("## ")), len(lineas))
    return range(inicio, fin)


def _items():
    """[(prefijo, rel, índice de línea, id o None, +n, -m, texto)]"""
    out = []
    for pre, (rel, seccion, patron) in ARCHIVOS.items():
        ls = _leer(rel)
        for i in _rango(ls, seccion):
            if not patron.match(ls[i]):
                continue
            m = MARCA.search(ls[i])
            texto = MARCA.sub("", ls[i])
            if m:
                out.append((pre, rel, i, f"{m.group(1)}{m.group(2)}", int(m.group(3)), int(m.group(4)), texto))
            else:
                out.append((pre, rel, i, None, 0, 0, texto))
    return out


def numerar():
    nuevos = 0
    for pre, (rel, _, _) in ARCHIVOS.items():
        items = [x for x in _items() if x[0] == pre]
        mayor = max((int(x[3][1:]) for x in items if x[3]), default=0)
        ls = _leer(rel)
        for _, _, i, ident, _, _, texto in items:
            if ident is None:
                mayor += 1
                ls[i] = f"{texto.rstrip()} %%{pre}{mayor:02d} +0 -0%%"
                nuevos += 1
        _escribir(rel, ls)
    print(f"numeradas: {nuevos} líneas nuevas")


def marcar(ident, signo):
    ident = ident.upper()
    for pre, rel, i, idx, mas, menos, texto in _items():
        if idx == ident:
            if signo == "+":
                mas += 1
            else:
                menos += 1
            ls = _leer(rel)
            ls[i] = f"{texto.rstrip()} %%{ident} +{mas} -{menos}%%"
            _escribir(rel, ls)
            print(f"{ident} +{mas} -{menos}  {texto[:70]}")
            return
    sys.exit(f"No encontré {ident}. Corre `lecciones.py listar` o `numerar`.")


def listar(alertas=False):
    n = 0
    for pre, rel, i, idx, mas, menos, texto in _items():
        if alertas and not (menos > mas):
            continue
        n += 1
        aviso = "  ← estorba más de lo que ayuda: revisar en la actualización" if menos > mas else ""
        print(f"{idx or '(sin id)'} +{mas} -{menos}  {texto.strip()[:90]}{aviso}")
    if alertas:
        print(f"Lecciones que estorban: {n}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("numerar")
    m = sub.add_parser("marcar"); m.add_argument("id"); m.add_argument("signo", choices=["+", "-"])
    l = sub.add_parser("listar"); l.add_argument("--alertas", action="store_true")
    a = ap.parse_args()
    if a.cmd == "numerar":
        numerar()
    elif a.cmd == "marcar":
        marcar(a.id, a.signo)
    else:
        listar(a.alertas)


if __name__ == "__main__":
    main()
