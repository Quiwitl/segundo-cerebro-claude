# -*- coding: utf-8 -*-
"""physarum.py: simula el moho Physarum polycephalum sobre la red del vault.

Modelo de Tero et al. (2007, 2010; el experimento de la red de trenes de Tokio):
cada enlace entre notas es un tubo con conductividad D y largo L. En cada ronda
se eligen dos notas al azar (comida y destino), el flujo se reparte por los tubos
según las leyes de Kirchhoff, y cada tubo se adapta:

    dD/dt = |Q|^mu - D        (los tubos que llevan flujo engordan; los demás se encogen)

Tras miles de rondas queda el "esqueleto": los enlaces que de verdad sostienen
el tránsito entre tus temas. NO toca ningún enlace del vault: solo escribe un informe.

Fuentes de alimento: parte de las rondas (--uso, 0.5 por omisión) salen de búsquedas
reales registradas con `hipocampo.py usar` (.cerebro/uso.jsonl): las notas que sirvieron
juntas se alimentan entre sí, y lo reciente pesa más (vida media de 30 días). Así los
caminos que de verdad transitas engordan; los que no se usan decaen hasta un piso,
nunca a cero, y ningún enlace se borra. Sin uso registrado, todo es al azar como antes.

Uso, desde la raíz del vault, después de conectoma.py:
    uv run --no-project --with networkx --with numpy --with matplotlib python .cerebro\\physarum.py
Opciones: --rondas 6000  --mu 1.3  --semilla 7  --uso 0.5
Salidas:
    wiki/meta/Physarum del vault.md          informe (sin wikilinks, para no alterar el grafo)
    _attachments/physarum-del-vault.png      el esqueleto dibujado con los colores de grafo.py
    .cerebro/salida/physarum.json            conductividades finales por enlace
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

import networkx as nx
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hipocampo  # noqa: E402  (ids estables y registro de uso)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, ".cerebro", "salida", "conectoma.json")
# mismos colores que .cerebro/grafo.py (pósters de Winkler), en el mismo orden de regiones
PALETA = ["#3A72D6", "#F05A1E", "#10A3A3", "#B4304F", "#7E9C2C", "#D034B0"]
SIN_REGION = "#9AB0E8"
FONDO = "#2B2A28"
TINTA = "#F0EEE8"


def nombre(rel):
    return rel.rsplit("/", 1)[-1]


def cargar():
    if not os.path.exists(DATOS):
        sys.exit("Falta .cerebro/salida/conectoma.json: corre primero conectoma.py")
    d = json.load(open(DATOS, encoding="utf-8"))
    g = nx.Graph()
    for u, v, w in d["aristas"]:
        if u == v:
            continue
        if g.has_edge(u, v):
            g[u][v]["w"] += w
        else:
            g.add_edge(u, v, w=w)
    g = g.subgraph(max(nx.connected_components(g), key=len)).copy()
    region = {}
    for i, r in enumerate(d.get("regiones", [])[: len(PALETA)]):
        for m in r["miembros"]:
            region[m] = i
    return g, region, d


def alimento_de_uso(g):
    """Eventos de uso como (peso, [nodos del grafo]); las notas renombradas se siguen por id."""
    try:
        rutas = hipocampo.rutas_actuales()
    except Exception as exc:  # sin índice no hay uso que mapear; el moho sigue al azar
        print("aviso: sin hipocampo, Physarum va al azar:", exc)
        return []
    out = []
    for peso, ids in hipocampo.eventos_de_uso():
        nodos = sorted({rutas[i] for i in ids if i in rutas and rutas[i] in g})
        if nodos:
            out.append((peso, nodos))
    return out


def simular(g, rondas, mu, semilla, eventos=(), f_uso=0.0):
    nodos = list(g.nodes)
    idx = {n: i for i, n in enumerate(nodos)}
    aristas = [(idx[u], idx[v]) for u, v in g.edges]
    # enlaces en ambos sentidos o repetidos = tubo más corto (más fácil de recorrer)
    largo = np.array([1.0 / g[u][v]["w"] for u, v in g.edges])
    D = np.ones(len(aristas))
    a = np.array([e[0] for e in aristas])
    b = np.array([e[1] for e in aristas])
    n = len(nodos)
    rng = np.random.default_rng(semilla)
    dt_ = 0.01  # paso chico: cada tubo "recuerda" ~100 rondas, no solo la última pareja
    uso = np.zeros(len(aristas))  # flujo acumulado, para medir qué tanto se usa cada tubo
    D_prom = np.zeros(len(aristas))  # conductividad promedio en la segunda mitad (ya estabilizada)
    if eventos and f_uso > 0:
        pesos_ev = np.array([p for p, _ in eventos])
        pesos_ev = pesos_ev / pesos_ev.sum()
        ev_idx = [[idx[x] for x in ns] for _, ns in eventos]
    for ronda in range(rondas):
        if eventos and f_uso > 0 and rng.random() < f_uso:
            ev = ev_idx[rng.choice(len(ev_idx), p=pesos_ev)]
            if len(ev) >= 2:  # notas que sirvieron juntas: comida en una, destino en otra
                s, t = rng.choice(ev, size=2, replace=False)
            else:  # una sola nota útil: comida ahí, destino cualquiera
                s = ev[0]
                t = rng.choice([i for i in range(n) if i != s])
        else:
            s, t = rng.choice(n, size=2, replace=False)
        c = D / largo
        lap = np.zeros((n, n))
        np.add.at(lap, (a, a), c)
        np.add.at(lap, (b, b), c)
        np.add.at(lap, (a, b), -c)
        np.add.at(lap, (b, a), -c)
        rhs = np.zeros(n)
        rhs[s] = 1.0
        rhs[t] = -1.0
        # tierra en t: quitar su fila y columna para que el sistema tenga solución única
        keep = np.arange(n) != t
        p = np.zeros(n)
        p[keep] = np.linalg.solve(lap[np.ix_(keep, keep)] + 1e-9 * np.eye(n - 1), rhs[keep])
        Q = c * (p[a] - p[b])
        uso += np.abs(Q)
        D = D + dt_ * (np.abs(Q) ** mu - D)
        D = np.maximum(D, 1e-6)
        if ronda >= rondas // 2:
            D_prom += D
    return nodos, aristas, D_prom / (rondas - rondas // 2), uso / rondas


def informe(g, region, d, nodos, aristas, D, uso, args):
    rel = D / D.max()
    orden = np.argsort(-rel)
    vivos = rel >= 0.05
    eb = nx.edge_betweenness_centrality(g)
    btw = np.array([eb.get((nodos[i], nodos[j]), eb.get((nodos[j], nodos[i]), 0.0)) for i, j in aristas])
    # correlación de rangos (Spearman) entre lo que conserva el moho y la intermediación clásica
    ra = np.argsort(np.argsort(rel))
    rb = np.argsort(np.argsort(btw))
    rho = float(np.corrcoef(ra, rb)[0, 1])

    def reg(nodo):
        r = region.get(nodo)
        return "sin región" if r is None else " · ".join(nombre(x) for x in d["regiones"][r]["nucleo"][:1])

    # enlaces que unen regiones distintas y sobreviven: las autopistas entre tus temas
    puentes = [k for k in orden if vivos[k] and region.get(nodos[aristas[k][0]]) != region.get(nodos[aristas[k][1]])]
    # tubos que el moho poda aunque la red clásica los considere importantes
    sorpresas = [k for k in np.argsort(-btw) if not vivos[k]][:8]
    # grado en el esqueleto: notas que siguen siendo cruces de caminos
    esq = nx.Graph()
    esq.add_edges_from((nodos[aristas[k][0]], nodos[aristas[k][1]]) for k in range(len(aristas)) if vivos[k])
    cruces = sorted(esq.degree, key=lambda x: -x[1])[:10]
    aislados = [x for x in g.nodes if x not in esq]

    hoy = dt.date.today().isoformat()
    L = [
        "---", "type: meta", 'title: "Physarum del vault"', *([f"id: {args.id_nota}"] if args.id_nota else []),
        'description: "Simulación del moho Physarum sobre la red del vault: qué enlaces forman el esqueleto y cuáles se podarían"',
        f"created: {hoy}", f"updated: {hoy}", "tags: [meta, red, physarum]", "status: developing",
        'generado_por: ".cerebro/physarum.py"', "---", "",
        "# Physarum del vault", "",
        "> Generado por `.cerebro/physarum.py`. Modelo de Tero et al.: cada enlace es un tubo; los que llevan flujo entre notas al azar engordan y los demás se encogen. "
        "No modifica ningún enlace real: es una lectura de la red. Los nombres van sin enlazar para no alterar el grafo.", "",
        f"Simulación: {len(nodos)} notas, {len(aristas)} enlaces, {args.rondas} rondas, μ = {args.mu}, semilla {args.semilla}. "
        f"Datos de conectoma del {d.get('fecha', '?')}.",
        (f"Fuentes de alimento: {100 * args.uso:.0f} % de las rondas salen de {args.n_eventos} búsquedas reales "
         "registradas con `hipocampo.py usar`; el resto, al azar." if args.n_eventos and args.uso > 0 else
         "Fuentes de alimento: todas al azar (todavía no hay búsquedas registradas con `hipocampo.py usar`)."), "",
        "![[physarum-del-vault.png]]", "",
        "## Resumen", "",
        f"- Sobreviven **{int(vivos.sum())} de {len(aristas)} enlaces** ({100 * vivos.mean():.0f} %): ese es el esqueleto.",
        f"- {len(puentes)} de ellos unen regiones distintas: son las vías entre tus temas.",
        f"- Parecido con la intermediación clásica de conectoma.py (Spearman ρ = {rho:.2f}): "
        + ("el moho confirma casi lo mismo." if rho > 0.7 else "el moho ve algo distinto a la medida clásica." if rho < 0.4 else "coinciden en lo grueso y difieren en el detalle."),
        (f"- {len(aislados)} nota queda fuera del esqueleto: el flujo no pasa por ella." if len(aislados) == 1 else
         f"- {len(aislados)} notas quedan fuera del esqueleto: el flujo no pasa por ellas."), "",
        "## Las 15 vías más gruesas", "",
        "| Enlace | Grosor | Regiones |", "|---|---|---|",
    ]
    for k in orden[:15]:
        u, v = nodos[aristas[k][0]], nodos[aristas[k][1]]
        L.append(f"| {nombre(u)} ↔ {nombre(v)} | {rel[k]:.2f} | {reg(u)} / {reg(v)} |")
    L += ["", "## Puentes que sobreviven entre regiones", ""]
    L += [f"- {nombre(nodos[aristas[k][0]])} ↔ {nombre(nodos[aristas[k][1]])} ({rel[k]:.2f})" for k in puentes[:12]] or ["- Ninguno."]
    L += ["", "## Cruces de caminos del esqueleto", "", "Notas con más vías vivas: por aquí pasa casi todo el tránsito entre ideas.", ""]
    L += [f"- {nombre(x)}: {gr} vías" for x, gr in cruces]
    L += ["", "## Lo que el moho podaría aunque parezca importante", "",
          "Enlaces con alta intermediación clásica que no sobreviven: hay otro camino más eficiente entre esas notas.", ""]
    L += [f"- {nombre(nodos[aristas[k][0]])} ↔ {nombre(nodos[aristas[k][1]])}" for k in sorpresas] or ["- Ninguno."]
    L += ["", "## Notas fuera del esqueleto", ""]
    L += [", ".join(sorted(nombre(x) for x in aislados)) or "Ninguna."]
    L += ["", "## Cómo leerlo", "",
          "- Un enlace grueso no es \"mejor\": es el que más rutas entre tus temas aprovechan.",
          "- Un enlace podado no sobra: solo existe otro camino más corto. Útil para ver redundancias.",
          "- Una nota fuera del esqueleto puede ser un tema nuevo o aislado: candidata a conectarse con algo, o a quedarse como está.", ""]
    return "\n".join(L), {"rho": rho, "vivos": int(vivos.sum())}


def dibujar(g, region, nodos, aristas, D, ruta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rel = D / D.max()
    pos = nx.spring_layout(g, seed=3, k=0.9 / np.sqrt(len(nodos)), iterations=200,
                           weight=None)
    fig, ax = plt.subplots(figsize=(12, 12), dpi=150)
    fig.patch.set_facecolor(FONDO)
    ax.set_facecolor(FONDO)
    # primero los tubos podados, finísimos; luego el esqueleto, con grosor según conductividad
    for k in np.argsort(rel):
        u, v = nodos[aristas[k][0]], nodos[aristas[k][1]]
        x, y = zip(pos[u], pos[v])
        if rel[k] < 0.05:
            ax.plot(x, y, color=TINTA, alpha=0.07, lw=0.4, zorder=1)
        else:
            ru, rv = region.get(u), region.get(v)
            col = PALETA[ru] if ru is not None and ru == rv else "#F2B544"  # ocre: puentes entre regiones
            ax.plot(x, y, color=col, alpha=0.35 + 0.6 * rel[k], lw=0.6 + 6 * rel[k] ** 0.7,
                    solid_capstyle="round", zorder=2)
    grado = dict(g.degree)
    for nodo in nodos:
        r = region.get(nodo)
        ax.scatter(*pos[nodo], s=12 + 9 * grado[nodo], color=PALETA[r] if r is not None else SIN_REGION,
                   edgecolors=FONDO, linewidths=1.2, zorder=3)
    import matplotlib.patheffects as pe
    puestas = []  # no encimar nombres: se salta uno si cae muy cerca de otro ya escrito
    for nodo in sorted(nodos, key=lambda x: -grado[x])[:16]:
        x, y = pos[nodo][0], pos[nodo][1] - 0.035
        if any(abs(x - px) < 0.22 and abs(y - py) < 0.045 for px, py in puestas):
            continue
        puestas.append((x, y))
        ax.text(x, y, nombre(nodo), color=TINTA, fontsize=7.5, ha="center", va="top", zorder=4,
                path_effects=[pe.withStroke(linewidth=3, foreground=FONDO)])
    ax.set_title("Physarum del vault — el esqueleto que sobrevive", color=TINTA, fontsize=13,
                 loc="left", fontweight="bold")
    ax.text(0, -0.01, "grosor = conductividad final · color = región · ocre = puente entre regiones · gris = tubo podado",
            transform=ax.transAxes, color="#8C8474", fontsize=8, va="top")
    ax.axis("off")
    fig.tight_layout()
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    fig.savefig(ruta, facecolor=FONDO)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="Physarum sobre la red del vault")
    ap.add_argument("--rondas", type=int, default=6000)
    ap.add_argument("--mu", type=float, default=1.3)
    ap.add_argument("--semilla", type=int, default=7)
    ap.add_argument("--uso", type=float, default=0.5, help="fracción de rondas alimentadas por búsquedas reales")
    args = ap.parse_args()
    g, region, d = cargar()
    eventos = alimento_de_uso(g)
    args.n_eventos = len(eventos)
    # la influencia del uso crece con la evidencia: pocas búsquedas no deben decidir toda la red
    # (con 20 búsquedas recientes llega a la mitad de --uso; con muchas, casi a --uso)
    n_eff = sum(p for p, _ in eventos)
    args.uso = args.uso * n_eff / (n_eff + 20.0)
    nodos, aristas, D, uso = simular(g, args.rondas, args.mu, args.semilla, eventos, args.uso)
    nota = os.path.join(RAIZ, "wiki", "meta", "Physarum del vault.md")
    args.id_nota = None
    if os.path.exists(nota):  # conservar el id estable al regenerar la nota
        with open(nota, encoding="utf-8") as f:
            m = re.search(r"^id:\s*(\S+)\s*$", f.read().split("\n---", 1)[0], re.M)
        args.id_nota = m.group(1) if m else None
    texto, res = informe(g, region, d, nodos, aristas, D, uso, args)
    with open(nota, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)
    dibujar(g, region, nodos, aristas, D, os.path.join(RAIZ, "_attachments", "physarum-del-vault.png"))
    with open(os.path.join(RAIZ, ".cerebro", "salida", "physarum.json"), "w", encoding="utf-8") as f:
        ids = {}
        try:  # ids estables: ruta.py sigue la vía aunque la nota se renombre antes de la próxima actualización
            for k, e in hipocampo.cargar()["notas"].items():
                if not k.startswith("ruta:"):
                    ids["wiki/" + e["ruta"]] = k
        except Exception:
            pass
        json.dump([{"u": nodos[i], "v": nodos[j], "D": float(x), "u_id": ids.get(nodos[i]), "v_id": ids.get(nodos[j])}
                   for (i, j), x in zip(aristas, D)], f, ensure_ascii=False, indent=0)
    print(f"Physarum: {res['vivos']} de {len(aristas)} enlaces sobreviven, rho={res['rho']:.2f}")


if __name__ == "__main__":
    main()
