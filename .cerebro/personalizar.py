# -*- coding: utf-8 -*-
"""personalizar.py: llena los marcadores de CLAUDE.md con tus datos (lo llaman setup.ps1 y setup.sh).

    python .cerebro/personalizar.py --nombre "Ana" --clave "Actualiza" --fuentes "C:\\Users\\ana\\Documents;D:\\Escuela"

Se escribe con Python y UTF-8 para que los acentos no se rompan (PowerShell en línea los corrompe).
Se puede volver a correr: si ya no quedan marcadores, no cambia nada.
"""
import argparse
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nombre", required=True)
    ap.add_argument("--clave", default="Actualiza")
    ap.add_argument("--fuentes", default="", help="carpetas separadas por ; (opcional)")
    a = ap.parse_args()
    fuentes = [f.strip() for f in a.fuentes.split(";") if f.strip()]
    lista = "\n".join(f"- `{f}`" for f in fuentes) or "- (ninguna todavía: agrega aquí las carpetas que quieras que lea la actualización)"
    p = os.path.join(RAIZ, "CLAUDE.md")
    with open(p, encoding="utf-8") as f:
        s = f.read()
    if "{{NOMBRE}}" not in s:
        print("CLAUDE.md ya estaba personalizado; no cambié nada.")
        return
    s = s.replace("{{NOMBRE}}", a.nombre.strip()).replace("{{CLAVE}}", a.clave.strip()).replace("{{FUENTES}}", lista)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)
    print(f"CLAUDE.md listo: nombre {a.nombre.strip()!r}, clave {a.clave.strip()!r}, {len(fuentes)} carpetas de fuentes.")


if __name__ == "__main__":
    main()
