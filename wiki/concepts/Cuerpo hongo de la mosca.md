---
type: concept
title: "Cuerpo hongo de la mosca"
id: n5477fc57
description: "Cuerpo hongo de Drosophila: células de Kenyon, código disperso y FlyHash para medir parecido entre textos"
created: 2026-11-20
updated: 2026-11-20
tags: ["concepto", "neurociencia", "conectoma"]
status: evergreen
related: ["[[Hipocampo como indice]]", "[[Physarum polycephalum]]"]
---

# Cuerpo hongo de la mosca

En la mosca de la fruta, unas 50 neuronas de olor proyectan al azar sobre ~2 000 células de Kenyon, y solo ~5 % de ellas se activan para cada olor. Ese **código disperso** separa olores parecidos y se puede usar como función hash que conserva el parecido (FlyHash, Dasgupta et al., Science 2017).

En el vault, el modo «hongo» de `hipocampo.py` usa esa idea para encontrar notas parecidas aunque no compartan palabras exactas, y `comparar` la usa para avisar duplicados antes de escribir.
