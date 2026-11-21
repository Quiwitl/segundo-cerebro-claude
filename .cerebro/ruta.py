# -*- coding: utf-8 -*-
"""ruta.py: rutas de lectura trazadas por el Physarum, para buscar información gastando menos.

No borra ni cambia nada: usa todos los enlaces. Cada paso cuesta una nota leída, y entre
rutas igual de cortas prefiere las vías gruesas que dejó physarum.py.

Uso (desde la raíz del vault, solo biblioteca estándar):
    python .cerebro\\ruta.py "Zettelkasten"              ruta desde el hub de su región + vecinos fuertes
    python .cerebro\\ruta.py "Zettelkasten" "Physarum"    ruta más barata entre dos notas
    python .cerebro\\ruta.py --hubs                     hubs de cada región (puntos de entrada)

Los nombres se buscan sin importar mayúsculas ni acentos, y basta con un pedazo.
Requiere .cerebro/salida/physarum.json (lo escribe physarum.py).
"""
import heapq
import json
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, ".cerebro", "salida")


def plano(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def nombre(rel):
    return rel.rsplit("/", 1)[-1]


def cargar():
    ruta = os.path.join(SALIDA, "physarum.json")
    if not os.path.exists(ruta):
        sys.exit("Falta .cerebro/salida/physarum.json: corre primero physarum.py")
    tubos = json.load(open(ruta, encoding="utf-8"))
    # el hipocampo dice dónde está hoy cada nota (por id), aunque se haya renombrado o movido
    # después del último physarum.py; si no está disponible, se usan las rutas tal cual
    try:
        import hipocampo
        actual = hipocampo.rutas_actuales()
    except Exception:
        actual = {}

    def hoy(ruta, id_):
        return actual.get(id_) or actual.get(ruta) or ruta

    dmax = max(t["D"] for t in tubos)
    vecinos = {}
    for t in tubos:
        g = t["D"] / dmax  # grosor relativo, 0..1
        u, v = hoy(t["u"], t.get("u_id")), hoy(t["v"], t.get("v_id"))
        vecinos.setdefault(u, []).append((v, g))
        vecinos.setdefault(v, []).append((u, g))
    con = json.load(open(os.path.join(SALIDA, "conectoma.json"), encoding="utf-8"))
    hub_de = {}
    hubs = []
    for r in con.get("regiones", []):
        nucleo = [hoy(x, None) for x in r["nucleo"]]
        h = next((x for x in nucleo if x in vecinos), None)
        if h:
            hubs.append(h)
            for m in r["miembros"]:
                hub_de[hoy(m, None)] = h
    return vecinos, hub_de, hubs


def buscar(texto, vecinos):
    q = plano(texto)
    exactas = [n for n in vecinos if plano(nombre(n)) == q]
    if exactas:
        return exactas[0]
    parecidas = sorted((n for n in vecinos if q in plano(nombre(n))), key=lambda n: len(n))
    if not parecidas:
        sys.exit(f"No encontré una nota que contenga «{texto}»")
    if len(parecidas) > 1:
        print("(también coinciden: " + ", ".join(nombre(n) for n in parecidas[1:5]) + ")")
    return parecidas[0]


def camino(a, b, vecinos):
    # Dijkstra: cada paso cuesta 1 (una nota más que leer = más tokens) y el grosor del Physarum
    # descuenta hasta 0.45. Así gana siempre el camino con menos notas, y entre caminos igual de
    # cortos gana el que va por vías gruesas. (Con costo 1/grosor puro las rutas salían más largas.)
    dist, prev, cola = {a: 0.0}, {}, [(0.0, a)]
    while cola:
        d, n = heapq.heappop(cola)
        if n == b:
            break
        if d > dist.get(n, 1e18):
            continue
        for m, g in vecinos.get(n, []):
            nd = d + 1.0 + 0.45 * (1.0 - g)
            if nd < dist.get(m, 1e18):
                dist[m], prev[m] = nd, (n, g)
                heapq.heappush(cola, (nd, m))
    if b not in dist:
        return None
    pasos, n = [], b
    while n != a:
        p, g = prev[n]
        pasos.append((p, n, g))
        n = p
    return list(reversed(pasos))


def imprimir(pasos):
    if not pasos:
        print("  (es la misma nota)")
        return
    print(f"  1. {nombre(pasos[0][0])}")
    for i, (_, n, g) in enumerate(pasos, 2):
        via = "vía gruesa" if g >= 0.3 else "vía media" if g >= 0.05 else "vía podada (atajo poco usado)"
        print(f"  {i}. {nombre(n)}   ← {via}, grosor {g:.2f}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    vecinos, hub_de, hubs = cargar()
    if args[0] == "--hubs":
        print("Puntos de entrada por región:")
        for h in hubs:
            print("  - " + nombre(h))
        return
    a = buscar(args[0], vecinos)
    if len(args) >= 2:
        b = buscar(args[1], vecinos)
        print(f"Ruta de lectura: {nombre(a)} → {nombre(b)}")
        pasos = camino(a, b, vecinos)
        imprimir(pasos) if pasos is not None else print("  No hay camino entre esas notas.")
        return
    hub = hub_de.get(a) or (hubs[0] if hubs else a)
    print(f"Nota: {nombre(a)}  (región de {nombre(hub)})")
    print("Ruta desde el punto de entrada:")
    imprimir(camino(hub, a, vecinos) or [])
    fuertes = sorted(vecinos[a], key=lambda x: -x[1])[:4]
    print("Leer junto con (vecinos por vía más gruesa):")
    for m, g in fuertes:
        print(f"  - {nombre(m)}   grosor {g:.2f}")


if __name__ == "__main__":
    main()
