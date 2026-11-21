---
type: meta
title: "Claude - método"
id: n1dca40bb
description: "Bóveda de método de Claude, nota de arranque: lo esencial con contadores de ayuda y estorbo y el índice de lecciones"
created: 2026-11-20
updated: 2026-11-20
tags: ["meta", "claude", "metodo"]
status: evergreen
related: ["[[Cómo funciona el cerebro del vault]]"]
---

# Claude – método de trabajo

Lecciones de método de Claude para mantener este vault: qué funcionó, qué falló y cómo evitarlo. No guarda nada personal.

## Uso

- **Al empezar** cualquier trabajo sobre el vault, leer esta nota y, si el tema es específico, la lección que toca.
- **Al terminar**, si salió algo nuevo, registrarlo en la lección correspondiente o crear una en `lecciones/` (síntoma → causa → qué hacer, con fecha) y agregar una línea a [[Claude - log de método]].
- **Antes de escribir una lección después de una falla**: ¿la decisión era mala con lo que se sabía antes, o fue una falla pasajera? Si fue pasajera, la lección lo dice y no recomienda cambiar de herramienta; «sin cambio» es una respuesta válida.
- **Contadores**: cada línea de «Lo esencial» y de [[Correcciones recurrentes]] lleva un id y dos contadores (ayudó / estorbó). Al cerrar: `python .cerebro/lecciones.py marcar <id> +` o `-`. Nunca se reescribe la nota entera: se agregan o ajustan líneas.
- **Lo que no sé o solo sabe el usuario**: [[Claude - quién sabe qué]].

## Lo esencial

1. **Acentos**: escribir archivos con Python `utf-8`. En Windows, PowerShell en línea los corrompe. → [[Escritura en Windows]] %%E01 +0 -0%%
2. **Respaldo**: un commit local no es un respaldo; el vault necesita un remoto **privado** y push al cerrar (`cerrar.py` avisa si falló). %%E02 +0 -0%%
3. **Herramientas fijas** (`.cerebro/`): buscar con `hipocampo.py buscar` (y `usar` si sirvió), escribir con `vault.py aplicar plan.json`, cerrar con `cerrar.py`. Antes y después de cambiar un script: `pruebas.py`. → [[Herramientas de .cerebro]] %%E03 +0 -0%%
4. **Medir antes de activar**: una mejora entra solo si mejora `evaluar` o los tokens por actualización, probada en una copia y sin bajar el control. → [[Cómo medir un cambio]] %%E04 +0 -0%%
5. **Lo que dijo el usuario es suyo**: una sugerencia de Claude no es una decisión hasta que la acepta ([[Registro de decisiones]]). %%E05 +0 -0%%
6. **Antes de entregar**, repasar [[Correcciones recurrentes]]. %%E06 +0 -0%%

## Lecciones

[[Escritura en Windows]] · [[Herramientas de .cerebro]] · [[Cómo medir un cambio]] · [[Correcciones recurrentes]]

## Log

El log está en [[Claude - log de método]], la entrada más reciente arriba.
