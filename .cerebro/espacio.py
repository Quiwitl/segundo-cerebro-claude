# -*- coding: utf-8 -*-
"""espacio.py: coloca las notas del vault en 3D como la mosca coloca sus neuronas.

En un cerebro real el cable cuesta, así que las neuronas conectadas quedan cerca: la
colocación minimiza el cableado total (Cherniak, «save wire»), y en el conectoma de FlyWire
la probabilidad de conexión cae con la distancia. Aquí cada enlace es un tubo del Physarum
y los tubos gruesos tiran más fuerte. No cambia notas ni enlaces: solo calcula y mide.

Mide:
  cableado   largo total de los tubos (pesado por grosor) contra 1000 colocaciones al azar
             de las mismas posiciones (prueba de Cherniak: ¿esta asignación es casi óptima?)
  fidelidad  correlación de Spearman entre distancia 3D y saltos en el grafo
  ley        fracción de parejas enlazadas según la distancia (cae con la distancia, como en la mosca)
  vecinos    de las 5 notas más cercanas en 3D, cuántas ya son vecinas en el grafo
             (si son casi todas, el espacio no aporta información nueva para buscar)
Y propone parejas cercanas en 3D, sin enlace, cuyo contenido también se parece (FlyHash):
candidatas a enlace, solo como sugerencia; nunca se aplican solas.

Uso (desde la raíz del vault):
    uv run --no-project --with networkx --with numpy --with scipy python .cerebro\\espacio.py
Escribe .cerebro/salida/espacio.json (incluye privadas marcadas) y
.cerebro/salida/espacio-vista.json, la vista 3D: los mismos nodos que el grafo de Obsidian
(notas, etiquetas y adjuntos, con los filtros de .obsidian/graph.json). Las notas medidas
conservan su lugar; las demás se acomodan alrededor. Es solo estética: no entra a la medición.
Las privadas van sin nombre, y una etiqueta que solo usan notas privadas no aparece.
"""
import datetime
import json
import os
import re
import sys

import networkx as nx
import numpy as np
from scipy.stats import spearmanr

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import hipocampo as h  # noqa: E402

RAIZ = os.path.dirname(AQUI)
SALIDA = os.path.join(AQUI, "salida")
SEMILLAS = 12        # se prueban varias colocaciones y se queda la de menor cableado
AZAR = 1000          # colocaciones al azar para comparar
K = 5                # vecinos 3D que se revisan por nota


def cargar():
    d, _ = h.sincronizar(mapas=False)
    actual = h.rutas_actuales(d)
    por_ruta = {"wiki/" + e["ruta"]: e for e in d["notas"].values()}
    con = json.load(open(os.path.join(SALIDA, "conectoma.json"), encoding="utf-8"))
    tubos = json.load(open(os.path.join(SALIDA, "physarum.json"), encoding="utf-8"))

    def hoy(r, i=None):
        return actual.get(i) or actual.get(r) or r

    G = nx.Graph()
    for n in con["nodos"]:
        G.add_node(hoy(n))
    dmax = max(t["D"] for t in tubos)
    for t in tubos:
        u, v = hoy(t["u"], t.get("u_id")), hoy(t["v"], t.get("v_id"))
        if u != v:
            g = t["D"] / dmax
            G.add_edge(u, v, g=g, w=1.0 + 4.0 * g)  # el tubo más grueso tira 5 veces más
    region = {}
    for i, r in enumerate(con.get("regiones", [])):
        for m in r["miembros"]:
            region[hoy(m)] = i
    return G, por_ruta, region


def cableado(G, pos):
    return sum(a["w"] * np.linalg.norm(pos[u] - pos[v]) for u, v, a in G.edges(data=True))


def colocar(G):
    mejor = None
    for s in range(SEMILLAS):
        p = nx.spring_layout(G, dim=3, weight="w", seed=s, iterations=400)
        p = {n: np.asarray(x) for n, x in p.items()}
        c = cableado(G, p)
        if mejor is None or c < mejor[0]:
            mejor = (c, p, s)
    return mejor


ADJUNTOS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".pdf", ".canvas",
            ".mp3", ".wav", ".m4a", ".ogg", ".mp4", ".webm", ".mov"}
TAG = re.compile(r"(?<![\w#&/\]])#([^\s#\[\]{}()<>,.;:!?\"'`|]+)")


def _filtros_obsidian():
    """Lo que el grafo de Obsidian esconde: -path: y -file: de graph.json, más userIgnoreFilters."""
    def leer_json(nombre):
        try:
            return json.load(open(os.path.join(RAIZ, ".obsidian", nombre), encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    busqueda = leer_json("graph.json").get("search", "")
    rutas = [a or b for k, a, b in re.findall(r'-(path|file):(?:"([^"]+)"|(\S+))', busqueda) if k == "path"]
    archivos = [a or b for k, a, b in re.findall(r'-(path|file):(?:"([^"]+)"|(\S+))', busqueda) if k == "file"]
    rutas += [x.rstrip("/") for x in leer_json("app.json").get("userIgnoreFilters", [])]
    return rutas, archivos


def grafo_obsidian():
    """Nodos y aristas como los dibuja el grafo de Obsidian (notas, etiquetas y adjuntos)."""
    rutas_fuera, archivos_fuera = _filtros_obsidian()
    archivos = []
    for d, dirs, fs in os.walk(RAIZ):
        dirs[:] = [x for x in dirs if not x.startswith(".")]  # Obsidian no indexa carpetas ocultas
        for f in fs:
            rel = os.path.relpath(os.path.join(d, f), RAIZ).replace("\\", "/")
            ext = os.path.splitext(f)[1].lower()
            if ext != ".md" and ext not in ADJUNTOS:
                continue
            if any(r in rel for r in rutas_fuera) or any(a in f for a in archivos_fuera):
                continue
            archivos.append(rel)
    nombres = {}
    for rel in archivos:
        base = rel.rsplit("/", 1)[-1].lower()
        nombres.setdefault(base[:-3] if base.endswith(".md") else base, rel)
    G = nx.Graph()
    privadas, etiquetas = set(), {}
    for rel in archivos:
        G.add_node(rel)
        if not rel.endswith(".md"):
            continue
        texto = h.vault.leer(os.path.join(RAIZ, rel))
        c = h.vault.campos(texto)
        if str(c.get("privado", "")).lower() == "true":
            privadas.add(rel)
        _, cuerpo = h.vault.partir(texto)
        limpio = re.sub(h.vault.CODIGO, "", texto)
        for m in h.vault.WIKILINK.finditer(limpio):
            t = m.group(1).strip().lower()
            t = t[:-3] if t.endswith(".md") else t
            dest = nombres.get(t) or nombres.get(t.rsplit("/", 1)[-1])
            if dest and dest != rel:
                G.add_edge(rel, dest)
        tags = {x.lower().lstrip("#") for x in h._lista(c.get("tags")) if x}
        tags |= {x.lower() for x in TAG.findall(re.sub(h.vault.CODIGO, "", cuerpo)) if not x.isdigit()}
        for t in tags:
            etiquetas.setdefault("#" + t, set()).add(rel)
    for t, notas in etiquetas.items():
        if notas - privadas:  # una etiqueta que solo usan notas privadas no se muestra
            for n in notas:
                G.add_edge(t, n)
    return G, privadas


def vista_obsidian(res, pos, Gmed):
    Go, privadas = grafo_obsidian()
    medidas = {n["ruta"]: n for n in res["nodos"]}
    clave = lambda rel: rel[:-3] if rel.endswith(".md") else rel  # noqa: E731
    fijas = {n for n in Go if clave(n) in medidas and medidas[clave(n)]["grado"] > 0}
    largos = [np.linalg.norm(pos[u] - pos[v]) for u, v in Gmed.edges if Gmed.degree(u) and Gmed.degree(v)]
    k = float(np.median(largos))
    rng = np.random.default_rng(1)
    centro = np.mean([pos[clave(n)] for n in fijas], axis=0)
    ini = {}
    for n in Go:
        if n in fijas:
            ini[n] = np.asarray(pos[clave(n)])
        else:
            vec = [pos[clave(v)] for v in Go[n] if v in fijas]
            base = np.mean(vec, axis=0) if vec else centro
            ini[n] = base + rng.normal(0, k, 3)
    p = nx.spring_layout(Go, dim=3, pos=ini, fixed=sorted(fijas) or None, k=k, iterations=300, seed=1)

    def region(n):
        if clave(n) in medidas and medidas[clave(n)]["region"] >= 0:
            return medidas[clave(n)]["region"]
        votos = [medidas[clave(v)]["region"] for v in Go[n] if clave(v) in medidas and medidas[clave(v)]["region"] >= 0]
        return max(set(votos), key=votos.count) if votos else -1

    nodos, idx = [], {}
    for n in sorted(Go, key=lambda x: (x.startswith("#"), x)):
        if n.startswith("#"):
            tipo, titulo, reg, carpeta = "t", n, -2, ""
        elif not n.endswith(".md"):
            tipo, titulo, reg, carpeta = "a", n.rsplit("/", 1)[-1], -3, n.split("/")[0]
        else:
            m = medidas.get(clave(n))
            tipo = "p" if n in privadas else "n"
            titulo = "" if tipo == "p" else (m["titulo"] if m else n.rsplit("/", 1)[-1][:-3])
            reg = region(n)
            carpeta = n.split("/")[1] if n.startswith("wiki/") and n.count("/") > 1 else n.split("/")[0]
        x, y, z = (round(float(v), 4) for v in p[n])
        idx[n] = len(nodos)
        nodos.append([titulo, reg, Go.degree(n), x, y, z, carpeta, tipo])
    gros = {frozenset((a["u"], a["v"])): a["g"] for a in res["aristas"]}
    aristas = [[idx[u], idx[v], gros.get(frozenset((clave(u), clave(v))), 0.0)] for u, v in Go.edges]
    vista = {"fecha": res["fecha"], "nodos": nodos, "aristas": aristas,
             "medidas": {k_: res[k_] for k_ in ("cableado", "fidelidad_spearman", "ley_distancia", "vecinos_3d_en_grafo")}}
    with open(os.path.join(SALIDA, "espacio-vista.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(vista, f, ensure_ascii=False, separators=(",", ":"))
    cuenta = {t: sum(1 for x in nodos if x[7] == t) for t in "npta"}
    print(f"Vista 3D (como Obsidian): {len(nodos)} nodos — {cuenta['n']} notas, {cuenta['p']} privadas sin nombre, "
          f"{cuenta['t']} etiquetas, {cuenta['a']} adjuntos — y {len(aristas)} enlaces")


def main():
    G, por_ruta, region = cargar()
    costo, pos, semilla = colocar(G)
    nodos = list(G.nodes)
    X = np.array([pos[n] for n in nodos])
    idx = {n: i for i, n in enumerate(nodos)}

    # --- cableado contra el azar (mismas posiciones, asignadas al azar)
    rng = np.random.default_rng(0)
    E = np.array([(idx[u], idx[v], a["w"]) for u, v, a in G.edges(data=True)])
    a_, b_, w_ = E[:, 0].astype(int), E[:, 1].astype(int), E[:, 2]
    azar = []
    for _ in range(AZAR):
        P = X[rng.permutation(len(nodos))]
        azar.append(float((w_ * np.linalg.norm(P[a_] - P[b_], axis=1)).sum()))
    azar = np.array(azar)

    # --- fidelidad y ley de distancia (componente mayor)
    comp = max(nx.connected_components(G), key=len)
    saltos = dict(nx.all_pairs_shortest_path_length(G.subgraph(comp)))
    cm = sorted(comp)
    dist, hop, enl = [], [], []
    for i, u in enumerate(cm):
        for v in cm[i + 1:]:
            dist.append(float(np.linalg.norm(pos[u] - pos[v])))
            hop.append(saltos[u][v])
            enl.append(G.has_edge(u, v))
    dist, hop, enl = np.array(dist), np.array(hop), np.array(enl)
    rho = float(spearmanr(dist, hop).correlation)
    cortes = np.quantile(dist, [0, .2, .4, .6, .8, 1])
    ley = []
    for k in range(5):
        m = (dist >= cortes[k]) & (dist <= cortes[k + 1]) if k == 4 else (dist >= cortes[k]) & (dist < cortes[k + 1])
        ley.append(round(float(enl[m].mean()), 3))

    # --- vecinos 3D contra vecinos del grafo, y sugerencias
    D = np.linalg.norm(X[:, None, :] - X[None, :, :], axis=2)
    np.fill_diagonal(D, np.inf)
    prec = []
    cand = {}

    def apta(n):
        e = por_ruta.get(n)
        return e is not None and not e.get("privado") and not e.get("generada")

    for n in nodos:
        cerca = [nodos[j] for j in np.argsort(D[idx[n]])[:K]]
        if G.degree(n):
            prec.append(sum(G.has_edge(n, c) for c in cerca) / K)
        if not apta(n):
            continue
        for c in cerca:
            if G.has_edge(n, c) or not apta(c):
                continue
            par = tuple(sorted((n, c)))
            if par not in cand:
                cand[par] = h.parecido(por_ruta[n]["huella"], por_ruta[c]["huella"])
    # referencia: parecido de todas las parejas sin enlace
    ref = [h.parecido(por_ruta[u]["huella"], por_ruta[v]["huella"])
           for i, u in enumerate(nodos) if apta(u)
           for v in nodos[i + 1:] if apta(v) and not G.has_edge(u, v)]
    p90 = float(np.quantile(ref, 0.9))
    sug = sorted(((s, u, v) for (u, v), s in cand.items() if s >= p90), reverse=True)

    def info(n):
        e = por_ruta.get(n, {})
        return {"ruta": n, "id": next((k for k, x in [(k, x) for k, x in []]), None),
                "titulo": e.get("titulo") or n.rsplit("/", 1)[-1], "desc": e.get("desc", ""),
                "privado": bool(e.get("privado")), "region": region.get(n, -1), "grado": G.degree(n),
                "x": round(float(pos[n][0]), 4), "y": round(float(pos[n][1]), 4), "z": round(float(pos[n][2]), 4)}

    res = {
        "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "semilla": semilla,
        "notas": len(nodos), "tubos": G.number_of_edges(),
        "cableado": {"real": round(costo, 2), "azar_media": round(float(azar.mean()), 2),
                     "reduccion": round(1 - costo / float(azar.mean()), 3),
                     "azar_mejores": int((azar <= costo).sum()), "azar_n": AZAR},
        "fidelidad_spearman": round(rho, 3),
        "ley_distancia": ley,
        "vecinos_3d_en_grafo": round(float(np.mean(prec)), 3),
        "parecido_p90_sin_enlace": round(p90, 3),
        "sugerencias": [{"a": u, "b": v, "parecido": round(s, 3)} for s, u, v in sug[:15]],
        "nodos": [info(n) for n in nodos],
        "aristas": [{"u": u, "v": v, "g": round(a["g"], 4)} for u, v, a in G.edges(data=True)],
    }
    os.makedirs(SALIDA, exist_ok=True)
    with open(os.path.join(SALIDA, "espacio.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    vista_obsidian(res, pos, G)

    c = res["cableado"]
    print(f"{res['notas']} notas, {res['tubos']} tubos (semilla {semilla})")
    print(f"Cableado: {c['real']:.1f} contra {c['azar_media']:.1f} al azar (−{100 * c['reduccion']:.0f} %); "
          f"colocaciones al azar mejores: {c['azar_mejores']} de {c['azar_n']}")
    print(f"Fidelidad (Spearman distancia 3D vs saltos): {rho:.2f}")
    print("Fracción enlazada por quintil de distancia (cerca → lejos):", ley)
    print(f"De los {K} vecinos 3D más cercanos, ya enlazados en el grafo: {100 * res['vecinos_3d_en_grafo']:.0f} %")
    print(f"Sugerencias de enlace (cerca en 3D, sin enlace, parecido ≥ p90 = {p90:.2f}): {len(sug)}")
    for s, u, v in sug[:8]:
        print(f"  {s:.2f}  {u.rsplit('/', 1)[-1]}  ↔  {v.rsplit('/', 1)[-1]}")


if __name__ == "__main__":
    main()
