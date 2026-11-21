---
name: actualizar-vault
description: "Actualización completa del vault de Obsidian de esta carpeta. Úsala SIEMPRE que el mensaje sea solo la palabra clave del usuario (está en CLAUDE.md, sección «Clave») o empiece con ella como orden, aunque no diga «vault» ni «actualiza», y también cuando pida «actualiza el vault» o «integra mis chats/archivos al vault». Integra exports de chats, archivos de las carpetas de fuentes y paquetes en .raw/, y cierra con commit y push."
---

# Actualizar el vault

La palabra clave y el nombre del usuario están en `CLAUDE.md`. No preguntes qué significa la clave: empieza.

Sigue `.cerebro/ACTUALIZAR.md` paso a paso, desde la raíz del vault. Lo esencial:

1. Fecha y hora; `python .cerebro/vault.py estado` para el corte; leer `wiki/hot.md` y `wiki/meta/claude/Claude - método.md`.
2. Leer solo lo nuevo: exports en `.raw/export-*/`, carpetas de «Fuentes» de `CLAUDE.md` y `ingest-*.md`.
3. Ubicar cada novedad con `python .cerebro/hipocampo.py buscar <palabras>`; registrar con `usar` lo que sirvió.
4. Escribir con un plan JSON: `hipocampo.py comparar --plan`, `vault.py aplicar --dry` y luego `vault.py aplicar`.
5. Cerrar con `python .cerebro/cerrar.py --corte <fecha> -m "actualizacion: <resumen>"` y leer su reporte.
6. Reportar en prosa breve: qué entró, pendientes, Physarum, puntería, preguntas abiertas, dos preguntas de prueba y **qué no se pudo leer**.

Con 5 fuentes nuevas o más, y si los agentes están en `.claude/agents/`, delega como dice `CLAUDE.md` («Agentes de la actualización»).
