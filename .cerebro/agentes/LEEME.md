# Agentes de la actualización

Tres subagentes de Claude Code para las actualizaciones grandes del vault. Cada uno trabaja con su propio contexto: la sesión principal no carga chats completos ni notas enteras, solo archivos cortos.

| Agente | Pasos de la actualización | Modelo | Escribe |
|---|---|---|---|
| `fuentes` | lectura: chats, archivos, `.raw/` | sonnet | solo `.raw/novedades.md` |
| `ubicador` | ubicar y escribir: hipocampo, `plan.json`, `comparar`, `--dry` | sonnet | solo `.raw/plan.json` |
| `revisor` | antes de aplicar: revisa el plan sin haberlo armado | haiku | nada |

La sesión principal hace el corte, aplica el plan y cierra con `cerrar.py`. Las reglas de cuándo delegar están en `CLAUDE.md` («Agentes de la actualización»).

## Cuándo no usarlos

Un sistema con varios agentes gasta varias veces los tokens de una sola sesión (Anthropic midió ~15× contra un chat en su sistema de investigación). Ahorran cuando hay mucho que leer; con pocas novedades cuestan más de lo que ahorran. Por eso: **4 fuentes nuevas o menos → sin agentes**.

## Instalar o actualizar

Esta carpeta es la copia versionada. Claude no escribe en `.claude/` (está protegida), así que la copia activa la pones tú, desde la raíz del vault en PowerShell:

```powershell
New-Item -ItemType Directory .claude\agents -Force | Out-Null
Copy-Item .cerebro\agentes\fuentes.md, .cerebro\agentes\ubicador.md, .cerebro\agentes\revisor.md .claude\agents\ -Force
```

Comprueba con `claude` → `/agents` que aparecen los tres. Repite la copia cada vez que cambie un archivo de esta carpeta.

## Ajustes

- `fuentes` no tiene línea `tools` a propósito: así hereda las herramientas MCP de la sesión (navegador, conectores). Si le pones una, incluye esas herramientas por nombre.
- Para gastar menos, `fuentes` puede ir en `haiku`; si empieza a mezclar lo que dijo Claude con lo que dijiste tú, regrésalo a `sonnet`.

## Medido antes de construir (en el vault original, oct 2026)

- **Detector de novedad con el cuerpo hongo: descartado.** Un párrafo de una nota se parece a su propia nota con mediana 0.19, y la mejor nota distinta 0.17: no hay umbral que separe lo conocido de lo nuevo.
- **`comparar` con dos niveles.** El umbral de duplicado (0.80) solo atrapa copias; el parecido máximo real entre notas es 0.60. Se agregó `pariente` desde 0.35, arriba del 99.9 % de las parejas actuales.
