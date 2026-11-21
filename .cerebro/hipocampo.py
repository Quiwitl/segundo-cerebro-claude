# -*- coding: utf-8 -*-
"""hipocampo.py: índice hipocampal del vault con cuerpo hongo, para encontrar notas gastando poco.

Como el hipocampo, no guarda el conocimiento: guarda punteros a las notas (la corteza).
Cada entrada lleva un id estable, la ruta, el `description`, los alias y una huella del
contenido. Nadie lo escribe a mano: se regenera solo y se verifica contra los archivos
cada vez que se consulta, así que no puede devolver una ruta que ya no existe.

El cuerpo hongo (FlyHash, Dasgupta et al. 2017) convierte cada texto en un código disperso:
proyección aleatoria a muchas "células de Kenyon" y luego el ganador se lo lleva todo
(solo se quedan las más activas). Dos textos parecidos comparten células aunque no
compartan palabras exactas: "convoluciones" encuentra "convolución".

Uso (desde la raíz del vault, solo biblioteca estándar):
    python .cerebro/hipocampo.py buscar fourier convolución     candidatas, ~1 línea cada una
    python .cerebro/hipocampo.py usar "Nota A" "Nota B" --consulta "fourier"   esto sirvió (y aprende
                                                  esas palabras: la próxima búsqueda igual ya llega)
    python .cerebro/hipocampo.py resolver "Nota o ruta vieja"   a dónde apunta hoy
    python .cerebro/hipocampo.py indexar          asigna ids que falten y regenera todo (actualización)
    python .cerebro/hipocampo.py pendientes       resúmenes viejos, sin description, duplicados
    python .cerebro/hipocampo.py comparar --plan .raw/plan.json   duplicados ANTES de aplicar un plan
    python .cerebro/hipocampo.py comparar "texto de un description"   lo mismo para un texto suelto
    python .cerebro/hipocampo.py evaluar          compara léxico, hongo y mixto con preguntas.json
    python .cerebro/hipocampo.py evaluar --solo-medir   lo mismo sin cambiar el modo (lo usa cerrar.py)
    python .cerebro/hipocampo.py catalogo         ruta + description de las notas no privadas (Project)

Archivos (todos generados; no se editan a mano):
    .cerebro/hipocampo.json        el índice
    .cerebro/uso.jsonl             qué notas sirvieron en cada búsqueda (alimenta a physarum.py)
    wiki/hipocampo/Mapa - *.md     un mapa por región del conectoma, para leer en Obsidian
    .cerebro/salida/evaluacion.json   resultado de `evaluar`; decide el modo por omisión
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
import random
import re
import sys
import unicodedata
import zlib

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import vault  # noqa: E402  (mismo frontmatter, misma escritura UTF-8/LF)

RAIZ = vault.RAIZ
WIKI = vault.WIKI
INDICE = os.path.join(AQUI, "hipocampo.json")
USO = os.path.join(AQUI, "uso.jsonl")
CACHE = os.path.join(AQUI, ".cache-hipocampo.json")  # mtimes de esta máquina; fuera de git
PREGUNTAS = os.path.join(AQUI, "preguntas.json")
SALIDA = os.path.join(AQUI, "salida")
EVALUACION = os.path.join(SALIDA, "evaluacion.json")
CONECTOMA = os.path.join(SALIDA, "conectoma.json")
MAPAS = "hipocampo"  # carpeta dentro de wiki/ con los mapas generados
VERSION = 1

# ------------------------------------------------------------------ cuerpo hongo
# Parámetros fijos: si cambian, cambian todas las huellas (subir VERSION para reindexar).
D_ENTRADA = 1024  # neuronas de proyección (rasgos del texto, por hashing)
N_KENYON = 2048  # células de Kenyon (expansión ×2)
CONEXIONES = 12  # entradas al azar por célula de Kenyon
K_ACTIVAS = 48  # ganadoras que se quedan (~2 %)
SEMILLA = 2017  # el año de Dasgupta, Stevens y Navlakha
UMBRAL_VIEJO = 0.55  # parecido mínimo entre el cuerpo de hoy y el que describía el resumen
UMBRAL_DUPLICADO = 0.80  # parecido de dos descripciones para avisar posible duplicado (pendientes y comparar)
# Medición del 21 oct (90 notas, 4005 parejas): mediana 0.02, p99.9 0.33, máximo real 0.60; una palabra de más
# en el título baja una copia exacta de 1.00 a 0.79. Así que 0.80 solo atrapa copias; `comparar` avisa también
# desde 0.35 (arriba del 99.9 % de las parejas actuales, que a esa altura son notas de verdad emparentadas).
UMBRAL_PARIENTE = 0.35
MINIMO = 0.2  # puntaje mínimo para mostrar una candidata en `buscar`
# Tercer eje (cuándo se usa). Fijados ANTES de medir con preguntas-tiempo.json; no se ajustan a la prueba.
MEDIA_EDICION = 14.0  # días: una nota editada hace dos semanas pesa la mitad
MEDIA_USO = 30.0  # días, igual que physarum.py
PESO_TIEMPO = 0.25  # el tiempo multiplica el puntaje: desempata, nunca saca candidatas sin señal propia
USAR_TIEMPO = False  # lo decide la medición (ver LEEME, «eje del tiempo»)

VACIAS = set("""a al algo ante con contra de del desde donde durante e el ella ellas ellos en entre es esa
ese eso esta este esto estos estas fue ha hay la las le les lo los mas me mi mis muy no o para pero
por que se sin sobre su sus te tu un una uno unos unas y ya como cual cuando the of and to in on for
with is are vs""".split())

_rng = random.Random(SEMILLA)
_CABLES = [_rng.sample(range(D_ENTRADA), CONEXIONES) for _ in range(N_KENYON)]
_POR_ENTRADA = [[] for _ in range(D_ENTRADA)]  # entrada -> células que la escuchan
for _j, _cs in enumerate(_CABLES):
    for _i in _cs:
        _POR_ENTRADA[_i].append(_j)


def plano(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def palabras(s):
    return [w for w in re.findall(r"[a-z0-9]+", plano(s)) if len(w) > 1 and w not in VACIAS]


def _cubeta(rasgo):
    return zlib.crc32(rasgo.encode("utf-8")) % D_ENTRADA


def rasgos(texto):
    """Vector de entrada: palabras y pedazos de 4 letras (atrapan plurales, acentos y erratas)."""
    x = {}
    for w in palabras(texto):
        x[_cubeta("w:" + w)] = x.get(_cubeta("w:" + w), 0.0) + 1.0
        b = f"_{w}_"
        for i in range(len(b) - 3):
            k = _cubeta("g:" + b[i:i + 4])
            x[k] = x.get(k, 0.0) + 0.5
    x = {k: math.sqrt(v) for k, v in x.items()}  # amortigua repeticiones
    n = math.sqrt(sum(v * v for v in x.values())) or 1.0
    return {k: v / n for k, v in x.items()}


def huella(texto, k=K_ACTIVAS):
    """FlyHash: expansión aleatoria dispersa y el ganador se lo lleva todo."""
    act = {}
    for i, v in rasgos(texto).items():
        for j in _POR_ENTRADA[i]:
            act[j] = act.get(j, 0.0) + v
    ganadoras = sorted(act.items(), key=lambda t: (-t[1], t[0]))[:k]
    return sorted(j for j, _ in ganadoras)


def parecido(a, b):
    if not a or not b:
        return 0.0
    return len(set(a) & set(b)) / math.sqrt(len(a) * len(b))


# ------------------------------------------------------------------ lectura de notas
def nuevo_id():
    return vault.nuevo_id()


def _lista(v):
    """Convierte un campo YAML en lista: ["a", "b"], [a, b] o "a"."""
    if isinstance(v, list):
        return v
    v = (v or "").strip()
    if not v:
        return []
    if v.startswith("["):
        try:
            return [str(x) for x in json.loads(v)]
        except ValueError:
            return [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
    return [v]


def _leer_nota(rel, p):
    s = vault.leer(p)
    c = vault.campos(s)
    _, cuerpo = vault.partir(s)
    nombre = rel.rsplit("/", 1)[-1]
    sin_codigo = re.sub(vault.CODIGO, "", s)
    salientes = sorted({m.group(1).strip().rsplit("/", 1)[-1].lower().removesuffix(".md")
                        for m in vault.WIKILINK.finditer(sin_codigo)} - {nombre.lower()})
    return {
        "ruta": rel,
        "titulo": c.get("title") or nombre,
        "alias": [a for a in _lista(c.get("aliases") or c.get("alias")) if a],
        "desc": (c.get("description") or "").strip(),
        "tags": _lista(c.get("tags")),
        "status": c.get("status", ""),
        "privado": c.get("privado", "") == "true",
        "tipo": c.get("type", ""),
        "generada": bool(c.get("generado_por")),  # informes que reescribe un script: su resumen no envejece
        "fecha": str(c.get("updated") or c.get("created") or "")[:10],
        "id_nota": c.get("id", ""),
        "hash": hashlib.sha1(s.encode("utf-8")).hexdigest()[:16],
        "salientes": salientes,
        "_cuerpo": cuerpo,
        # memoria prospectiva: un pendiente que despierta cuando la búsqueda toca su señal
        **({"cuando": [w for w in _lista(c.get("cuando")) if w]} if c.get("cuando") else {}),
        **({"pendiente": c["pendiente"].strip()} if (c.get("pendiente") or "").strip() else {}),
    }


def _archivos():
    """rel -> (ruta absoluta, mtime, tamaño) de las notas que indexa el hipocampo."""
    out = {}
    for rel in vault.notas():
        nombre = rel.rsplit("/", 1)[-1]
        if nombre in vault.NAVEGACION or rel.split("/")[0] == MAPAS:
            continue
        p = vault.abs_(rel)
        st = os.stat(p)
        out[rel] = (p, st.st_mtime_ns, st.st_size)
    return out


def _texto_hongo(e):
    return " ".join([e["titulo"], " ".join(e["alias"]), " ".join(e["tags"]), e["desc"]])


# ------------------------------------------------------------------ índice
def cargar():
    if os.path.exists(INDICE):
        try:
            with open(INDICE, encoding="utf-8") as f:
                d = json.load(f)
            if d.get("version") == VERSION:
                return d
        except ValueError:
            pass  # índice dañado: se reconstruye entero, no hay nada que perder
    return {"version": VERSION, "notas": {}}


def guardar(d):
    # una nota por línea: diffs legibles en git
    notas = d["notas"]
    lineas = [json.dumps(k, ensure_ascii=False) + ": " + json.dumps(notas[k], ensure_ascii=False, sort_keys=True)
              for k in sorted(notas, key=lambda k: notas[k]["ruta"].lower())]
    cab = {k: v for k, v in d.items() if k != "notas"}
    texto = "{\n" + "".join(f" {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)},\n" for k, v in sorted(cab.items()))
    texto += ' "notas": {\n  ' + ",\n  ".join(lineas) + "\n }\n}\n"
    vault.escribir(INDICE, texto)


def _regiones():
    """ruta (sin wiki/) -> nombre de la región del conectoma (su nota núcleo)."""
    if not os.path.exists(CONECTOMA):
        return {}
    with open(CONECTOMA, encoding="utf-8") as f:
        con = json.load(f)
    out = {}
    for r in con.get("regiones", []):
        nombre = r["nucleo"][0].rsplit("/", 1)[-1] if r.get("nucleo") else "Sin nombre"
        for m in r.get("miembros", []):
            out[m.removeprefix("wiki/")] = nombre
    return out


def _poner_id(p):
    """Escribe un id nuevo en el frontmatter de la nota (sin tocar `updated`)."""
    i = nuevo_id()
    vault.escribir(p, vault.poner_campos(vault.leer(p), {"id": i}))
    return i


def sincronizar(asignar_ids=False, mapas=True):
    """Pone el índice al día con los archivos. Solo relee las notas que cambiaron.

    Garantía: al terminar, cada entrada apunta a un archivo que existe y su huella
    corresponde a su contenido actual. Devuelve (índice, cambios)."""
    d = cargar()
    viejo = d["notas"]
    por_ruta = {e["ruta"]: k for k, e in viejo.items()}
    cambios = {"nuevas": [], "cambiadas": [], "movidas": [], "borradas": [], "ids": []}
    try:
        with open(CACHE, encoding="utf-8") as f:
            cache = json.load(f)
    except (OSError, ValueError):
        cache = {}
    cache_nuevo = {}

    # 1. qué hay en disco: entradas en caché (archivo sin cambios) o leídas de nuevo
    items = []  # [clave, rel, entrada, leida]
    for rel, (p, mtime, tam) in _archivos().items():
        k_prev = por_ruta.get(rel)
        prev = viejo.get(k_prev) if k_prev else None
        reusar = prev and not (asignar_ids and k_prev.startswith("ruta:"))
        if reusar and "fecha" in prev and cache.get(rel) == [mtime, tam, prev["hash"]]:
            cache_nuevo[rel] = cache[rel]
            items.append([k_prev, rel, prev, False])
            continue
        e = _leer_nota(rel, p)
        if reusar and "fecha" in prev and e["hash"] == prev["hash"]:  # solo cambió la fecha del archivo (clon, copia)
            cache_nuevo[rel] = [mtime, tam, prev["hash"]]
            items.append([k_prev, rel, prev, False])
            continue
        if asignar_ids and not e["id_nota"] and vault.partir(vault.leer(p))[0] is not None:
            e = _leer_nota(rel, p) if _poner_id(p) else e
            cambios["ids"].append(rel)
        items.append([e["id_nota"] or "ruta:" + rel, rel, e, True])

    # 2. ids repetidos (una nota duplicada en Obsidian copia su frontmatter): conserva el id
    #    la que ya lo tenía en esa ruta; la copia recibe uno nuevo o queda provisional
    vistos = {}
    for it in sorted(items, key=lambda it: (viejo.get(it[0], {}).get("ruta") != it[1], it[1])):
        if it[0] in vistos:
            p = vault.abs_(it[1])
            if asignar_ids and vault.partir(vault.leer(p))[0] is not None:
                _poner_id(p)
                it[2], it[3] = _leer_nota(it[1], p), True
                it[0] = it[2]["id_nota"]
                cambios["ids"].append(it[1])
            else:
                it[0] = "ruta:" + it[1]
                if not it[3]:
                    it[2], it[3] = _leer_nota(it[1], p), True
            it.append(True)  # copia: no hereda historia
        vistos[it[0]] = it

    # 3. huellas y vigencia del resumen, solo para lo que se leyó
    nuevo = {}
    for it in items:
        clave, rel, e, leida = it[:4]
        copia = len(it) > 4
        if not leida:
            nuevo[clave] = e
            continue
        p = vault.abs_(rel)
        st = os.stat(p)
        antes = None if copia else (viejo.get(clave) or viejo.get(por_ruta.get(rel, "")))
        cuerpo = e.pop("_cuerpo")
        e.pop("id_nota")
        cache_nuevo[rel] = [st.st_mtime_ns, st.st_size, e["hash"]]
        e["huella"] = huella(_texto_hongo(e))
        h_cuerpo = huella(cuerpo)
        desc_hash = hashlib.sha1(e["desc"].encode("utf-8")).hexdigest()[:10]
        if antes and antes.get("desc_hash") == desc_hash and antes.get("huella_desc"):
            e["huella_desc"] = antes["huella_desc"]  # mismo resumen: se compara con el cuerpo que describía
        else:
            e["huella_desc"] = h_cuerpo  # resumen nuevo o reescrito: describe el cuerpo de hoy
        e["desc_hash"] = desc_hash
        e["vigencia"] = round(parecido(e["huella_desc"], h_cuerpo), 3)
        e["rutas_previas"] = list((antes or {}).get("rutas_previas", []))
        if antes and antes["ruta"] != rel:
            e["rutas_previas"] = (e["rutas_previas"] + [antes["ruta"]])[-5:]
            cambios["movidas"].append(f"{antes['ruta']} → {rel}")
        if antes is None:
            cambios["nuevas"].append(rel)
        elif antes.get("hash") != e["hash"]:
            cambios["cambiadas"].append(rel)
        nuevo[clave] = e

    vivas = {e["ruta"] for e in nuevo.values()}
    for k, e in viejo.items():
        if e["ruta"] not in vivas and k not in nuevo:
            cambios["borradas"].append(e["ruta"])

    # entrantes y región: se recalculan siempre (baratos, no releen archivos)
    por_nombre = {}
    for k, e in nuevo.items():
        por_nombre.setdefault(e["ruta"].rsplit("/", 1)[-1].lower(), k)
        for a in e["alias"]:
            por_nombre.setdefault(a.lower(), k)
    entrantes = {k: 0 for k in nuevo}
    for k, e in nuevo.items():
        for t in e.get("salientes", []):
            destino = por_nombre.get(t)
            if destino and destino != k:
                entrantes[destino] += 1
    region = _regiones()
    for k, e in nuevo.items():
        e["entrantes"] = entrantes[k]
        e["region"] = region.get(e["ruta"])

    hubo = any(cambios.values()) or set(nuevo) != set(viejo) or any(
        (viejo.get(k) or {}).get(c) != e.get(c) for k, e in nuevo.items() for c in ("entrantes", "region"))
    d["notas"] = nuevo
    if hubo or not os.path.exists(INDICE):
        d["actualizado"] = dt.datetime.now().isoformat(timespec="seconds")
        guardar(d)
    if cache_nuevo != cache:
        vault.escribir(CACHE, json.dumps(cache_nuevo, ensure_ascii=False))
    if mapas:
        escribir_mapas(d)
    return d, cambios


# ------------------------------------------------------------------ resolver
def resolver(texto, d=None):
    """Nombre, alias, ruta actual o ruta vieja -> (clave, entrada) o (None, None)."""
    d = d or sincronizar(mapas=False)[0]
    q = plano(texto.strip().replace("\\", "/")).removesuffix(".md").removeprefix("wiki/")
    if q in d["notas"]:
        return q, d["notas"][q]
    for prueba in ("ruta", "previa", "nombre", "titulo", "alias", "parcial"):
        hallados = []
        for k, e in d["notas"].items():
            nombre = plano(e["ruta"].rsplit("/", 1)[-1])
            if prueba == "ruta" and plano(e["ruta"]) == q \
                    or prueba == "previa" and q in (plano(r) for r in e.get("rutas_previas", [])) \
                    or prueba == "previa" and q in (plano(r.rsplit("/", 1)[-1]) for r in e.get("rutas_previas", [])) \
                    or prueba == "nombre" and nombre == q \
                    or prueba == "titulo" and plano(e["titulo"]) == q \
                    or prueba == "alias" and q in (plano(a) for a in e["alias"]) \
                    or prueba == "parcial" and q in nombre:
                hallados.append((k, e))
        if hallados:
            return min(hallados, key=lambda t: len(t[1]["ruta"]))
    return None, None


def rutas_actuales(d=None):
    """Mapa para otras herramientas: 'wiki/<ruta vieja o actual>' e id -> 'wiki/<ruta actual>'."""
    d = d or sincronizar(mapas=False)[0]
    out = {}
    for k, e in d["notas"].items():
        actual = "wiki/" + e["ruta"]
        out[k] = actual
        out[actual] = actual
        for r in e.get("rutas_previas", []):
            out.setdefault("wiki/" + r, actual)
    return out


# ------------------------------------------------------------------ buscar
def _idf(d):
    df = {}
    for e in d["notas"].values():
        for w in set(palabras(_texto_hongo(e) + " " + e["ruta"].rsplit("/", 1)[-1])):
            df[w] = df.get(w, 0) + 1
    n = max(1, len(d["notas"]))
    return lambda w: math.log(1 + n / (1 + df.get(w, 0)))


def _coincide(q, ws):
    # palabra exacta, o mismo arranque largo (plural, conjugación): convoluciones ~ convolucion
    return any(w == q or (len(q) >= 5 and len(w) >= 5 and (w.startswith(q[:max(5, len(q) - 2)]) or q.startswith(w[:max(5, len(w) - 2)])))
               for w in ws)


def vocabulario_aprendido():
    """id -> palabras de las consultas que terminaron en esa nota (`usar --consulta`).

    Es el aprendizaje del hipocampo: si una búsqueda falló y la nota se encontró por otro
    camino, al registrarla con su consulta la próxima búsqueda con esas palabras ya llega."""
    out = {}
    if not os.path.exists(USO):
        return out
    with open(USO, encoding="utf-8") as f:
        for linea in f:
            try:
                x = json.loads(linea)
            except ValueError:
                continue
            for i in x.get("ids", []):
                out.setdefault(i, set()).update(palabras(x.get("q", "")))
    return out


def puntaje_lexico(consulta, e, idf, aprendidas=()):
    campos = [
        (3.0, palabras(e["ruta"].rsplit("/", 1)[-1] + " " + e["titulo"])),
        (3.0, palabras(" ".join(e["alias"]))),
        (2.0, palabras(" ".join(e["tags"]))),
        (2.0, list(aprendidas)),
        (1.0, palabras(e["desc"])),
    ]
    total = 0.0
    for q in set(palabras(consulta)):
        mejor = max((peso for peso, ws in campos if _coincide(q, ws)), default=0.0)
        total += mejor * idf(q)
    return total


def modo_por_omision():
    try:
        with open(EVALUACION, encoding="utf-8") as f:
            return json.load(f).get("ganador", "lexico")
    except (OSError, ValueError):
        return "lexico"  # regla de corte: el hongo entra solo si gana en las preguntas de prueba


def actividad(d, hoy=None):
    """id -> 0..1: qué tan viva está cada nota hoy (tercer eje: cuándo se usa).

    Lo mayor entre la edición reciente (`updated` del frontmatter, mitad cada MEDIA_EDICION días)
    y el uso reciente (`uso.jsonl`, mitad cada MEDIA_USO días). Las notas que reescribe un script
    no cuentan como editadas: su fecha cambia sola."""
    hoy = hoy or dt.date.today()
    uso = {}
    for peso, ids in eventos_de_uso(MEDIA_USO):
        for i in ids:
            uso[i] = uso.get(i, 0.0) + peso
    out = {}
    for k, e in d["notas"].items():
        ed = 0.0
        if not e.get("generada"):
            try:
                f = dt.date.fromisoformat(e.get("fecha", ""))
                ed = 0.5 ** (max((hoy - f).days, 0) / MEDIA_EDICION)
            except ValueError:
                pass
        out[k] = max(ed, min(1.0, uso.get(k, 0.0)))
    return out


def ranking(consulta, d, modo, tiempo=None):
    tiempo = USAR_TIEMPO if tiempo is None else tiempo
    act = actividad(d) if tiempo else {}
    idf = _idf(d)
    hq = huella(consulta)
    aprendido = vocabulario_aprendido()
    filas = []
    lex_max = 0.0
    for k, e in d["notas"].items():
        lx = puntaje_lexico(consulta, e, idf, aprendido.get(k, ()))
        ho = parecido(hq, e["huella"])
        lex_max = max(lex_max, lx)
        filas.append([k, e, lx, ho])
    for f in filas:
        lx = f[2] / lex_max if lex_max else 0.0
        if modo == "lexico":
            s = lx
        elif modo == "hongo":
            s = f[3]
        else:
            s = lx + 0.8 * f[3]
        s *= 1.0 + PESO_TIEMPO * act.get(f[0], 0.0)
        # entre parecidas, gana la que más notas citan (punto de entrada más útil)
        f.append(s + 0.002 * min(f[1].get("entrantes", 0), 20) if s > 0 else 0.0)
    filas.sort(key=lambda f: -f[4])
    return [f for f in filas if f[4] > 0]


def inicio_cuerpo(rel):
    """Primera línea después del frontmatter (desde 1): ahí empieza lo que vale la pena leer.

    El frontmatter ocupa ~11 líneas y repite la description que `buscar` ya mostró."""
    ls = vault.leer(vault.abs_(rel)).split("\n")
    if ls and ls[0].strip() == "---":
        for i in range(1, len(ls)):
            if ls[i].strip() == "---":
                return i + 2
    return 1


def buscar(consulta, n=5, modo=None, cuerpo=True):
    d, cambios = sincronizar()
    modo = modo or modo_por_omision()
    todas = ranking(consulta, d, modo)
    tope = todas[0][4] if todas else 0.0
    # sin ruido: solo candidatas con señal propia y cerca de la mejor
    filas = [f for f in todas if f[4] >= max(MINIMO, 0.3 * tope)][:n]
    if cambios["nuevas"] or cambios["cambiadas"] or cambios["movidas"] or cambios["borradas"]:
        print("(hipocampo al día: " + ", ".join(f"{len(v)} {k}" for k, v in cambios.items() if v and k != "ids") + ")")
    if not filas:
        print(f"Sin coincidencias en el índice (modo {modo}).")
    for k, e, lx, ho, s in filas:
        marcas = []
        if e["privado"]:
            marcas.append("PRIVADA")
        if e.get("vigencia", 1) < UMBRAL_VIEJO and not e.get("generada"):
            marcas.append("resumen viejo")
        if e["status"] == "archived":
            marcas.append("archivada")
        extra = f" [{', '.join(marcas)}]" if marcas else ""
        print(f"{e['ruta']} | l.{inicio_cuerpo(e['ruta'])} | {e['desc'] or '(sin description)'} | ←{e.get('entrantes', 0)}"
              f"{' | ' + e['region'] if e.get('region') else ''}{extra}")
    for linea in pendientes_con_senal(consulta, d):
        print(linea)
    if cuerpo and not filas:
        # último recurso: el texto completo, solo para decir dónde está, sin volcarlo
        qs = palabras(consulta)
        hits = []
        for e in d["notas"].values():
            texto = plano(vault.leer(vault.abs_(e["ruta"])))
            c = sum(texto.count(q) for q in qs)
            if c:
                hits.append((c, e["ruta"]))
        for c, r in sorted(hits, reverse=True)[:n]:
            print(f"{r} | l.{inicio_cuerpo(r)} | aparece {c} veces en el texto")


def pendientes_con_senal(consulta, d):
    """Memoria prospectiva: «si aparece X, recordar Y» (intenciones de implementación).

    Una nota con `pendiente:` y `cuando: [palabras]` en el frontmatter avisa en `buscar`
    cuando alguna palabra de la consulta toca su señal. Así lo que depende de un tema, no de
    una fecha, sale de hot.md y vuelve en el momento justo."""
    qs = set(palabras(consulta))
    out = []
    for e in d["notas"].values():
        if not e.get("pendiente") or not e.get("cuando"):
            continue
        senal = palabras(" ".join(e["cuando"]))
        if any(_coincide(q, senal) for q in qs):
            out.append(f"⏰ pendiente ({e['ruta'].rsplit('/', 1)[-1]}): {e['pendiente']}")
    return out


# ------------------------------------------------------------------ usar
def usar(nombres, consulta=""):
    d, _ = sincronizar(mapas=False)
    ids, faltan = [], []
    for n in nombres:
        k, e = resolver(n, d)
        if k is None:
            faltan.append(n)
        elif k.startswith("ruta:"):
            faltan.append(n + " (sin id todavía: corre `hipocampo.py indexar`)")
        else:
            ids.append(k)
    if faltan:
        sys.exit("No registré nada; no encontré: " + "; ".join(faltan))
    linea = {"t": dt.datetime.now().isoformat(timespec="minutes"), "q": consulta, "ids": ids}
    with open(USO, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(linea, ensure_ascii=False) + "\n")
    print(f"registrado: {', '.join(d['notas'][i]['ruta'] for i in ids)} (Physarum lo usará en la próxima pasada)")


def eventos_de_uso(dias_media=30.0):
    """[(peso, [ids])] con peso que decae a la mitad cada `dias_media` días. Lo usa physarum.py."""
    if not os.path.exists(USO):
        return []
    hoy = dt.datetime.now()
    out = []
    with open(USO, encoding="utf-8") as f:
        for linea in f:
            try:
                x = json.loads(linea)
                edad = (hoy - dt.datetime.fromisoformat(x["t"])).total_seconds() / 86400
                out.append((0.5 ** (max(edad, 0) / dias_media), x["ids"]))
            except (ValueError, KeyError):
                continue
    return out


# ------------------------------------------------------------------ mapas
def escribir_mapas(d):
    grupos = {}
    for e in d["notas"].values():
        grupos.setdefault(e.get("region") or "Sin región", []).append(e)
    carpeta = os.path.join(WIKI, MAPAS)
    os.makedirs(carpeta, exist_ok=True)
    escritos = set()
    for region, es in sorted(grupos.items()):
        titulo = f"Mapa - {region}"
        es.sort(key=lambda e: (-e.get("entrantes", 0), e["ruta"].lower()))
        L = ["---", "type: indice", f"title: {vault.valor_yaml(titulo)}",
             f"description: {vault.valor_yaml(f'Mapa del hipocampo: {len(es)} notas de la región de {region}, de la más citada a la menos')}",
             "tags: [hipocampo, indice]", 'generado_por: ".cerebro/hipocampo.py"', "---", "",
             f"# {titulo}", "",
             "> Generado por `.cerebro/hipocampo.py` a partir del `description` de cada nota y de las regiones "
             "de `conectoma.py`. No se edita: se sobrescribe. Para cambiar una línea, corrige el `description` de la nota.",
             ""]
        for e in es:
            marca = " *(privada)*" if e["privado"] else " *(archivada)*" if e["status"] == "archived" else ""
            L.append(f"- [[{e['ruta'].rsplit('/', 1)[-1]}]]{marca} · ←{e.get('entrantes', 0)} — {e['desc'] or '(sin description)'}")
        texto = "\n".join(L) + "\n"
        p = os.path.join(carpeta, titulo + ".md")
        escritos.add(os.path.basename(p))
        if not os.path.exists(p) or vault.leer(p) != texto:
            vault.escribir(p, texto)
    for f in os.listdir(carpeta):  # mapas de regiones que ya no existen
        if f.endswith(".md") and f.startswith("Mapa - ") and f not in escritos:
            os.remove(os.path.join(carpeta, f))


# ------------------------------------------------------------------ pendientes
def pendientes(d=None, imprimir=True):
    d = d or sincronizar()[0]
    viejos = sorted((e["vigencia"], e["ruta"]) for e in d["notas"].values()
                    if e.get("vigencia", 1) < UMBRAL_VIEJO and e["desc"] and not e.get("generada"))
    sin_desc = sorted(e["ruta"] for e in d["notas"].values() if not e["desc"])
    sin_id = sorted(e["ruta"] for k, e in d["notas"].items() if k.startswith("ruta:"))
    es = list(d["notas"].values())
    dup = []
    for i in range(len(es)):
        for j in range(i + 1, len(es)):
            if es[i]["desc"] and es[j]["desc"]:
                p = parecido(es[i]["huella"], es[j]["huella"])
                if p >= UMBRAL_DUPLICADO:
                    dup.append((p, es[i]["ruta"], es[j]["ruta"]))
    dup.sort(reverse=True)
    con_senal = sorted((e["ruta"], e["pendiente"], e.get("cuando", [])) for e in d["notas"].values() if e.get("pendiente"))
    if imprimir:
        print(f"Resúmenes viejos (el cuerpo cambió desde que se escribió el description): {len(viejos)}")
        for v, r in viejos:
            print(f"  - {r}  (parecido {v:.2f})")
        print(f"Sin description: {len(sin_desc)}" + "".join(f"\n  - {r}" for r in sin_desc))
        print(f"Sin id: {len(sin_id)}" + (" → `hipocampo.py indexar`" if sin_id else ""))
        print(f"Posibles duplicados (separación de patrones): {len(dup)}")
        for p, a, b in dup[:15]:
            print(f"  - {a} ≈ {b}  ({p:.2f})")
        print(f"Pendientes con señal: {len(con_senal)}")
        for r, t, c in con_senal:
            print(f"  - {r}: {t}  (señal: {', '.join(c) or 'sin señal'})")
    return {"viejos": viejos, "sin_desc": sin_desc, "sin_id": sin_id, "duplicados": dup, "con_senal": con_senal}


# ------------------------------------------------------------------ comparar (antes de aplicar un plan)
def _desde_plan(ruta_plan, d):
    """Lo que un plan va a crear o cuyo description va a cambiar: [(etiqueta, clave en el índice o None, texto)].

    El texto se arma igual que `_texto_hongo` (título, alias, tags y description), para que su huella
    sea comparable con las del índice."""
    with open(ruta_plan, encoding="utf-8-sig") as f:
        plan = json.load(f)
    if isinstance(plan, dict):
        plan = plan.get("ops", [])
    out = []
    for op in plan:
        tipo = op.get("op")
        if tipo == "nueva":
            meta = op.get("meta", {})
            rel = op["ruta"].replace("\\", "/").removesuffix(".md")
            e = {"titulo": meta.get("title") or rel.rsplit("/", 1)[-1],
                 "alias": [a for a in _lista(meta.get("aliases") or meta.get("alias")) if a],
                 "tags": _lista(meta.get("tags")), "desc": str(meta.get("description") or "").strip()}
            if e["desc"]:
                out.append((f'nueva "{rel.rsplit("/", 1)[-1]}"', None, _texto_hongo(e)))
        elif tipo == "meta" and "description" in op.get("campos", {}):
            k, e = resolver(op["ruta"], d)
            if e is None:
                continue  # log, índices y otras notas fuera del hipocampo
            e = dict(e, desc=str(op["campos"]["description"]).strip())
            out.append((f'meta "{e["ruta"].rsplit("/", 1)[-1]}"', k, _texto_hongo(e)))
    return out


def comparar(textos=(), ruta_plan=None):
    """Separación de patrones antes de escribir: compara cada nota nueva (o description reescrito)
    con las que ya existen y con las demás del mismo plan. Dos niveles: `duplicado` (≥ UMBRAL_DUPLICADO,
    casi una copia) y `pariente` (≥ UMBRAL_PARIENTE: revisar si conviene anexar en vez de crear).
    Solo lee: no toca el índice, ni uso.jsonl, ni el plan. Lo usa el agente revisor."""
    d, _ = sincronizar(mapas=False)
    nuevas = _desde_plan(ruta_plan, d) if ruta_plan else []
    nuevas += [(f'texto "{t[:40]}"', None, t) for t in textos]
    hs = [(et, k, huella(tx)) for et, k, tx in nuevas]
    filas = []
    for i, (et, k, h) in enumerate(hs):
        for k2, e in d["notas"].items():
            if k2 != k and e["desc"]:
                p = parecido(h, e["huella"])
                if p >= UMBRAL_PARIENTE:
                    filas.append((p, et, f'"{e["ruta"].rsplit("/", 1)[-1]}"', e["ruta"]))
        for et2, k2, h2 in hs[i + 1:]:
            p = parecido(h, h2)
            if p >= UMBRAL_PARIENTE and not (k and k == k2):
                filas.append((p, et, et2.split(" ", 1)[1], "mismo plan"))
    filas.sort(key=lambda f: -f[0])
    if not nuevas:
        print("sin parecidos (el plan no crea notas ni cambia descriptions)")
    elif not filas:
        print(f"sin parecidos ({len(nuevas)} revisadas, umbral {UMBRAL_PARIENTE:.2f})")
    for p, a, b, donde in filas:
        nivel = "duplicado" if p >= UMBRAL_DUPLICADO else "pariente"
        print(f"{a} ~ {b} {p:.2f} {nivel} | {donde}")
    return filas


# ------------------------------------------------------------------ catálogo para el Project
def catalogo(destino=None):
    """Lista ruta + description de las notas NO privadas, para un Project de claude.ai.

    Así, en un chat del Project sin acceso al disco, Claude sabe qué hay en el vault. Las notas con
    `privado: true` no aparecen ni por nombre."""
    d, _ = sincronizar(mapas=False)
    destino = destino or os.path.join(SALIDA, "catalogo-project.md")
    publicas = [e for e in d["notas"].values() if not e["privado"]]
    grupos = {}
    for e in publicas:
        grupos.setdefault(e["ruta"].split("/")[0], []).append(e)
    L = ["# Catálogo del vault", "",
         f"Generado por `.cerebro/hipocampo.py catalogo` el {dt.date.today().isoformat()}: {len(publicas)} notas. "
         "Una línea por nota: nombre y de qué trata. No incluye las notas privadas. "
         "El contenido completo está en la carpeta `wiki/` del vault; desde un chat sin acceso al disco, "
         "decir qué nota abrir o pedir que se abra la app de escritorio.", ""]
    for carpeta in sorted(grupos):
        L.append(f"## {carpeta}")
        for e in sorted(grupos[carpeta], key=lambda e: e["ruta"].lower()):
            L.append(f"- {e['ruta'].rsplit('/', 1)[-1]} — {e['desc'] or '(sin descripción)'}")
        L.append("")
    vault.escribir(destino, "\n".join(L))
    print(f"catálogo: {len(publicas)} notas públicas → {os.path.relpath(destino, RAIZ)}")
    return destino


# ------------------------------------------------------------------ evaluar
def evaluar(ruta=PREGUNTAS, solo_medir=False):
    if not os.path.exists(ruta):
        sys.exit(f"Falta {os.path.relpath(ruta, RAIZ)}: lista de {{\"pregunta\", \"esperadas\"}}")
    with open(ruta, encoding="utf-8") as f:
        preguntas = json.load(f)
    if isinstance(preguntas, dict):
        preguntas = preguntas.get("preguntas", [])
    d, _ = sincronizar(mapas=False)
    res = {}
    for modo, tiempo in (("lexico", False), ("hongo", False), ("mixto", False), ("lexico+tiempo", True)):
        a3, rr, fallos = 0, 0.0, []
        for q in preguntas:
            esperadas = set()
            for n in q["esperadas"]:
                k, _ = resolver(n, d)
                if k:
                    esperadas.add(k)
            orden = [f[0] for f in ranking(q["pregunta"], d, modo.split("+")[0], tiempo)]
            pos = next((i for i, k in enumerate(orden) if k in esperadas), None)
            if pos is not None and pos < 3:
                a3 += 1
            else:
                fallos.append(q["pregunta"])
            rr += 1.0 / (pos + 1) if pos is not None else 0.0
        res[modo] = {"acierto_3": a3, "mrr": round(rr / len(preguntas), 3), "fallos": fallos}
    n = len(preguntas)
    base = res["lexico"]
    # regla de corte: el hongo entra solo si acierta al menos 2 preguntas más (10 % de 20) que el léxico
    candidato = max(("mixto", "hongo"), key=lambda m: (res[m]["acierto_3"], res[m]["mrr"]))
    ganador = candidato if res[candidato]["acierto_3"] >= base["acierto_3"] + max(2, round(0.1 * n)) else "lexico"
    salida = {"fecha": dt.datetime.now().isoformat(timespec="minutes"), "preguntas": n,
              "resultados": res, "ganador": ganador}
    os.makedirs(SALIDA, exist_ok=True)
    # --solo-medir (cerrar.py) escribe aparte: medir no debe cambiar el modo por omisión
    destino = os.path.join(SALIDA, "evaluacion-ultima.json") if solo_medir else EVALUACION
    with open(destino, "w", encoding="utf-8", newline="\n") as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)
        f.write("\n")
    for m, r in res.items():
        print(f"{m:7s} aciertos en top 3: {r['acierto_3']}/{n} · MRR {r['mrr']:.2f}")
    if solo_medir:
        print(f"Solo medición. Modo que ganaría: {ganador} · modo actual: {modo_por_omision()}")
    else:
        print(f"Modo por omisión de `buscar`: {ganador}")
    return salida


# ------------------------------------------------------------------ main
def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("buscar"); b.add_argument("palabras", nargs="+"); b.add_argument("-n", type=int, default=5)
    b.add_argument("--modo", choices=["lexico", "hongo", "mixto"])
    u = sub.add_parser("usar"); u.add_argument("notas", nargs="+"); u.add_argument("--consulta", default="")
    r = sub.add_parser("resolver"); r.add_argument("nota")
    i = sub.add_parser("indexar"); i.add_argument("--hook", action="store_true")
    sub.add_parser("pendientes")
    cp = sub.add_parser("comparar"); cp.add_argument("textos", nargs="*"); cp.add_argument("--plan")
    e = sub.add_parser("evaluar"); e.add_argument("archivo", nargs="?", default=PREGUNTAS)
    e.add_argument("--solo-medir", action="store_true", help="no cambia el modo por omisión")
    c = sub.add_parser("catalogo"); c.add_argument("--salida")
    a = ap.parse_args()
    if a.cmd == "buscar":
        buscar(" ".join(a.palabras), a.n, a.modo)
    elif a.cmd == "usar":
        usar(a.notas, a.consulta)
    elif a.cmd == "resolver":
        k, e = resolver(a.nota)
        print(f"{e['ruta']} (id {k})" if e else "No está en el índice.")
    elif a.cmd == "indexar":
        d, c = sincronizar(asignar_ids=not a.hook)
        if not a.hook:
            print(f"{len(d['notas'])} notas · " + " · ".join(f"{k}: {len(v)}" for k, v in c.items()))
            for m in c["movidas"]:
                print("  movida:", m)
            pendientes(d)
    elif a.cmd == "pendientes":
        pendientes()
    elif a.cmd == "comparar":
        if not a.textos and not a.plan:
            ap.error("comparar necesita --plan <archivo> o un texto")
        comparar(a.textos, a.plan)
    elif a.cmd == "evaluar":
        evaluar(a.archivo, a.solo_medir)
    elif a.cmd == "catalogo":
        catalogo(a.salida)


if __name__ == "__main__":
    main()
