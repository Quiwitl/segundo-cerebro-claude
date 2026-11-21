# .cerebro — las herramientas del vault

Scripts de Python para que Claude mantenga el vault gastando pocos tokens. Casi todos usan solo la biblioteca estándar; `conectoma.py`, `physarum.py` y `espacio.py` necesitan `networkx`, `numpy`, `matplotlib` y `scipy` (con `uv` instalado, `cerrar.py` las trae solo). Todo se corre desde la raíz del vault.

**Antes y después de cambiar cualquier script: `python .cerebro/pruebas.py`** (con `--red` también prueba la red). Trabaja sobre una copia temporal, nunca sobre tus notas.

## Para cada tarea

| Tarea | Comando |
|---|---|
| Buscar una nota | `python .cerebro/hipocampo.py buscar <palabras>` |
| Decir que una nota sirvió (y enseñar esas palabras) | `python .cerebro/hipocampo.py usar "Nota" --consulta "<palabras>"` |
| Contexto alrededor de una nota | `python .cerebro/ruta.py "Nota"` · entre dos: `ruta.py "A" "B"` · puntos de entrada: `ruta.py --hubs` |
| Escribir varias notas a la vez | `python .cerebro/vault.py aplicar plan.json` (`--dry` para simular) |
| Revisar duplicados antes de escribir | `python .cerebro/hipocampo.py comparar --plan plan.json` |
| Mantenimiento | `python .cerebro/hipocampo.py pendientes` |
| Marcar una lección de Claude | `python .cerebro/lecciones.py marcar E01 +` (o `-`) · `listar --alertas` |
| Medir el buscador | `python .cerebro/hipocampo.py evaluar --solo-medir` (las preguntas con `"esperadas": []` no tienen respuesta: se cuenta cuántas reciben candidatas) |
| Cerrar una actualización | `python .cerebro/cerrar.py --corte <fecha> -m "actualizacion: …"` |
| Hablar con tu yo del pasado | `python .cerebro/pasado.py AAAA-MM-DD` |

## Los scripts

- **`vault.py`**: escribe con planes JSON (todo o nada; operaciones `nueva`, `anexar`, `insertar_tras`, `reemplazar`, `meta`, `log`), regenera `index.md` y los `_index.md`, verifica enlaces y acentos, y guarda el registro de actualizaciones (`estado`).
- **`hipocampo.py`**: el índice. Una entrada por nota con id estable, `description`, alias, etiquetas y una huella del cuerpo hongo (FlyHash). Se verifica contra los archivos en cada consulta, así que nunca devuelve una ruta que no existe. Modos de búsqueda: léxico (con el vocabulario aprendido de `usar`), hongo (parecido sin palabras exactas) y mixto; `evaluar` decide cuál usar por omisión con tus preguntas. También avisa los **pendientes con señal** (`pendiente` + `cuando` en el frontmatter) con ⏰.
- **`conectoma.py`**: analiza el vault como red (hubs, puentes, regiones, mundo pequeño) y escribe `wiki/meta/Mapa del cerebro.md`.
- **`physarum.py`**: simula el moho *Physarum polycephalum* sobre los enlaces (Tero et al., 2010). Las búsquedas reales de `uso.jsonl` lo alimentan: los caminos usados engordan. No cambia enlaces; escribe un informe.
- **`ruta.py`**: rutas de lectura sobre el esqueleto del Physarum.
- **`espacio.py`**: coloca las notas en 3D minimizando el cableado (como un cerebro real); datos para vistas propias.
- **`lecciones.py`**: contadores de ayuda y estorbo en las lecciones de Claude (idea de ACE, ICLR 2026: cambios por línea, nunca reescribir la nota entera).
- **`cerrar.py`**: el cierre en un solo comando: rota `hot.md`, indexa, índice, verifica (se detiene si hay errores), red, mapas, catálogo, puntería, estado, commit y push. Avisa si el push falló.
- **`pruebas.py`**: 18 pruebas sobre una copia temporal.
- **`medir_tokens.py`**: cuánto lee Claude para encontrar cada nota, con y sin hipocampo.
- **`pasado.py`**: arma una cápsula con lo que sabías hasta una fecha (chats del export + notas en git) para conversar con tu yo de entonces.
- **`personalizar.py`**: llena `CLAUDE.md` con tu nombre, clave y carpetas (lo usa el instalador).
- **`hooks/pre-commit`**: gitleaks bloquea secretos antes de cada commit y el hipocampo se regenera.
- **`agentes/`**: tres subagentes de Claude Code para actualizaciones grandes (ver su `LEEME.md`).

## Generados (no se editan a mano)

`hipocampo.json`, `uso.jsonl`, `wiki/hipocampo/`, `salida/` y las notas `Mapa del cerebro` y `Physarum del vault`.

## Regla de corte

Una idea entra solo si mejora la medición (`evaluar` con tus preguntas, o los tokens por actualización) sin bajar el control (`preguntas-control.json`). Lo que no pasa se anota en «Descartado» del Registro de decisiones con su cifra. Así se probaron estas piezas en el vault original: el detector de novedad con el cuerpo hongo y el eje del tiempo se midieron y quedaron fuera.
