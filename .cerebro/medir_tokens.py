# -*- coding: utf-8 -*-
"""medir_tokens.py: cuánto lee Claude para encontrar cada nota de preguntas.json, con y sin hipocampo.

Simula, sin gastar tokens reales, tres formas de buscar y cuenta lo que Claude tendría
que leer (salida de comandos y notas abiertas) hasta llegar a la nota esperada:

  grep        a ciegas: lista de archivos que contienen las palabras y abrir notas
              completas, de la que más coincide a la que menos, hasta dar con la buena (máx. 5)
  antes       el flujo anterior: `vault.py descripciones` completo y abrir la nota correcta completa
              (optimista: supone que Claude elige bien a la primera)
  hipocampo   `hipocampo.py buscar` y abrir la candidata correcta con límite de 15 líneas;
              si la nota esperada no sale, se suma el costo del flujo anterior (fallo honesto)

Tokens estimados como caracteres / 3.5 (texto en español con markdown); el ahorro en
porcentaje casi no depende del tokenizador. Uso:
    python .cerebro/medir_tokens.py [preguntas.json] [--completa]   --completa: la nota se lee entera también con hipocampo
Escribe .cerebro/salida/tokens.json.
"""
import contextlib
import io
import json
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import hipocampo as h  # noqa: E402
import vault  # noqa: E402

CHARS_POR_TOKEN = 3.5
MAX_ABRIR = 5


def tok(s):
    return round(len(s) / CHARS_POR_TOKEN)


CUERPO = 5  # líneas que se leen desde donde empieza el cuerpo (lo que antes se alcanzaba a ver en 15)


def lectura(rel, limite=None, desde=1):
    """Lo que devuelve la herramienta Read: cada línea con su número."""
    lineas = vault.leer(vault.abs_(rel)).split("\n")[desde - 1:]
    if limite:
        lineas = lineas[:limite]
    return "".join(f"{i:6d}\t{l}\n" for i, l in enumerate(lineas, desde))


def salida(f, *a, **k):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        f(*a, **k)
    return buf.getvalue()


def main():
    completa = "--completa" in sys.argv
    inicio = "--inicio" in sys.argv  # el flujo anterior: 15 líneas desde el principio, con frontmatter
    archivo = next((x for x in sys.argv[1:] if not x.startswith("--")), h.PREGUNTAS)
    with open(archivo, encoding="utf-8") as f:
        qs = json.load(f)
    qs = qs["preguntas"] if isinstance(qs, dict) else qs
    d, _ = h.sincronizar(mapas=False)
    rutas = [e["ruta"] for e in d["notas"].values()]
    textos = {r: h.plano(vault.leer(vault.abs_(r))) for r in rutas}
    descripciones = salida(vault.descripciones)
    filas = []
    for q in qs:
        esperadas = {h.resolver(n, d)[1]["ruta"] for n in q["esperadas"] if h.resolver(n, d)[1]}
        meta = sorted(esperadas)[0]
        # --- grep a ciegas
        palabras = [w for w in h.palabras(q["pregunta"]) if len(w) >= 4] or h.palabras(q["pregunta"])
        conteo = sorted(((sum(textos[r].count(w) for w in palabras), r) for r in rutas), reverse=True)
        con = [r for c, r in conteo if c > 0]
        costo_g = tok("\n".join("wiki/" + r + ".md" for r in con))
        ok_g = False
        for r in con[:MAX_ABRIR]:
            costo_g += tok(lectura(r))
            if r in esperadas:
                ok_g = True
                break
        # --- antes: descripciones + nota completa
        costo_a = tok(descripciones) + tok(lectura(meta))
        # --- hipocampo: buscar + candidata (15 líneas o completa)
        out = salida(h.buscar, q["pregunta"])
        filas_b = [l.split(" | ") for l in out.splitlines() if " | " in l]
        cand = [x[0] for x in filas_b]
        hallada = next((r for r in cand if r in esperadas), None)
        costo_h = tok(out)
        if hallada:
            desde = int(next(x[1] for x in filas_b if x[0] == hallada)[2:])
            if completa:
                costo_h += tok(lectura(hallada))
            elif inicio:
                costo_h += tok(lectura(hallada, 15))
            else:
                costo_h += tok(lectura(hallada, CUERPO, desde))
        else:
            costo_h += costo_a  # no la encontró: se cae al flujo anterior
        filas.append({"pregunta": q["pregunta"], "nota": meta, "grep": costo_g, "grep_ok": ok_g,
                      "antes": costo_a, "hipocampo": costo_h, "hipocampo_ok": bool(hallada)})
    total = {k: sum(f[k] for f in filas) for k in ("grep", "antes", "hipocampo")}
    claude_antes = None
    p_antes = os.path.join(h.RAIZ, ".tools", "CLAUDE-antes.md")
    if os.path.exists(p_antes):
        claude_antes = tok(open(p_antes, encoding="utf-8-sig").read())
    claude_hoy = tok(vault.leer(os.path.join(h.RAIZ, "CLAUDE.md")))
    res = {"modo_lectura": "completa" if completa else "15 líneas desde el inicio" if inicio else f"{CUERPO} líneas desde el cuerpo", "preguntas": len(filas), "filas": filas,
           "total": total, "claude_md": {"antes": claude_antes, "hoy": claude_hoy},
           "chars_por_token": CHARS_POR_TOKEN}
    os.makedirs(h.SALIDA, exist_ok=True)
    with open(os.path.join(h.SALIDA, "tokens.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(f"{'pregunta':45s} {'grep':>6s} {'antes':>6s} {'hipo':>6s}")
    for f in filas:
        print(f"{f['pregunta'][:45]:45s} {f['grep']:6d}{'' if f['grep_ok'] else '*'} {f['antes']:6d} {f['hipocampo']:6d}{'' if f['hipocampo_ok'] else '*'}")
    n = len(filas)
    print(f"\nPromedio por búsqueda: grep {total['grep'] / n:.0f} · antes {total['antes'] / n:.0f} · hipocampo {total['hipocampo'] / n:.0f} tokens")
    print(f"Ahorro del hipocampo: {100 * (1 - total['hipocampo'] / total['antes']):.0f} % contra antes, "
          f"{100 * (1 - total['hipocampo'] / total['grep']):.0f} % contra grep")
    print(f"Encontradas: grep {sum(f['grep_ok'] for f in filas)}/{n} · hipocampo {sum(f['hipocampo_ok'] for f in filas)}/{n} (* = no la encontró)")
    if claude_antes:
        print(f"CLAUDE.md (se carga en cada sesión): antes {claude_antes} · hoy {claude_hoy} tokens")


if __name__ == "__main__":
    main()
