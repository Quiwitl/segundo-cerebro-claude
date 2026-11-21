# -*- coding: utf-8 -*-
"""pasado.py: arma una "cápsula" con lo que el usuario sabía y decía hasta una fecha.

Sirve para hablar con su yo del pasado: Claude lee solo la cápsula y responde
como si fuera esa fecha. No toca el vault; la cápsula se escribe FUERA de él
(por defecto ../vault-pasado/FECHA, junto al vault) para que Obsidian no la indexe ni git la suba.

Uso, desde la raíz del vault:
    python .cerebro\\pasado.py 2026-06-30
    python .cerebro\\pasado.py 2026-06-30 --salida E:\\capsulas

Qué entra:
  - chats/AAAA-MM.md: tus mensajes en claude.ai hasta esa fecha (solo lo que tú
    escribiste, recortado si es muy largo), del export más reciente en .raw/.
  - notas/: el vault tal como estaba en git en esa fecha (desde el primer commit;
    antes de eso no hay notas, solo chats).
  - LEEME.md: las reglas para que Claude responda como tu yo de esa fecha.
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_MSG = 1500  # caracteres por mensaje; los pegados largos (código, PDFs) se recortan


def export_mas_reciente():
    zips = sorted(glob.glob(os.path.join(RAIZ, ".raw", "export-claude-*", "conversations-*.zip")))
    if not zips:
        sys.exit("No encontré un export de claude.ai en .raw/export-claude-*/")
    return zips[-1]


def texto(m):
    t = m.get("text") or ""
    if not t and isinstance(m.get("content"), list):
        t = "\n".join(b.get("text", "") for b in m["content"] if b.get("type") == "text")
    t = t.strip()
    return t if len(t) <= MAX_MSG else t[:MAX_MSG] + " […recortado]"


def chats(fecha_fin, destino):
    z = zipfile.ZipFile(export_mas_reciente())
    convs = json.loads(z.read("conversations.json"))
    por_mes, total_msgs, total_chats = {}, 0, 0
    for c in sorted(convs, key=lambda c: c["created_at"]):
        msgs = [m for m in c.get("chat_messages", [])
                if m.get("sender") == "human" and m["created_at"] < fecha_fin and texto(m)]
        if not msgs:
            continue
        total_chats += 1
        total_msgs += len(msgs)
        mes = c["created_at"][:7]
        bloque = [f"## {c.get('name') or 'Sin título'} — {c['created_at'][:10]}", ""]
        # el resumen del export lo escribió Claude con la conversación completa:
        # solo sirve si la conversación terminó antes de la fecha
        if c.get("summary") and c.get("updated_at", "9") < fecha_fin:
            bloque += ["> Resumen de Claude: " + c["summary"].strip().replace("\n", " ")[:600], ""]
        for m in msgs:
            bloque += [f"**{m['created_at'][:16].replace('T', ' ')}** — " + texto(m), ""]
        por_mes.setdefault(mes, []).append("\n".join(bloque))
    os.makedirs(os.path.join(destino, "chats"), exist_ok=True)
    for mes, bloques in por_mes.items():
        with open(os.path.join(destino, "chats", mes + ".md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(f"# Mis mensajes en claude.ai — {mes}\n\n" + "\n\n".join(bloques) + "\n")
    return total_chats, total_msgs


def notas(fecha_fin, destino):
    git = ["git", "-C", RAIZ]
    commit = subprocess.run(git + ["rev-list", "-1", f"--before={fecha_fin}", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    if not commit:
        return 0, None
    rutas = subprocess.run(git + ["ls-tree", "-r", "--name-only", commit, "wiki"],
                           capture_output=True, text=True, encoding="utf-8").stdout.splitlines()
    n = 0
    for r in rutas:
        if not r.endswith(".md"):
            continue
        datos = subprocess.run(git + ["show", f"{commit}:{r}"], capture_output=True).stdout
        p = os.path.join(destino, "notas", *r.split("/")[1:])
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(datos)
        n += 1
    return n, commit[:7]


LEEME = """# Cápsula del {fecha}

Eres Claude ayudando al usuario a conversar con **su yo del {fecha}**.

Reglas:
1. Usa solo lo que está en esta carpeta. Lo que pasó después del {fecha} no existe para esta conversación.
2. Responde como él lo habría dicho entonces, en primera persona y con su forma de escribir de esos mensajes.
3. Cada vez que afirmes algo, di de qué chat o nota sale (título y fecha) para que pueda comprobarlo.
4. Si algo no aparece en la cápsula, dilo ("en ese momento no lo había hablado") en lugar de inventarlo.
5. Si el usuario pregunta por el futuro, contesta como alguien que todavía no lo sabe.
6. Al final de la conversación, si lo pide, sal del papel y comenta qué cambió entre ese yo y el de hoy.

Contenido: {chats} conversaciones con {msgs} mensajes suyos hasta el {fecha} (carpeta chats/).
{notas_linea}
"""


def main():
    ap = argparse.ArgumentParser(description="Cápsula de lo que sabías hasta una fecha")
    ap.add_argument("fecha", help="AAAA-MM-DD; la cápsula incluye hasta el final de ese día")
    ap.add_argument("--salida", default=None, help="carpeta base (por defecto vault-pasado, junto al vault)")
    a = ap.parse_args()
    try:
        dia = dt.date.fromisoformat(a.fecha)
    except ValueError:
        sys.exit("La fecha va como AAAA-MM-DD, por ejemplo 2026-06-30")
    fecha_fin = (dia + dt.timedelta(days=1)).isoformat()  # comparaciones de texto ISO: < día siguiente
    base = a.salida or os.path.join(os.path.dirname(RAIZ.rstrip("\\/")), "vault-pasado")
    destino = os.path.join(base, a.fecha)
    if os.path.exists(destino):
        sys.exit(f"Ya existe {destino}: bórrala o elige otra fecha")
    os.makedirs(destino)
    nc, nm = chats(fecha_fin, destino)
    nn, commit = notas(fecha_fin, destino)
    notas_linea = (f"Notas del vault tal como estaban en git ({commit}): {nn} (carpeta notas/)."
                   if nn else "No hay notas del vault anteriores a esa fecha en git, así que solo hay chats.")
    with open(os.path.join(destino, "LEEME.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(LEEME.format(fecha=a.fecha, chats=nc, msgs=nm, notas_linea=notas_linea))
    print(f"Cápsula {a.fecha}: {nc} chats, {nm} mensajes, {nn} notas -> {destino}")


if __name__ == "__main__":
    main()
