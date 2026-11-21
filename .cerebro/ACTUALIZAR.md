# Actualización del vault — procedimiento completo

Para cuando la skill `actualizar-vault` no está disponible. Correr todo desde la raíz del vault. La palabra clave está en `CLAUDE.md`.

1. **Arranque**: mostrar fecha y hora. `python .cerebro/vault.py estado` da la fecha de la última actualización (el corte) y los chats ya integrados: leer solo lo posterior y saltar esos IDs. Leer `wiki/hot.md` y `wiki/meta/claude/Claude - método.md`. Si viene con alcance («solo chats», «solo archivos»), limitarse a eso. Si nadie está mirando (tarea programada), no preguntar: tomar la lectura más razonable y decirla en el reporte.
2. **Chats**: el export más reciente de claude.ai (u otro asistente) en `.raw/export-*/`. Solo lo posterior al corte. Si hay una skill o un navegador para leer chats, se puede usar; si falla, reintentar una vez y anotarlo.
3. **Archivos** de las carpetas de la sección «Fuentes» de `CLAUDE.md`, modificados desde el corte. PDFs con `pypdf`; Word, PowerPoint y Excel con `uvx --from "markitdown[docx,pptx,xlsx]" markitdown "<archivo>"`.
4. **Paquetes pendientes** en `.raw/` (`ingest-*.md`).
5. **Ubicar**: para cada novedad, `python .cerebro/hipocampo.py buscar <palabras>` dice a qué nota va. Abrir la candidata desde `l.N` con ~5–15 líneas. Contexto con `ruta.py "Nota"`. Si una nota resolvió la búsqueda: `hipocampo.py usar "Nota" --consulta "<palabras>"`.
6. **Escribir** con un plan de `vault.py aplicar` (notas, `log`, `hot`); `--dry` primero y `hipocampo.py comparar --plan` antes de aplicar. Reglas:
   - Toda nota nueva lleva `description` con las palabras con que se buscaría y máximo 3 conceptos en `related`. El `id` lo pone `vault.py`.
   - Ampliar antes que crear. Nunca borrar ni fusionar notas solo.
   - Lo que propuso Claude no es una decisión del usuario.
   - Si una novedad reemplaza un dato, el viejo va a `## Historial` al final de la nota (olvido activo).
   - Si un pendiente depende de un tema, va como `pendiente` + `cuando` en su nota, no en `hot.md`.
   - Cada fuente lleva su nota en `wiki/sources/` con el enlace al original.
   - Las notas con `privado: true` no se citan ni se resumen en otras.
7. **Cerrar**: `python .cerebro/cerrar.py --corte <fecha y hora> --chats <ids> --nota "<nota fuente>" -m "actualizacion: <resumen>"`. Rota `hot.md`, indexa, regenera el índice, verifica (se detiene si hay errores), corre conectoma y physarum, mapas, catálogo, puntería del buscador, estado, commit y push.
   - **Resúmenes viejos** o **sin description**: reescribirlos con un plan (op `meta`) y correr `cerrar.py --sin-red`.
   - **Posibles duplicados**: reportarlos; nunca fusionar solo.
   - Si dice **«NO está respaldado»**, el push falló: decirlo primero.
   - Si el commit falla por **gitleaks** (posible secreto), no saltarlo con `--no-verify`: quitar el dato o, si es falso positivo, agregar su `Fingerprint` a `.gitleaksignore`.
8. **Reporte**: qué entró, los pendientes, un renglón del Physarum, la puntería y **qué no se pudo leer**. Además:
   - **Pendientes con señal** (`hipocampo.py pendientes`, última sección) y si alguno ya se cumplió.
   - **Lecciones que estorban**: `python .cerebro/lecciones.py listar --alertas`.
   - **Preguntas abiertas** de `wiki/meta/claude/Claude - quién sabe qué.md`.
   - **Dos preguntas de prueba** sobre el propio vault («¿qué decidiste sobre X?», «¿dónde quedó Y?») para que el usuario responda de memoria. Si responde, su pregunta y la nota correcta van a `.cerebro/preguntas.json` (preguntas suyas, sin el sesgo de las de Claude). Si dos actualizaciones seguidas no responde, dejar de hacerlas y anotarlo.
