---
type: meta
title: "Cómo medir un cambio"
id: n5bbf3b13
description: "Lecciones: regla de corte, conjuntos de preguntas, evaluar con control y cómo registrar una mejora descartada"
created: 2026-11-20
updated: 2026-11-20
tags: ["meta", "claude", "leccion", "medicion"]
status: evergreen
related: ["[[Claude - método]]"]
---

# Cómo medir un cambio

**Regla de corte**: una mejora entra solo si mejora la medición y no baja el control.

1. Escribe preguntas **tú** (no Claude: las suyas usan sus mismas palabras y salen sesgadas) en `.cerebro/preguntas.json`: pregunta + nota esperada.
2. `python .cerebro/hipocampo.py evaluar --solo-medir` da aciertos en el top 3 y MRR por modo (léxico, hongo, mixto, léxico+tiempo).
3. Prueba el cambio en una copia del vault y repite con `preguntas.json` y `preguntas-control.json`.
4. Agrega también preguntas **sin respuesta** (`"esperadas": []`), mejor si comparten una palabra con una nota ajena: `evaluar` cuenta cuántas reciben candidatas. Si ninguna candidata nombra el tema, Claude debe decir que no está.
5. Entra si gana por 2 o más sin bajar el control. Si no, se anota en «Descartado» del [[Registro de decisiones]] con la cifra.
