# -*- coding: utf-8 -*-
"""vault.py: herramienta fija para que Claude (o el usuario) mantenga el vault.

Solo usa la biblioteca estándar. Escribe siempre UTF-8 con saltos LF.

Uso (desde la raíz del vault):
    python .cerebro/vault.py aplicar plan.json [--dry]   cambios en lote, todo o nada
    python .cerebro/vault.py publicar plan.json -m "..." [--trailer "..."] [--dry] [--sin-git] [--forzar]
                                                         una escritura completa en un solo comando: comparar,
                                                         aplicar, indice, verificar, git add/commit/push
    python .cerebro/vault.py indice                      regenera index.md y los _index.md
    python .cerebro/vault.py verificar                   acentos, enlaces, frontmatter, privadas en hot.md,
                                                         pendientes sin señal, status y type, regla dispersa
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
import subprocess
import tempfile
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
STATUS = ("seed", "developing", "evergreen", "complete", "archived")
TIPOS = ("area", "learning", "concept", "resource", "question", "source", "session", "meta")


def verificar():
    """Revisa el vault. Cada error y cada aviso dice cómo arreglarlo (→ …).

    Errores (cerrar.py no sube nada si hay alguno):
      acentos rotos, enlaces rotos, notas sin frontmatter, una nota privada enlazada desde
      hot.md (hot.md sale del vault como contexto) y un pendiente sin su señal o al revés.
    Avisos: sin description o sin id, status o type fuera de la lista, regla dispersa y
      notas archivadas que hot.md trata como hilo activo.
    """
    rels = notas()
    rels_min = {x.lower() for x in rels}
    por_nombre = {}
    for r in rels:
        por_nombre.setdefault(r.rsplit("/", 1)[-1].lower(), r)
    errores, avisos = [], []
    hace7 = (dt.date.today() - dt.timedelta(days=7)).isoformat()
    meta = {}
    for r in rels:
        s = leer(abs_(r))
        sin_codigo = re.sub(CODIGO, "", s)
        if MOJIBAKE.search(sin_codigo):
            errores.append(f"acentos rotos: {r} → reescribir el archivo con Python (encoding='utf-8'); PowerShell en línea los rompe")
        for m in WIKILINK.finditer(sin_codigo):
            t = m.group(1).strip()
            if re.search(r"\.(png|jpe?g|gif|svg|pdf|webp|mp4|mp3|canvas|base)$", t, re.I):
                continue
            base = t.rsplit("/", 1)[-1].lower().removesuffix(".md")
            completo = t.lower().removesuffix(".md").removeprefix("wiki/")
            if base not in por_nombre and completo not in rels_min:
                # documentos de código fuera de wiki/ (p. ej. proyectos/x/LEEME): válidos si el archivo existe
                if "/" in t and os.path.isfile(os.path.join(RAIZ, t if t.lower().endswith(".md") else t + ".md")):
                    continue
                errores.append(f"enlace roto: {r} → [[{t}]] → si la nota se renombró, `hipocampo.py resolver \"{t}\"` dice cómo se llama hoy")
        if not de_contenido(r):
            continue
        c = campos(s)
        meta[r] = c
        if not c:
            errores.append(f"sin frontmatter: {r} → copiar el de _templates/Nota.md o crearla con `vault.py aplicar` (op nueva)")
            continue
        if not c.get("description"):
            avisos.append(f"sin description: {r} → una línea con los temas y las palabras con que se buscaría")
        if not c.get("id"):
            avisos.append(f"sin id: {r} → python .cerebro/hipocampo.py indexar")
        if not c.get("generado_por"):
            if c.get("status") not in STATUS:
                avisos.append(f"status {c.get('status') or 'vacío'}: {r} → usar uno de {', '.join(STATUS)}")
            if c.get("type") and c.get("type") not in TIPOS:
                avisos.append(f"type {c.get('type')}: {r} → usar uno de {', '.join(TIPOS)}")
        if bool(c.get("pendiente", "").strip("\"' ")) != bool(c.get("cuando", "").strip("[]\"' ")):
            falta = "cuando" if c.get("pendiente") else "pendiente"
            errores.append(f"pendiente sin señal: {r} → falta `{falta}`; sin los dos campos `buscar` nunca avisa (al cumplirse, quitar ambos)")
        rel_links = WIKILINK.findall(c.get("related", ""))
        if c.get("created", "") >= hace7 and len(rel_links) > 3 and r.split("/")[0] in ("concepts", "learning", "resources", "questions"):
            avisos.append(f"regla dispersa: {r} tiene {len(rel_links)} enlaces en related → dejar los 3 más específicos")
    privadas = [r for r, c in meta.items() if c.get("privado") == "true"]
    # hot.md se lee al empezar cada sesión y viaja fuera del vault: nada privado ahí
    if "hot" in rels:
        hot = re.sub(CODIGO, "", leer(abs_("hot")))
        nombres_priv = {r.rsplit("/", 1)[-1].lower(): r for r in privadas}
        archivadas = {r.rsplit("/", 1)[-1].lower(): r for r, c in meta.items() if c.get("status") == "archived"}
        seccion = ""
        for linea in hot.split("\n"):
            if linea.startswith("## "):
                seccion = linea[3:].strip().lower()
            for m in WIKILINK.finditer(linea):
                base = m.group(1).strip().rsplit("/", 1)[-1].lower().removesuffix(".md")
                if base in nombres_priv:
                    errores.append(f"privada en hot.md: [[{m.group(1).strip()}]] → quitar el enlace y lo que resuma de ella (las notas privadas no salen del vault)")
                if base in archivadas and "active" in seccion and "archivad" not in linea.lower():
                    avisos.append(f"archivada como hilo activo en hot.md: [[{m.group(1).strip()}]] → moverla a la línea de «Archivados» o quitarla")
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
# ------------------------------------------------------------------ publicar
def publicar(args):
    """Una escritura completa en un solo comando, para gastar menos solicitudes (cada llamada relee todo el contexto).

    Se detiene en el primer problema:
      1. hipocampo.py comparar   un `duplicado` (o dos notas iguales en el mismo plan) detiene todo; `pariente` solo avisa
      2. aplicar                 todo o nada (con --dry solo simula y termina)
      3. indice                  index.md y los _index.md
      4. verificar               con errores no se sube nada (código 2): lo aplicado queda en el disco para corregirlo
      5. git add -A, commit y push   salvo --sin-git; si el push falla, código 3 y aviso
    Códigos: 0 bien, 1 detenido antes de escribir, 2 verificar con errores, 3 git o push fallaron.
    """
    py = sys.executable
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    def correr(cmd):
        r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()

    hip = os.path.join(RAIZ, ".cerebro", "hipocampo.py")
    if os.path.exists(hip):
        _, out = correr([py, hip, "comparar", "--plan", args.plan])
        malos = [l for l in out.splitlines() if " duplicado" in l or "mismo plan" in l]
        parientes = [l for l in out.splitlines() if " pariente" in l]
        for l in parientes:
            print("aviso pariente:", l.strip())
        if malos and not args.forzar:
            print("\n".join(malos))
            print("DETENIDO: el plan duplica notas; anexar a la existente o usar --forzar si de verdad son distintas")
            return 1
    try:
        aplicar(args.plan, args.dry)
    except SystemExit as exc:
        print(exc if isinstance(exc.code, str) else f"aplicar falló ({exc.code})")
        return 1
    if args.dry:
        return 0
    indice()
    if verificar():
        print("NO SE SUBIÓ: verificar dio errores; corregirlos y correr `vault.py publicar` con otro plan o `cerrar.py`")
        return 2
    if args.sin_git:
        print("git: omitido (--sin-git)")
        return 0
    codigo, out = correr(["git", "add", "-A"])
    if codigo:
        print("git add falló:", out[-800:])
        return 3
    if correr(["git", "diff", "--cached", "--quiet"])[0] == 0:
        print("git: nada que subir")
        return 0
    mensaje = args.mensaje or "vault | " + os.path.splitext(os.path.basename(args.plan))[0]
    if args.trailer:
        mensaje += "\n\n" + "\n".join(args.trailer)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", suffix=".txt", delete=False) as f:
        f.write(mensaje + "\n")   # UTF-8 sin BOM (Set-Content de PowerShell 5 le pone BOM)
        ruta_msg = f.name
    try:
        codigo, out = correr(["git", "commit", "-q", "-F", ruta_msg])
    finally:
        os.remove(ruta_msg)
    if codigo:
        print("git commit falló:", out[-800:])
        return 3
    codigo, out = correr(["git", "push", "-q"])
    _, ultimo = correr(["git", "log", "--oneline", "-1"])
    if codigo:
        print(f"commit {ultimo} hecho, pero el PUSH FALLÓ (el vault no está respaldado):", out[-800:])
        return 3
    print(f"subido: {ultimo}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("aplicar"); a.add_argument("plan"); a.add_argument("--dry", action="store_true")
    pu = sub.add_parser("publicar"); pu.add_argument("plan"); pu.add_argument("-m", "--mensaje")
    pu.add_argument("--trailer", action="append", default=[], help="línea al final del commit (se puede repetir)")
    pu.add_argument("--dry", action="store_true"); pu.add_argument("--sin-git", action="store_true")
    pu.add_argument("--forzar", action="store_true", help="aplicar aunque comparar vea un duplicado")
    sub.add_parser("indice")
    sub.add_parser("verificar")
    d = sub.add_parser("descripciones"); d.add_argument("carpeta", nargs="?")
    e = sub.add_parser("estado")
    e.add_argument("--init", action="store_true"); e.add_argument("--corte"); e.add_argument("--chats"); e.add_argument("--nota")
    args = ap.parse_args()
    if args.cmd == "aplicar":
        aplicar(args.plan, args.dry)
    elif args.cmd == "publicar":
        sys.exit(publicar(args))
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
