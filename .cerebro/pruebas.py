# -*- coding: utf-8 -*-
"""pruebas.py: comprueba las herramientas de .cerebro sobre una COPIA temporal del vault.

Correr antes de cambiar cualquier script (y después, para ver que nada se rompió). No toca
el vault real: copia wiki/ y .cerebro/ a una carpeta temporal y prueba ahí.

    python .cerebro/pruebas.py            pruebas rápidas (solo biblioteca estándar, segundos)
    python .cerebro/pruebas.py --red      además conectoma.py, physarum.py y ruta.py (necesitan networkx)

Sale con código 1 si alguna falla.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
RESULTADOS = []


def preparar():
    tmp = tempfile.mkdtemp(prefix="vault-prueba-")
    shutil.copytree(os.path.join(RAIZ, "wiki"), os.path.join(tmp, "wiki"))
    shutil.copytree(AQUI, os.path.join(tmp, ".cerebro"),
                    ignore=shutil.ignore_patterns("__pycache__", ".cache-hipocampo.json", "uso.jsonl"))
    return tmp


def cli(tmp, *args, ok=True):
    r = subprocess.run([sys.executable, *args], cwd=tmp, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if ok and r.returncode != 0:
        raise AssertionError(f"{' '.join(args)} salió con {r.returncode}: {(r.stdout + r.stderr)[-600:]}")
    return r.stdout + r.stderr


def leer(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def escribir(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


def prueba(nombre):
    def deco(f):
        def correr(tmp):
            try:
                f(tmp)
                RESULTADOS.append((True, nombre, ""))
            except Exception as exc:  # se reporta y se sigue con las demás
                RESULTADOS.append((False, nombre, str(exc)[:400]))
        correr.nombre = nombre
        return correr
    return deco


def plan(tmp, ops, *extra, ok=True):
    p = os.path.join(tmp, "plan-prueba.json")
    escribir(p, json.dumps(ops, ensure_ascii=False))
    return cli(tmp, ".cerebro/vault.py", "aplicar", p, *extra, ok=ok)


NOTA = {"op": "nueva", "ruta": "concepts/Zz prueba quimera", "meta": {"description": "Nota de prueba sobre quimeras xilofónicas"},
        "cuerpo": "# Zz prueba quimera\n\nTexto corto de prueba."}


@prueba("verificar el vault copiado: 0 errores")
def t_verificar(tmp):
    out = cli(tmp, ".cerebro/vault.py", "verificar", ok=False)
    assert " 0 errores" in out, out[-400:]


@prueba("aplicar --dry no escribe nada")
def t_dry(tmp):
    plan(tmp, [NOTA], "--dry")
    assert not os.path.exists(os.path.join(tmp, "wiki", "concepts", "Zz prueba quimera.md"))


@prueba("aplicar es todo o nada (una op mala cancela todo)")
def t_todo_o_nada(tmp):
    malo = {"op": "reemplazar", "ruta": "concepts/Zz no existe", "viejo": "x", "nuevo": "y"}
    plan(tmp, [NOTA, malo], ok=False)
    assert not os.path.exists(os.path.join(tmp, "wiki", "concepts", "Zz prueba quimera.md"))
    assert not any(f.endswith(".tmp-vault") for _, _, fs in os.walk(tmp) for f in fs), "quedaron temporales"


@prueba("aplicar crea la nota con id y description")
def t_nueva(tmp):
    plan(tmp, [NOTA])
    s = leer(os.path.join(tmp, "wiki", "concepts", "Zz prueba quimera.md"))
    assert "\nid: n" in s and "description:" in s, s[:300]


@prueba("buscar encuentra la nota nueva (siempre al día, sin indexar antes)")
def t_buscar(tmp):
    out = cli(tmp, ".cerebro/hipocampo.py", "buscar", "quimeras", "xilofonicas")
    assert out.splitlines() and "Zz prueba quimera" in "\n".join(out.splitlines()[:3]), out


@prueba("renombrar: resolver sigue la nota por id")
def t_renombrar(tmp):
    a = os.path.join(tmp, "wiki", "concepts", "Zz prueba quimera.md")
    b = os.path.join(tmp, "wiki", "learning", "Zz quimera movida.md")
    os.replace(a, b)
    out = cli(tmp, ".cerebro/hipocampo.py", "resolver", "Zz prueba quimera")
    assert "learning/Zz quimera movida" in out, out


@prueba("borrar: buscar ya no la devuelve")
def t_borrar(tmp):
    os.remove(os.path.join(tmp, "wiki", "learning", "Zz quimera movida.md"))
    out = cli(tmp, ".cerebro/hipocampo.py", "buscar", "quimeras", "xilofonicas")
    assert "Zz quimera movida |" not in out, out


@prueba("duplicar en Obsidian: la copia recibe id nuevo y sale como posible duplicado")
def t_duplicado(tmp):
    plan(tmp, [dict(NOTA, ruta="concepts/Zz original")])
    a = os.path.join(tmp, "wiki", "concepts", "Zz original.md")
    b = os.path.join(tmp, "wiki", "concepts", "Zz original 1.md")
    shutil.copy(a, b)
    out = cli(tmp, ".cerebro/hipocampo.py", "indexar")
    ida = [l for l in leer(a).split("\n") if l.startswith("id:")]
    idb = [l for l in leer(b).split("\n") if l.startswith("id:")]
    assert ida and idb and ida != idb, (ida, idb)
    assert "Zz original 1" in out and "≈" in out, out[-500:]


@prueba("resumen viejo: si el cuerpo cambia mucho, pendientes lo marca")
def t_viejo(tmp):
    p = os.path.join(tmp, "wiki", "concepts", "Zz original.md")
    extra = ("\n\n## Tema nuevo\n\n" + "La transformada de Laplace convierte ecuaciones diferenciales en algebraicas "
             "con tablas, fracciones parciales, convolución, funciones escalón y delta de Dirac. ") * 6
    escribir(p, leer(p) + extra)
    out = cli(tmp, ".cerebro/hipocampo.py", "pendientes")
    bloque = out.split("Sin description")[0]
    assert "Zz original" in bloque, out[:600]


@prueba("usar: el hipocampo aprende el vocabulario de la consulta")
def t_aprende(tmp):
    antes = cli(tmp, ".cerebro/hipocampo.py", "buscar", "ornitorrinco", "cuantico")
    assert "Zz original |" not in antes, antes
    cli(tmp, ".cerebro/hipocampo.py", "usar", "Zz original", "--consulta", "ornitorrinco cuantico")
    despues = cli(tmp, ".cerebro/hipocampo.py", "buscar", "ornitorrinco")
    assert "Zz original |" in despues, despues


@prueba("comparar: avisa duplicados antes de aplicar el plan y no escribe nada")
def t_comparar(tmp):
    generados = [os.path.join(tmp, ".cerebro", "hipocampo.json"), os.path.join(tmp, ".cerebro", "uso.jsonl")]
    cli(tmp, ".cerebro/hipocampo.py", "indexar")
    antes = [leer(p) if os.path.exists(p) else None for p in generados]
    copia = dict(NOTA, ruta="concepts/Zz original copia")
    ajena = {"op": "nueva", "ruta": "concepts/Zz receta", "meta": {"description": "Receta de mole poblano con chiles y chocolate"},
             "cuerpo": "x"}
    p = os.path.join(tmp, "plan-comparar.json")
    escribir(p, json.dumps([copia, ajena], ensure_ascii=False))
    out = cli(tmp, ".cerebro/hipocampo.py", "comparar", "--plan", p)
    assert 'nueva "Zz original copia" ~ "Zz original"' in out, out
    assert "Zz receta" not in out, out
    gemelas = [dict(ajena, ruta="concepts/Zz receta A"), dict(ajena, ruta="concepts/Zz receta B")]
    escribir(p, json.dumps(gemelas, ensure_ascii=False))
    out = cli(tmp, ".cerebro/hipocampo.py", "comparar", "--plan", p)
    assert "mismo plan" in out, out
    escribir(p, json.dumps([{"op": "log", "titulo": "x", "puntos": ["y"]}]))
    out = cli(tmp, ".cerebro/hipocampo.py", "comparar", "--plan", p)
    assert "sin parecidos" in out, out
    assert [leer(p) if os.path.exists(p) else None for p in generados] == antes, "comparar modificó un generado"
    assert not os.path.exists(os.path.join(tmp, "wiki", "concepts", "Zz original copia.md")), "comparar escribió una nota"


@prueba("catálogo para el Project: sin notas privadas")
def t_catalogo(tmp):
    # una privada propia, por si el vault no tiene ninguna
    plan(tmp, [dict(NOTA, ruta="areas/Zz privada", meta={"description": "Nota privada de prueba", "privado": True})])
    cli(tmp, ".cerebro/hipocampo.py", "catalogo")
    cat = leer(os.path.join(tmp, ".cerebro", "salida", "catalogo-project.md"))
    sys.path.insert(0, os.path.join(tmp, ".cerebro"))
    privadas = []
    for d, _, fs in os.walk(os.path.join(tmp, "wiki")):
        for f in fs:
            if f.endswith(".md") and "\nprivado: true" in leer(os.path.join(d, f)):
                privadas.append(f[:-3])
    assert privadas, "no hay notas privadas en la copia para comprobar"
    filtradas = [n for n in privadas if f"- {n} —" in cat]
    assert not filtradas, f"el catálogo trae privadas: {filtradas}"


@prueba("hook pre-commit con saltos LF; solo bloquea secretos (gitleaks)")
def t_hook(tmp):
    p = os.path.join(tmp, ".cerebro", "hooks", "pre-commit")
    with open(p, "rb") as f:
        b = f.read()
    assert b"\r\n" not in b, "el hook tiene CRLF: sh fallaría"
    assert b.rstrip().endswith(b"exit 0"), "el hook debe terminar en exit 0"
    assert b.count(b"exit 1") == 1 and b'"RuleID"' in b, "solo un secreto confirmado por gitleaks puede bloquear"
    if not shutil.which("gitleaks") or not shutil.which("git"):
        return  # sin gitleaks el hook no bloquea nada
    import random
    import string
    repo = os.path.join(tmp, "repo-hook")
    os.makedirs(os.path.join(repo, "hooks"))
    shutil.copy(p, os.path.join(repo, "hooks", "pre-commit"))

    def g(*a):
        return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True)
    g("init", "-q")
    g("config", "user.name", "prueba")
    g("config", "user.email", "prueba@local")
    g("config", "core.hooksPath", "hooks")
    falso = "".join(random.Random(1).sample(string.ascii_letters + string.digits, 36))  # sin repetir: gitleaks ignora algunas cadenas de baja entropía
    escribir(os.path.join(repo, "nota.md"), f"token: ghp_{falso}\n")
    g("add", "nota.md")
    assert g("commit", "-m", "x").returncode != 0, "el hook dejó pasar un token falso"
    escribir(os.path.join(repo, "nota.md"), "nada secreto\n")
    g("add", "nota.md")
    assert g("commit", "-m", "y").returncode == 0, "el hook bloqueó un commit limpio"


@prueba("conectoma, physarum y ruta (con --red)")
def t_red(tmp):
    if "--red" not in sys.argv:
        return
    uv = shutil.which("uv")
    pre = [uv, "run", "--no-project", "--with", "networkx", "--with", "numpy", "--with", "matplotlib", "python"] if uv else [sys.executable]
    for args in ([".cerebro/conectoma.py", tmp, "--salida", ".cerebro/salida"], [".cerebro/physarum.py", "--rondas", "300"]):
        r = subprocess.run(pre + args, cwd=tmp, capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert r.returncode == 0, (args[0], (r.stdout + r.stderr)[-500:])
    out = cli(tmp, ".cerebro/ruta.py", "--hubs")
    assert "Puntos de entrada" in out, out


@prueba("hot.md: rota «Last Updated» y no pierde lo que no está en log.md")
def t_hot(tmp):
    import importlib.util
    spec = importlib.util.spec_from_file_location("cerrar_prueba", os.path.join(tmp, ".cerebro", "cerrar.py"))
    c = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(c)
    c.RAIZ = tmp
    hot = os.path.join(tmp, "wiki", "hot.md")
    escribir(hot, "---\nupdated: 2026-01-01\n---\n\n## Last Updated\n\n"
             + "".join(f"2026-10-{d:02d} (21:46): entrada {d}.\n\n" for d in (9, 8, 7, 6, 5))
             + "1999-01-01: sin entrada en log.\n\n## Active Threads\n- hilo\n")
    escribir(os.path.join(tmp, "wiki", "log.md"),
             "# Log\n\n" + "".join(f"## [2026-10-{d:02d}] actualizacion\n\n" for d in (9, 8, 7, 6, 5)))
    c.rotar_hot()
    t = leer(hot)
    assert "entrada 9" in t and "entrada 7" in t and "entrada 6" not in t, t
    assert "1999-01-01" in t, "borró una entrada que no estaba en log.md"
    assert "## Active Threads\n- hilo" in t, "tocó otra sección"
    assert "entrada 9" in c.rotar_hot() or "nada que rotar" in c.rotar_hot()


@prueba("evaluar --solo-medir no cambia el modo de buscar")
def t_solo_medir(tmp):
    ev = os.path.join(tmp, ".cerebro", "salida", "evaluacion.json")
    antes = leer(ev) if os.path.exists(ev) else None
    out = cli(tmp, ".cerebro/hipocampo.py", "evaluar", "--solo-medir")
    assert "Solo medición" in out, out
    despues = leer(ev) if os.path.exists(ev) else None
    assert antes == despues, "evaluacion.json cambió"


@prueba("pendiente con señal: buscar lo avisa solo cuando la consulta toca su señal")
def t_pendiente(tmp):
    plan(tmp, [dict(NOTA, ruta="concepts/Zz senal", meta={"description": "Nota de prueba sobre marsupiales lunares",
                                                          "pendiente": "llamar al ornitorrinco", "cuando": ["axolote"]})])
    con = cli(tmp, ".cerebro/hipocampo.py", "buscar", "axolotes")
    assert "⏰ pendiente (Zz senal): llamar al ornitorrinco" in con, con
    sin = cli(tmp, ".cerebro/hipocampo.py", "buscar", "marsupiales", "lunares")
    assert "⏰" not in sin, sin
    assert "Pendientes con señal: " in cli(tmp, ".cerebro/hipocampo.py", "pendientes")


@prueba("lecciones: numera una vez, marca ayudas y estorbos, avisa lo que estorba")
def t_lecciones(tmp):
    cli(tmp, ".cerebro/lecciones.py", "numerar")
    assert "numeradas: 0" in cli(tmp, ".cerebro/lecciones.py", "numerar"), "numerar no es idempotente"
    assert "E01 +1 -0" in cli(tmp, ".cerebro/lecciones.py", "marcar", "E01", "+")
    cli(tmp, ".cerebro/lecciones.py", "marcar", "C01", "-")
    al = cli(tmp, ".cerebro/lecciones.py", "listar", "--alertas")
    assert "C01 +0 -1" in al and "E01" not in al, al
    m = leer(os.path.join(tmp, "wiki", "meta", "claude", "Claude - método.md"))
    assert m.count("%%E") >= 5 and "%%E01 +1 -0%%" in m, m[:800]


@prueba("evaluar: las preguntas sin respuesta no cuentan en el MRR y se reportan aparte")
def t_negativas(tmp):
    plan(tmp, [dict(NOTA, ruta="concepts/Zz ornitorrinco", meta={"description": "Ornitorrinco lunar de prueba"})])
    ruta = os.path.join(tmp, ".cerebro", "preguntas-neg.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump({"preguntas": [{"pregunta": "ornitorrinco lunar", "esperadas": ["Zz ornitorrinco"]},
                                 {"pregunta": "qxzvbn wqplmk", "esperadas": []},
                                 {"pregunta": "ornitorrinco marciano", "esperadas": []}]}, f)
    s = cli(tmp, ".cerebro/hipocampo.py", "evaluar", ruta, "--solo-medir")
    assert "lexico  aciertos en top 3: 1/1 · MRR 1.00 · sin respuesta con candidata: 1/2" in s, s


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tmp = preparar()
    try:
        for t in (t_verificar, t_dry, t_todo_o_nada, t_nueva, t_buscar, t_renombrar, t_borrar, t_duplicado,
                  t_viejo, t_aprende, t_comparar, t_catalogo, t_hook, t_hot, t_solo_medir, t_pendiente, t_lecciones, t_negativas, t_red):
            t(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for ok, nombre, err in RESULTADOS:
        print(("✓ " if ok else "✗ ") + nombre + ("" if ok else f"\n    {err}"))
    fallas = sum(1 for ok, _, _ in RESULTADOS if not ok)
    print(f"{len(RESULTADOS) - fallas}/{len(RESULTADOS)} pruebas bien")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
