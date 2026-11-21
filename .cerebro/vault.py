# -*- coding: utf-8 -*-
"""vault.py: herramienta fija para que Claude (o el usuario) mantenga el vault.

Solo usa la biblioteca estándar. Escribe siempre UTF-8 con saltos LF.

Uso (desde la raíz del vault):
    python .cerebro/vault.py aplicar plan.json [--dry]   cambios en lote, todo o nada
    python .cerebro/vault.py indice                      regenera index.md y los _index.md
    python .cerebro/vault.py verificar                   acentos, enlaces, frontmatter, regla dispersa
    python .cerebro/vault.py descripciones [carpeta]     lectura nivel 1: ruta | descripción
    python .cerebro/vault.py estado                      muestra el registro de actualizaciones
    python .cerebro/vault.py estado --corte 2026-10-17T20:10 --chats id1,id2 [--nota "Nombre"]
    python .cerebro/vault.py estado --init               reconstruye el registro desde las notas fuente

Operaciones del plan (lista JSON de objetos con "op"):
    {"op": "nueva", "ruta": "learning/X.md", "meta": {...}, "cuerpo": "..."}
    {"op": "anexar", "ruta": "...", "texto": "..."}                 al final de la nota
    {"op": "insertar_tras", "ruta": "...", "ancla": "...", "texto": "..."}
    {"op": "reemplazar", "ruta": "...", "viejo": "...", "nuevo": "..."}
    {"op": "meta", "ruta": "...", "campos": {"description": "...", "privado": true}}
    {"op": "log", "titulo": "actualizacion | ...", "puntos": ["...", "..."]}
Las rutas son relativas a wiki/. Cada operación toca `updated:`.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import uuid

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI = os.path.join(RAIZ, "wiki")
ESTADO = os.path.join(RAIZ, ".cerebro", "estado.json")
HOY = dt.date.today().isoformat()

NAVEGACION = {"index", "_index", "log", "hot", "overview"}
MAPAS = "hipocampo"  # wiki/hipocampo/: mapas que genera hipocampo.py, no son notas
CARPETAS = [  # orden y título de las secciones de index.md
    ("areas", "Areas"), ("learning", "Learning"), ("concepts", "Concepts"),
    ("resources", "Resources"), ("questions", "Questions"), ("sources", "Sources"),
    ("sessions", "Sessions"), ("meta", "Meta"),
]
ORDEN_CAMPOS = ["type", "title", "id", "description", "created", "updated", "tags", "status",
                "privado", "related", "raw"]
MOJIBAKE = re.compile(r"Ã[ -¿]|�")
WIKILINK = re.compile(r"!?\[\[([^\]\|#\^]+)(?:[#\^][^\]\|]*)?(?:\|[^\]]*)?\]\]")
CODIGO = re.compile(r"```.*?```|`[^`\n]*`", re.S)
CHAT = re.compile(r"claude\.ai/chat/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ------------------------------------------------------------------ archivos
def abs_(rel):
    rel = rel.replace("\\", "/")
    if not rel.endswith(".md"):
        rel += ".md"
    return os.path.join(WIKI, *rel.split("/"))


def leer(p):
    with open(p, encoding="utf-8") as f:
        return f.read().replace("\r\n", "\n")


def escribir(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


def notas():
    """Todas las notas .md de wiki/, como rutas relativas sin extensión."""
    out = []
    for d, subdirs, fs in os.walk(WIKI):
        subdirs[:] = sorted(s for s in subdirs if not s.startswith("."))
        for f in sorted(fs):
            if f.endswith(".md"):
                out.append(os.path.relpath(os.path.join(d, f), WIKI).replace("\\", "/")[:-3])
    return out


def nuevo_id():
    """Id estable de nota: no cambia aunque la nota se renombre o se mueva."""
    return "n" + uuid.uuid4().hex[:8]


def de_contenido(rel):
    """Notas de contenido: ni navegación ni mapas generados."""
    return rel.rsplit("/", 1)[-1] not in NAVEGACION and rel.split("/")[0] != MAPAS


# ------------------------------------------------------------------ frontmatter
def partir(s):
    """Devuelve (lineas_frontmatter | None, cuerpo)."""
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", s, re.S)
    if not m:
        return None, s
    return m.group(1).split("\n"), m.group(2)


def campos(s):
    fm, _ = partir(s)
    out = {}
    for linea in fm or []:
        m = re.match(r"^([A-Za-z_]+):\s?(.*)$", linea)
        if m:
            v = m.group(2).strip()
            if v.startswith('"') and v.endswith('"') and len(v) > 1:
                try:
                    v = json.loads(v)
                except ValueError:
                    v = v[1:-1]
            out[m.group(1)] = v
    return out


def valor_yaml(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        return json.dumps(v, ensure_ascii=False)
    v = str(v)
    if v == "" or re.search(r"[:#\[\]{}\"',&*!|>%@`]", v) or v != v.strip():
        return json.dumps(v, ensure_ascii=False)
    return v


def poner_campos(s, nuevos):
    fm, cuerpo = partir(s)
    if fm is None:
        fm, cuerpo = [], "\n" + s
    claves = [re.match(r"^([A-Za-z_]+):", l).group(1) if re.match(r"^([A-Za-z_]+):", l) else None for l in fm]
    for k, v in nuevos.items():
        linea = f"{k}: {valor_yaml(v)}"
        if v is None:  # borrar campo
            fm = [l for l, c in zip(fm, claves) if c != k]
            claves = [c for c in claves if c != k]
        elif k in claves:
            fm[claves.index(k)] = linea
        else:
            # insertar respetando ORDEN_CAMPOS cuando se pueda
            pos = len(fm)
            if k in ORDEN_CAMPOS:
                despues = ORDEN_CAMPOS[ORDEN_CAMPOS.index(k) + 1:]
                for i, c in enumerate(claves):
                    if c in despues:
                        pos = i
                        break
            fm.insert(pos, linea)
            claves.insert(pos, k)
    return "---\n" + "\n".join(fm) + "\n---\n" + cuerpo


def bump(s):
    return poner_campos(s, {"updated": HOY}) if partir(s)[0] is not None else s


# ------------------------------------------------------------------ aplicar
def aplicar(plan_path, dry=False):
    with open(plan_path, encoding="utf-8-sig") as f:
        plan = json.load(f)
    if isinstance(plan, dict):
        plan = plan.get("ops", [])
    memoria = {}  # ruta absoluta -> contenido nuevo (todo o nada)

    def actual(p):
        if p in memoria:
            return memoria[p]
        if not os.path.exists(p):
            raise SystemExit(f"ERROR: no existe {os.path.relpath(p, WIKI)}")
        return leer(p)

    for i, op in enumerate(plan, 1):
        tipo = op.get("op")
        if tipo == "log":
            p = abs_("log")
            s = actual(p)
            fm, cuerpo = partir(s)
            inicio = len(s) - len(cuerpo)  # el separador se busca después del frontmatter
            ancla = "\n---\n\n"
            k = s.find(ancla, inicio)
            if k < 0:
                raise SystemExit("ERROR: log.md sin separador '---' después del encabezado")
            entrada = f"## [{op.get('fecha', HOY)}] {op['titulo']}\n\n" + "\n".join(f"- {x}" for x in op["puntos"]) + "\n\n"
            k += len(ancla)
            memoria[p] = bump(s[:k] + entrada + s[k:])
            continue
        p = abs_(op["ruta"])
        rel = os.path.relpath(p, WIKI)
        if tipo == "nueva":
            if os.path.exists(p) or p in memoria:
                raise SystemExit(f"ERROR op {i}: ya existe {rel}")
            meta = {"type": "note", "title": os.path.basename(p)[:-3], "id": nuevo_id(), "created": HOY, "updated": HOY,
                    "tags": [], "status": "developing", "related": []}
            meta.update(op.get("meta", {}))
            orden = [k for k in ORDEN_CAMPOS if k in meta] + [k for k in meta if k not in ORDEN_CAMPOS]
            fm = "\n".join(f"{k}: {valor_yaml(meta[k])}" for k in orden)
            memoria[p] = f"---\n{fm}\n---\n\n{op['cuerpo'].strip()}\n"
        elif tipo == "anexar":
            s = actual(p)
            memoria[p] = bump(s.rstrip("\n") + "\n\n" + op["texto"].strip("\n") + "\n")
        elif tipo in ("insertar_tras", "reemplazar"):
            s = actual(p)
            viejo = op["ancla"] if tipo == "insertar_tras" else op["viejo"]
            n = s.count(viejo)
            if n != 1:
                raise SystemExit(f"ERROR op {i} ({tipo}) en {rel}: el texto aparece {n} veces")
            nuevo = viejo + op["texto"] if tipo == "insertar_tras" else op["nuevo"]
            memoria[p] = bump(s.replace(viejo, nuevo))
        elif tipo == "meta":
            s = actual(p)
            nuevos = dict(op["campos"])
            if partir(s)[0] is None:  # nota sin frontmatter: crear uno mínimo
                base = {"type": "meta", "title": os.path.basename(p)[:-3], "created": HOY}
                base.update(nuevos)
                nuevos = base
            memoria[p] = bump(poner_campos(s, nuevos))
        else:
            raise SystemExit(f"ERROR op {i}: operación desconocida {tipo!r}")

    for p, s in memoria.items():
        if MOJIBAKE.search(s) and not MOJIBAKE.search(leer(p) if os.path.exists(p) else ""):
            raise SystemExit(f"ERROR: acentos rotos en {os.path.relpath(p, WIKI)}; no se escribió nada")
    if not dry:
        # todo o nada de verdad: primero se escriben copias temporales; si alguna falla no se
        # toca ninguna nota. Después se reemplazan (renombrar es casi instantáneo) y al final se imprime,
        # así una salida cortada (BrokenPipe) ya no deja el plan a medias.
        temporales = []
        try:
            for p in sorted(memoria):
                t = p + ".tmp-vault"
                escribir(t, memoria[p])
                temporales.append((t, p))
        except OSError as exc:
            for t, _ in temporales:
                if os.path.exists(t):
                    os.remove(t)
            raise SystemExit(f"ERROR al escribir: {exc}; no se escribió nada")
        for t, p in temporales:
            os.replace(t, p)
    print(f"{len(plan)} operaciones, {len(memoria)} archivos{' (simulación)' if dry else ''}:")
    for p in sorted(memoria):
        print("  ", os.path.relpath(p, WIKI).replace("\\", "/"))


# ------------------------------------------------------------------ índice
def info(rel):
    s = leer(abs_(rel))
    c = campos(s)
    desc = c.get("description", "").strip()
    return {"rel": rel, "nombre": rel.rsplit("/", 1)[-1], "desc": desc, "status": c.get("status", ""),
            "privado": c.get("privado", "") == "true", "updated": c.get("updated", "")}


def linea_indice(x):
    marca = {"seed": " *(semilla)*", "archived": " *(archivado)*"}.get(x["status"], "")
    return f"- [[{x['nombre']}]]{marca} — {x['desc'] or '(sin descripción)'}"


def indice():
    todas = [info(r) for r in notas() if de_contenido(r)]
    estado = cargar_estado()
    # index.md
    p = abs_("index")
    s = leer(p) if os.path.exists(p) else f"---\ntype: meta\ntitle: Index\ncreated: {HOY}\nupdated: {HOY}\ntags: [meta]\n---\n"
    fm, _ = partir(s)
    cuerpo = ["# Index", "", "> Generado por `.cerebro/vault.py indice` a partir del campo `description` de cada nota. "
              "No editar a mano: corregir la descripción en la nota y regenerar.", ""]
    for carpeta, titulo in CARPETAS:
        grupo = [x for x in todas if x["rel"].split("/")[0] == carpeta]
        if not grupo:
            continue
        cuerpo += [f"## {titulo}"] + [linea_indice(x) for x in sorted(grupo, key=lambda x: x["nombre"].lower())] + [""]
    mapas = sorted(r for r in notas() if r.split("/")[0] == MAPAS)
    if mapas:
        cuerpo += ["## Mapas del hipocampo", "Un mapa por región del conectoma, con la nota más citada arriba "
                   "(los genera `.cerebro/hipocampo.py`): " + ", ".join(f"[[{r.rsplit('/', 1)[-1]}]]" for r in mapas), ""]
    semillas = [x for x in todas if x["status"] == "seed"]
    if semillas:
        cuerpo += ["## Semillas", "Notas que siguen incompletas: " + ", ".join(f"[[{x['nombre']}]]" for x in semillas), ""]
    cuerpo += ["## Stats", f"- Pages: {len(todas)}",
               f"- Last ingest: {estado.get('ultimo_corte', 'desconocido')}",
               f"- Chats integrados: {len(estado.get('chats', {}))}", ""]
    nuevo = "---\n" + "\n".join(fm) + "\n---\n\n" + "\n".join(cuerpo)
    escribir(p, bump(nuevo))
    # _index.md de cada carpeta
    for carpeta, titulo in CARPETAS:
        pi = os.path.join(WIKI, carpeta, "_index.md")
        if not os.path.isdir(os.path.dirname(pi)):
            continue
        grupo = [x for x in todas if x["rel"].startswith(carpeta + "/")]
        texto = [f"# {titulo}", "", "> Generado por `.cerebro/vault.py indice`.", ""] + \
                [linea_indice(x) for x in sorted(grupo, key=lambda x: x["nombre"].lower())] + [""]
        escribir(pi, "\n".join(texto))
    print(f"index.md y {len(CARPETAS)} _index regenerados ({len(todas)} notas)")


# ------------------------------------------------------------------ verificar
def verificar():
    rels = notas()
    rels_min = {x.lower() for x in rels}
    por_nombre = {}
    for r in rels:
        por_nombre.setdefault(r.rsplit("/", 1)[-1].lower(), r)
    errores, avisos = [], []
    hace7 = (dt.date.today() - dt.timedelta(days=7)).isoformat()
    for r in rels:
        s = leer(abs_(r))
        sin_codigo = re.sub(CODIGO, "", s)
        if MOJIBAKE.search(sin_codigo):
            errores.append(f"acentos rotos: {r}")
        for m in WIKILINK.finditer(sin_codigo):
            t = m.group(1).strip()
            if re.search(r"\.(png|jpe?g|gif|svg|pdf|webp|mp4|mp3|canvas|base)$", t, re.I):
                continue
            base = t.rsplit("/", 1)[-1].lower().removesuffix(".md")
            completo = t.lower().removesuffix(".md").removeprefix("wiki/")
            if base not in por_nombre and completo not in rels_min:
                errores.append(f"enlace roto: {r} → [[{t}]]")
        if not de_contenido(r):
            continue
        c = campos(s)
        if not c:
            errores.append(f"sin frontmatter: {r}")
            continue
        if not c.get("description"):
            avisos.append(f"sin description: {r}")
        if not c.get("id"):
            avisos.append(f"sin id: {r} (python .cerebro/hipocampo.py indexar)")
        rel_links = WIKILINK.findall(c.get("related", ""))
        if c.get("created", "") >= hace7 and len(rel_links) > 3 and r.split("/")[0] in ("concepts", "learning", "resources", "questions"):
            avisos.append(f"regla dispersa: {r} tiene {len(rel_links)} enlaces en related (máx. 3 en notas nuevas)")
    privadas = [r for r in rels if campos(leer(abs_(r))).get("privado") == "true"]
    for e in errores:
        print("ERROR", e)
    for a in avisos:
        print("aviso", a)
    print(f"{len(rels)} notas · {len(errores)} errores · {len(avisos)} avisos · privadas: {', '.join(privadas) or 'ninguna'}")
    return 1 if errores else 0


# ------------------------------------------------------------------ descripciones
def descripciones(carpeta=None):
    for r in notas():
        if carpeta and not r.startswith(carpeta):
            continue
        if not de_contenido(r):
            continue
        x = info(r)
        print(f"{r} | {x['desc'] or '-'}{' | PRIVADO' if x['privado'] else ''}")


# ------------------------------------------------------------------ estado
def cargar_estado():
    if os.path.exists(ESTADO):
        with open(ESTADO, encoding="utf-8") as f:
            return json.load(f)
    return {}


def guardar_estado(e):
    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    with open(ESTADO, "w", encoding="utf-8", newline="\n") as f:
        json.dump(e, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


def estado(args):
    e = cargar_estado()
    if args.init:
        chats = {}
        for r in notas():
            for cid in CHAT.findall(leer(abs_(r))):
                chats.setdefault(cid, r.rsplit("/", 1)[-1])
        e["chats"] = chats
    if args.corte:
        e["ultimo_corte"] = args.corte
    if args.chats:
        e.setdefault("chats", {})
        for cid in args.chats.split(","):
            if cid.strip():
                e["chats"][cid.strip()] = args.nota or e["chats"].get(cid.strip(), "")
    if args.init or args.corte or args.chats:
        e["actualizado"] = dt.datetime.now().isoformat(timespec="minutes")
        guardar_estado(e)
    print(f"última actualización: {e.get('ultimo_corte', '-')} · chats integrados: {len(e.get('chats', {}))} · "
          f"actualizado: {e.get('actualizado', '-')}")


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("aplicar"); a.add_argument("plan"); a.add_argument("--dry", action="store_true")
    sub.add_parser("indice")
    sub.add_parser("verificar")
    d = sub.add_parser("descripciones"); d.add_argument("carpeta", nargs="?")
    e = sub.add_parser("estado")
    e.add_argument("--init", action="store_true"); e.add_argument("--corte"); e.add_argument("--chats"); e.add_argument("--nota")
    args = ap.parse_args()
    if args.cmd == "aplicar":
        aplicar(args.plan, args.dry)
    elif args.cmd == "indice":
        indice()
    elif args.cmd == "verificar":
        sys.exit(verificar())
    elif args.cmd == "descripciones":
        descripciones(args.carpeta)
    elif args.cmd == "estado":
        estado(args)


if __name__ == "__main__":
    main()
