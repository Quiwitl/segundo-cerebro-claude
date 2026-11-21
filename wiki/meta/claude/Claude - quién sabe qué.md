---
type: meta
title: "Claude - quién sabe qué"
id: nb70fb874
description: "Directorio de memoria transactiva entre Claude y el usuario: dónde vive cada tipo de conocimiento y preguntas abiertas"
created: 2026-11-20
updated: 2026-11-20
tags: ["meta", "claude", "metodo"]
status: developing
related: ["[[Claude - método]]", "[[Registro de decisiones]]"]
---

# Claude – quién sabe qué

Directorio para no inventar ni guardar de más. Idea de la memoria transactiva (Wegner, 1987): una pareja no necesita saberlo todo, sino saber quién sabe qué.

## Dónde vive cada cosa

| Tipo de conocimiento | Dónde | Qué hace Claude |
|---|---|---|
| General (teoría, definiciones) | Pesos de Claude | No se guarda en el vault; si es reciente o cambia, se busca en la web |
| Lo del usuario y lo que decidió | El vault (`hipocampo.py buscar`, [[Registro de decisiones]]) | Se lee antes de preguntar |
| Lo que solo sabe el usuario | Su cabeza | Se le pregunta; va abajo y sale en el reporte de la actualización |
| Código y datos de proyectos | Sus carpetas y repos | Se lee el archivo, no una cifra copiada en una nota |

## Preguntas abiertas para el usuario

Se cierran con su respuesta (con fecha) y se mueven a la nota que corresponda.

- (ejemplo) ¿Qué carpetas quieres que lea la actualización?
