# Vault de {{NOMBRE}} — instrucciones para Claude

Segundo cerebro en Obsidian que Claude mantiene con {{NOMBRE}}. Las notas son de {{NOMBRE}}; Claude las ubica, las enlaza y las busca gastando pocos tokens. Las escribe con Python (`.cerebro/vault.py`), nunca con PowerShell en línea.

## Estructura

- `.raw/` — fuentes inmutables (exports de chats, PDFs, paquetes `ingest-*.md`). No se editan.
- `wiki/areas/` — áreas activas y proyectos.
- `wiki/concepts/` — una idea por nota.
- `wiki/learning/` — lo aprendido por materia o tema.
- `wiki/sources/` — una nota por fuente ingerida, con enlace al original.
- `wiki/meta/` — entorno, método y notas sobre el propio vault. Incluye `wiki/meta/claude/`: la bóveda de método de Claude.
- `wiki/index.md` (catálogo), `wiki/log.md` (operaciones, la más reciente arriba, nunca se editan entradas pasadas), `wiki/hot.md` (contexto reciente, unas 500 palabras, se lee al empezar), `wiki/overview.md`.
- Cada carpeta de `wiki/` tiene un `_index.md`; los genera `vault.py indice` (no editarlos a mano).
- `wiki/hipocampo/` — un mapa por región, generado por `hipocampo.py`. No son notas: no se editan.
- `.cerebro/` — herramientas del vault (detalle en `.cerebro/LEEME.md`): `vault.py` (escribir en lote, índices, verificar, registro de actualizaciones), `hipocampo.py` (buscar gastando poco), `ruta.py`, `conectoma.py`, `physarum.py`, `lecciones.py`, `cerrar.py` (cierre de la actualización), `pruebas.py` (correr antes de cambiar cualquier herramienta) y `pasado.py`. **Nunca se editan a mano**: `hipocampo.json`, `uso.jsonl` (solo con `hipocampo.py usar`), `wiki/hipocampo/`.

## Fuentes

Lo que lee la actualización, además de `.raw/`:

{{FUENTES}}

## Convenciones

- Notas en español. Frontmatter: `type`, `title`, `id` (estable; lo pone `vault.py` o `hipocampo.py indexar`, nunca se cambia a mano), **`description`** (una línea: qué contiene y para qué leerla; es lo que lee el hipocampo, así que debe nombrar los temas con las palabras con que se buscarían), `created`, `updated`, `tags`, `status` (seed/developing/evergreen/complete/archived), `related`; opcional `privado: true`, `aliases`, `pendiente` y `cuando`.
- **Lo importante arriba**: el primer párrafo después del frontmatter debe bastar para saber si la nota sirve.
- Enlaces con `[[Nombre de nota]]`. Un enlace a una nota que todavía no existe está bien: marca algo por escribir.
- Lo que dijo {{NOMBRE}} se registra como suyo; una sugerencia de Claude no es una decisión de {{NOMBRE}}.
- **Buscar gastando poco (hipocampo → corteza)**:
  1. `python .cerebro/hipocampo.py buscar <palabras>` antes que Grep: devuelve ~1 línea por candidata (ruta | l.N | description | citas | región). `l.N` es la línea donde empieza el cuerpo.
  Si ninguna candidata nombra el tema de la consulta, lo más probable es que **no esté en el vault**: decirlo en vez de forzar la más parecida.
  2. Abrir la candidata desde `l.N` con límite de ~5 líneas; leer el resto solo si hace falta.
  3. Contexto alrededor: `python .cerebro/ruta.py "Nota"`; para unir dos temas, `ruta.py "A" "B"`. Parar en cuanto alcance.
  4. Si una nota resolvió la búsqueda: `python .cerebro/hipocampo.py usar "Nota" --consulta "<palabras>"`. Alimenta al Physarum y enseña esas palabras al hipocampo, **sobre todo cuando `buscar` falló** y la nota salió por otro camino.
- **Enlaces dispersos**: una nota nueva enlaza en `related` a **máximo 3** conceptos, los más específicos.
- **Notas privadas** (`privado: true`): no se citan ni se resumen fuera del vault y no salen en el catálogo.
- **Decisiones**: lo que {{NOMBRE}} decide va a `wiki/areas/Registro de decisiones.md` (una línea, con fecha y fuente). Revisarlo antes de proponer algo: no reabrir lo descartado sin que lo pida.
- **Olvido activo**: cuando un dato nuevo reemplaza a otro, el viejo se mueve en el mismo paso a `## Historial` al final de la nota («era X hasta <fecha>, según <fuente>»). Arriba queda solo lo vigente: un dato viejo en el mismo contexto empuja a usarlo.
- **Pendientes con señal**: un pendiente que depende de un tema y no de una fecha va en el frontmatter de su nota: `pendiente: "…"` y `cuando: [palabras]`. `hipocampo.py buscar` lo avisa con ⏰ y `pendientes` los lista. Al cumplirse, quitar los dos campos. Los pendientes con fecha van en `hot.md`.
- **Escribir con `python .cerebro/vault.py aplicar plan.json`**: operaciones `nueva`, `anexar`, `insertar_tras`, `reemplazar`, `meta` y `log`; todo o nada, `--dry` para simular. Notas nuevas desde Obsidian: plantilla `_templates/Nota.md`. Para lo demás, Python con `encoding='utf-8', newline='\n'`.

## Respaldo (obligatorio)

El vault es un repo git. Para que esté respaldado necesita un remoto **privado** (nunca público: es tu información). Al terminar cualquier escritura de Claude: `python .cerebro/cerrar.py`, que hace commit y push y avisa si el push falló. Si no hay remoto, decirlo: un vault sin push no está respaldado.

## Clave «{{CLAVE}}» (actualización completa)

Cuando {{NOMBRE}} escriba **{{CLAVE}}** como orden (sola o con alcance, p. ej. "{{CLAVE}}, solo archivos"), hacer la actualización completa sin preguntar cómo. Seguir la skill `actualizar-vault`; si no está disponible, el procedimiento está en `.cerebro/ACTUALIZAR.md`. El cierre es un solo comando: `python .cerebro/cerrar.py`.

## Agentes de la actualización

Definidos en `.cerebro/agentes/` (copia activa en `.claude/agents/`; ver `.cerebro/agentes/LEEME.md`). Si están instalados:
- La sesión principal hace el corte (`vault.py estado`) y cuenta las fuentes nuevas. **Con 4 o menos, todo sin agentes**: delegar cuesta más tokens de los que ahorra.
- Con 5 o más: `fuentes` (escribe `.raw/novedades.md`) → `ubicador` (escribe `.raw/plan.json` y lo prueba con `--dry`) → `revisor` (APROBADO o CORREGIR; máximo dos vueltas) → la sesión principal aplica con `vault.py aplicar .raw/plan.json` y cierra con `cerrar.py`.
- Con o sin agentes, antes de aplicar un plan: `python .cerebro/hipocampo.py comparar --plan <plan>`. `duplicado` → anexar a la existente sin pasar por el revisor (encaja en lo que ya hay); `pariente` → revisar si es el mismo tema; sin parecido → ruta completa.

## Bóveda de Claude (aprendizaje de método)

Antes de trabajar en este vault, leer `wiki/meta/claude/Claude - método.md` (lo esencial + índice de lecciones; el log está en `Claude - log de método.md` y se lee solo si hace falta). Al terminar, registrar lo aprendido en la lección y una línea en el log (síntoma → causa → qué hacer; después de una falla, decir si la decisión era mala o fue mala suerte) y marcar con `python .cerebro/lecciones.py marcar <id> +|-` las líneas de lo esencial o de las correcciones que ayudaron o estorbaron. Lo que solo sabe {{NOMBRE}} va como pregunta a `Claude - quién sabe qué.md`.
