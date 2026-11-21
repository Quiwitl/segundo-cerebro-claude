# -*- coding: utf-8 -*-
"""Conectoma del vault: lee notas y enlaces de un vault de Obsidian y los
analiza como una red (notas = neuronas, enlaces = sinapsis).

Solo lectura sobre las notas. Escribe un reporte .md y un .json en --salida.

Uso:
    uv run --with networkx python conectoma.py <vault> --salida <carpeta>
"""
import argparse
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime

import networkx as nx

IGNORAR = {".obsidian", ".git", ".tools", ".trash", ".raw", "node_modules", ".cerebro",
           "graphify-out", "_templates", "_attachments", "proyectos",  # proyectos/: código y LEEME de proyectos, no son notas
           "hipocampo"}  # copias generadas, plantillas y mapas del hipocampo (wiki/hipocampo)
WIKILINK = re.compile(r"!?\[\[([^\]\|#\^]+)(?:[#\^][^\]\|]*)?(?:\|[^\]]*)?\]\]")
MDLINK = re.compile(r"\[[^\]]*\]\(([^)\s]+?\.md)(?:#[^)]*)?\)")
CODIGO = re.compile(r"```.*?```|`[^`\n]*`", re.S)
# Notas de navegación o configuración: enlazan a todo y falsean hubs y puentes.
ESTRUCTURALES = {"index", "_index", "log", "hot", "overview", "claude", "readme",
                 "mapa de conexiones del vault", "mapa del cerebro"}
PRIVADO = re.compile(r"^privado:\s*true\s*$", re.M | re.I)


def leer_vault(raiz):
    notas = {}  # ruta relativa sin .md -> texto
    for d, subdirs, archivos in os.walk(raiz):
        subdirs[:] = [s for s in subdirs if s not in IGNORAR and not s.startswith(".")]
        for a in archivos:
            if a.lower().endswith(".md"):
                p = os.path.join(d, a)
                rel = os.path.relpath(p, raiz).replace("\\", "/")[:-3]
                if rel.rsplit("/", 1)[-1].lower() in ESTRUCTURALES:
                    continue
                with open(p, encoding="utf-8", errors="replace") as f:
                    notas[rel] = f.read()
    return notas


def resolver(destino, por_nombre, por_ruta):
    destino = destino.strip().replace("\\", "/")
    if destino.lower().endswith(".md"):
        destino = destino[:-3]
    clave = destino.lower()
    if clave in por_ruta:
        return por_ruta[clave]
    nombre = clave.rsplit("/", 1)[-1]
    candidatos = por_nombre.get(nombre, [])
    if candidatos:
        # Obsidian prefiere la ruta más corta cuando hay nombres repetidos
        return min(candidatos, key=len)
    return None


def construir_red(notas):
    por_nombre = defaultdict(list)
    por_ruta = {}
    for rel in notas:
        por_ruta[rel.lower()] = rel
        por_nombre[rel.rsplit("/", 1)[-1].lower()].append(rel)

    G = nx.DiGraph()
    G.add_nodes_from(notas)
    rotos = Counter()
    for rel, texto in notas.items():
        limpio = CODIGO.sub("", texto)
        destinos = [m.group(1) for m in WIKILINK.finditer(limpio)]
        destinos += [os.path.normpath(os.path.join(os.path.dirname(rel), m.group(1))).replace("\\", "/")
                     for m in MDLINK.finditer(limpio) if "://" not in m.group(1)]
        for t in destinos:
            r = resolver(t, por_nombre, por_ruta)
            if r is None:
                if t.strip().rsplit("/", 1)[-1].lower() in ESTRUCTURALES:
                    continue  # nota de navegación excluida, no está rota
                if not re.search(r"\.(png|jpe?g|gif|svg|pdf|webp|mp4|mp3|canvas|base)$", t, re.I):
                    rotos[t.strip()] += 1
            elif r != rel:
                if G.has_edge(rel, r):
                    G[rel][r]["peso"] += 1
                else:
                    G.add_edge(rel, r, peso=1)
    return G, rotos


def mundo_pequeno(U, semilla=42, n_rand=5):
    """Compara agrupamiento y camino medio con redes aleatorias del mismo tamaño."""
    comp = U.subgraph(max(nx.connected_components(U), key=len)).copy()
    n, m = comp.number_of_nodes(), comp.number_of_edges()
    if n < 10 or m < n:
        return None
    C = nx.average_clustering(comp)
    L = nx.average_shortest_path_length(comp)
    Cs, Ls = [], []
    rng = random.Random(semilla)
    for _ in range(n_rand):
        R = nx.gnm_random_graph(n, m, seed=rng.randint(0, 10**6))
        if not nx.is_connected(R):
            R = R.subgraph(max(nx.connected_components(R), key=len)).copy()
        Cs.append(nx.average_clustering(R))
        Ls.append(nx.average_shortest_path_length(R))
    Cr, Lr = sum(Cs) / len(Cs), sum(Ls) / len(Ls)
    sigma = (C / Cr) / (L / Lr) if Cr > 0 else None
    return {"n": n, "C": C, "L": L, "C_rand": Cr, "L_rand": Lr, "sigma": sigma}


def sugerir_enlaces(G, notas, n=10):
    """Pares sin enlace que comparten vecinos poco comunes (asignación de recursos).

    Medido el 9 nov 2026 quitando al azar el 10 % de los enlaces (en el vault original):
    recupera ~39 veces más enlaces que el azar en su top 20; Adamic–Adar, casi igual. El parecido
    de contenido del hongo no predijo nada (1.1 veces el azar). Sin notas privadas ni fuentes
    (catálogos de chats): enlazarlas no ayuda a nadie."""
    fuera = {v for v in G if v.startswith("wiki/sources/")
             or PRIVADO.search(notas.get(v, "").split("\n---", 1)[0])}
    U = nx.Graph()
    U.add_nodes_from(v for v in G if v not in fuera)
    U.add_edges_from((x, y) for x, y in G.edges() if x != y and x not in fuera and y not in fuera)
    nodos = sorted(v for v in U if U.degree(v) > 0)
    pares = [(x, y) for i, x in enumerate(nodos) for y in nodos[i + 1:] if not U.has_edge(x, y)]
    filas = sorted(((s, x, y) for x, y, s in nx.resource_allocation_index(U, pares) if s > 0), reverse=True)[:n]
    return [{"a": x, "b": y, "puntaje": round(s, 3),
             "via": sorted(nx.common_neighbors(U, x, y), key=lambda w: U.degree(w))[:3]} for s, x, y in filas]


def enlace(rel):
    return f"[[{rel}|{rel.rsplit('/', 1)[-1]}]]"


def analizar(G, rotos, top=10):
    U = G.to_undirected()
    n, m = U.number_of_nodes(), U.number_of_edges()
    grado = dict(U.degree())
    entrada = dict(G.in_degree())
    aisladas = sorted(v for v, d in grado.items() if d == 0)
    componentes = sorted(nx.connected_components(U), key=len, reverse=True)

    conectadas = U.subgraph([v for v in U if grado[v] > 0]).copy()
    puentes = {}
    regiones = []
    if conectadas.number_of_nodes() > 2:
        k = None if conectadas.number_of_nodes() <= 1500 else 300
        puentes = nx.betweenness_centrality(conectadas, k=k, seed=42)
        comunidades = nx.community.louvain_communities(conectadas, seed=42)
        Q = nx.community.modularity(conectadas, comunidades)
        for c in sorted(comunidades, key=len, reverse=True):
            miembros = sorted(c, key=lambda v: -grado[v])
            carpetas = Counter(v.rsplit("/", 1)[0].removeprefix("wiki/") if "/" in v else "(raíz)" for v in c)
            regiones.append({"tamano": len(c), "nucleo": miembros[:5], "miembros": sorted(c),
                             "carpetas": carpetas.most_common(3)})
    else:
        Q = None

    return {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "notas": n, "enlaces": m,
        "grado_medio": (2 * m / n) if n else 0,
        "densidad": nx.density(U) if n > 1 else 0,
        "componentes": len(componentes),
        "componente_mayor": len(componentes[0]) if componentes else 0,
        "hubs": sorted(entrada, key=lambda v: -entrada[v])[:top],
        "entrada": entrada,
        "grado": grado,
        "puentes": sorted(puentes, key=lambda v: -puentes[v])[:top],
        "betweenness": puentes,
        "regiones": regiones,
        "modularidad": Q,
        "aisladas": aisladas,
        "rotos": rotos.most_common(),
        "mundo_pequeno": mundo_pequeno(U),
    }


def id_existente(p):
    """Conserva el id estable de la nota al regenerarla (el hipocampo la sigue por id)."""
    try:
        with open(p, encoding="utf-8") as f:
            m = re.search(r"^id:\s*(\S+)\s*$", f.read().split("\n---", 1)[0], re.M)
        return m.group(1) if m else None
    except OSError:
        return None


def reporte_md(r, id_nota=None):
    L = []
    L.append("---\ntype: meta\ntitle: Mapa del cerebro\n" + (f"id: {id_nota}\n" if id_nota else "") +
             "description: \"Análisis de red del vault (hubs, puentes, regiones, mundo pequeño); lo genera .cerebro/conectoma.py\"\n"
             "updated: " + r["fecha"].split()[0] + "\ngenerado_por: conectoma.py\n---\n")
    L.append("# Mapa del cerebro\n")
    L.append(f"> Generado automáticamente el {r['fecha']}. Solo lectura: no modifica ninguna nota. "
             "Se regenera en cada pasada; no lo edites a mano. Excluye las notas de navegación "
             "(index, _index, log, hot) porque enlazan a todo y falsearían hubs y puentes.\n")
    L.append("## Resumen\n")
    L.append(f"- **Notas (neuronas):** {r['notas']}")
    L.append(f"- **Enlaces (sinapsis):** {r['enlaces']}")
    L.append(f"- **Grado medio:** {r['grado_medio']:.2f} enlaces por nota")
    L.append(f"- **Componentes:** {r['componentes']} (la mayor reúne {r['componente_mayor']} notas)")
    L.append(f"- **Notas aisladas:** {len(r['aisladas'])}")
    L.append(f"- **Enlaces rotos:** {sum(c for _, c in r['rotos'])} hacia {len(r['rotos'])} destinos")
    if r["modularidad"] is not None:
        L.append(f"- **Regiones:** {len(r['regiones'])} (modularidad {r['modularidad']:.2f}; "
                 "por encima de 0.3 hay regiones bien separadas)")
    mp = r["mundo_pequeno"]
    if mp:
        veredicto = ("sí, como un cerebro" if mp["sigma"] and mp["sigma"] > 1.5
                     else "débil" if mp["sigma"] and mp["sigma"] > 1 else "no")
        L.append(f"- **¿Mundo pequeño?** {veredicto} (σ = {mp['sigma']:.2f}; agrupamiento "
                 f"{mp['C']:.2f} vs {mp['C_rand']:.2f} al azar, camino medio {mp['L']:.2f} vs {mp['L_rand']:.2f})")
    L.append("")

    L.append("## Hubs\nLas notas a las que más se enlaza. Son tus conceptos centrales.\n")
    for v in r["hubs"]:
        if r["entrada"][v] == 0:
            break
        L.append(f"- {enlace(v)} — {r['entrada'][v]} enlaces entrantes")
    L.append("")

    if r["puentes"]:
        L.append("## Puentes\nNotas por las que pasan los caminos entre temas. Si desaparecieran, "
                 "partes del vault quedarían desconectadas.\n")
        for v in r["puentes"]:
            if r["betweenness"][v] <= 0:
                break
            L.append(f"- {enlace(v)} — {r['betweenness'][v]:.3f}")
        L.append("")

    if r.get("sugeridos"):
        L.append("## Enlaces que faltan\nPares sin enlace que comparten vecinos poco comunes. Son sugerencias: "
                 "enlazar solo si de verdad se relacionan y sin pasar de 3 conceptos en `related`. "
                 "No incluye notas privadas ni fuentes.\n")
        for x in r["sugeridos"]:
            via = ", ".join(v.rsplit("/", 1)[-1] for v in x["via"])
            L.append(f"- {x['a'].rsplit('/', 1)[-1]} ↔ {x['b'].rsplit('/', 1)[-1]} · vía {via} ({x['puntaje']})")
        L.append("")

    if r["regiones"]:
        L.append("## Regiones\nGrupos de notas más enlazadas entre sí que con el resto (Louvain).\n")
        for i, reg in enumerate(r["regiones"], 1):
            if reg["tamano"] < 3:
                continue
            carp = ", ".join(f"`{c}` ({k})" for c, k in reg["carpetas"])
            L.append(f"### Región {i} · {reg['tamano']} notas")
            L.append(f"Carpetas: {carp}  ")
            L.append("Núcleo: " + " · ".join(enlace(v) for v in reg["nucleo"]) + "\n")
        pequenas = sum(1 for reg in r["regiones"] if reg["tamano"] < 3)
        if pequenas:
            L.append(f"_Además hay {pequenas} grupos de 1–2 notas._\n")

    if r.get("catalogos"):
        L.append("## Catálogos (excluidos del análisis)\nNotas que enlazan a gran parte del vault, "
                 "como un índice. Se excluyen para que no aparezcan como falsos puentes.\n")
        for v, k in r["catalogos"]:
            L.append(f"- {enlace(v)} — enlaza a {k} notas")
        L.append("")

    if r["aisladas"]:
        L.append(f"## Notas aisladas ({len(r['aisladas'])})\nSin enlaces de entrada ni de salida.\n")
        for v in r["aisladas"][:60]:
            L.append(f"- {enlace(v)}")
        if len(r["aisladas"]) > 60:
            L.append(f"- … y {len(r['aisladas']) - 60} más (ver el .json)")
        L.append("")

    if r["rotos"]:
        L.append(f"## Enlaces rotos\nDestinos que no existen como nota.\n")
        for t, c in r["rotos"][:40]:
            L.append(f"- `{t}` ×{c}")
        L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vault")
    ap.add_argument("--salida", required=True)
    a = ap.parse_args()
    notas = leer_vault(a.vault)
    if not notas:
        sys.exit("No encontré notas .md en " + a.vault)
    G, rotos = construir_red(notas)
    # Catálogos: notas que enlazan a buena parte del vault (como un índice).
    # Falsean los puentes igual que index, así que se reportan aparte y se excluyen.
    umbral = max(15, int(0.4 * G.number_of_nodes()))
    catalogos = sorted((v for v in G if G.out_degree(v) >= umbral), key=lambda v: -G.out_degree(v))
    salida_cat = [(v, G.out_degree(v)) for v in catalogos]
    G.remove_nodes_from(catalogos)
    r = analizar(G, rotos)
    r["catalogos"] = salida_cat
    r["sugeridos"] = sugerir_enlaces(G, notas)
    os.makedirs(a.salida, exist_ok=True)
    with open(os.path.join(a.salida, "Mapa del cerebro.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(reporte_md(r, id_existente(os.path.join(a.vault, "wiki", "meta", "Mapa del cerebro.md"))))
    datos = {k: v for k, v in r.items() if k not in ("entrada", "grado", "betweenness")}
    datos["nodos"] = {v: {"grado": r["grado"][v], "entrada": r["entrada"][v],
                          "betweenness": round(r["betweenness"].get(v, 0), 5)} for v in r["grado"]}
    datos["aristas"] = [[u, v, d["peso"]] for u, v, d in G.edges(data=True)]
    with open(os.path.join(a.salida, "conectoma.json"), "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    print(f"notas={r['notas']} enlaces={r['enlaces']} regiones={len(r['regiones'])} "
          f"aisladas={len(r['aisladas'])} rotos={len(r['rotos'])}")


if __name__ == "__main__":
    main()
