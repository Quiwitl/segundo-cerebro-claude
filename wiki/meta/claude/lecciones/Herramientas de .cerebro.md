---
type: meta
title: "Herramientas de .cerebro"
id: nab047c26
description: "Lecciones: qué herramienta de .cerebro usar en cada caso (buscar, usar, ruta, aplicar, comparar, cerrar, pruebas, evaluar)"
created: 2026-11-20
updated: 2026-11-20
tags: ["meta", "claude", "leccion", "herramientas"]
status: evergreen
related: ["[[Claude - método]]", "[[Cómo funciona el cerebro del vault]]"]
---

# Herramientas de .cerebro

| Para | Usar | En lugar de |
|---|---|---|
| Encontrar una nota | `hipocampo.py buscar <palabras>` | Grep o abrir el índice completo |
| Enseñarle al buscador | `hipocampo.py usar "Nota" --consulta "<palabras>"` cuando una nota sirvió | Nada: sin esto no aprende |
| Contexto alrededor | `ruta.py "Nota"` (o `ruta.py "A" "B"`) | Abrir el vecindario completo |
| Escribir | `vault.py aplicar plan.json` (`--dry` primero) | Editar a mano muchas notas |
| Evitar duplicados | `hipocampo.py comparar --plan plan.json` | Crear y luego fusionar |
| Mantenimiento | `hipocampo.py pendientes` (resúmenes viejos, sin description, duplicados y pendientes con señal) | Recorrer el vault |
| Un pendiente que depende de un tema | `pendiente` + `cuando: [palabras]` en el frontmatter; `buscar` lo avisa con ⏰ | Dejarlo en `hot.md` |
| Registrar que una lección ayudó o estorbó | `lecciones.py marcar E01 +` (o `-`) | Reescribir la nota de lecciones |
| Cerrar | `cerrar.py` | Correr cada paso a mano |
| Cambiar un script | `pruebas.py` antes y después | Probar en el vault real |
