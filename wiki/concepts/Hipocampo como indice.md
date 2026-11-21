---
type: concept
title: "Hipocampo como indice"
id: n11a7c3b5
description: "Teoría del índice hipocampal: el hipocampo guarda punteros a la corteza, no el contenido; base del buscador del vault"
created: 2026-11-20
updated: 2026-11-20
tags: ["concepto", "neurociencia", "memoria"]
status: evergreen
related: ["[[Zettelkasten]]", "[[Cuerpo hongo de la mosca]]"]
---

# Hipocampo como índice

La teoría del índice hipocampal (Teyler y DiScenna, 1986) propone que el hipocampo no guarda los recuerdos completos, sino un **índice** que apunta a dónde están en la corteza. Recordar es activar el índice y que este reactive el patrón completo.

En el vault, `hipocampo.py` hace eso: guarda una línea por nota (título, alias, etiquetas, `description`, vocabulario aprendido) y devuelve candidatas en ~1 línea cada una. Claude abre solo la nota que sirve. Ver [[Cómo funciona el cerebro del vault]].
