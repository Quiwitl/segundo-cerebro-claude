---
type: meta
title: "Cómo funciona el cerebro del vault"
id: n6a872188
description: "Cómo funcionan las herramientas de .cerebro: hipocampo para buscar, Physarum y conectoma para la red, actualización y cierre"
created: 2026-11-20
updated: 2026-11-20
tags: ["meta", "herramientas", "hub"]
status: evergreen
related: ["[[Hipocampo como indice]]", "[[Physarum polycephalum]]", "[[Bienvenida]]"]
---

# Cómo funciona el cerebro del vault

Tres ideas de neurociencia, cada una medida antes de activarse (regla de corte: entra solo si mejora la puntería del buscador o baja los tokens):

| Pieza | Inspiración | Herramienta | Qué hace |
|---|---|---|---|
| Índice | [[Hipocampo como indice]] | `hipocampo.py buscar` | Una línea por candidata; Claude abre solo la que sirve |
| Parecido | [[Cuerpo hongo de la mosca]] | `hipocampo.py comparar` | Avisa duplicados antes de escribir |
| Caminos | [[Physarum polycephalum]] | `physarum.py`, `ruta.py` | Los enlaces que se usan engordan |
| Mapa | Conectomas | `conectoma.py` | Hubs, puentes y regiones del vault |

El ciclo de trabajo: **buscar** (hipocampo) → **leer** poco (`ruta.py` para el contexto) → **escribir** con un plan (`vault.py aplicar`) → **cerrar** (`cerrar.py`: indexa, verifica, red, catálogo, commit y push). Detalle en `.cerebro/LEEME.md`.
