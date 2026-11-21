---
type: meta
title: "Physarum del vault"
id: na0b0173b
description: "Simulación del moho Physarum sobre la red del vault: qué enlaces forman el esqueleto y cuáles se podarían"
created: 2026-11-20
updated: 2026-11-20
tags: [meta, red, physarum]
status: developing
generado_por: ".cerebro/physarum.py"
---

# Physarum del vault

> Generado por `.cerebro/physarum.py`. Modelo de Tero et al.: cada enlace es un tubo; los que llevan flujo entre notas al azar engordan y los demás se encogen. No modifica ningún enlace real: es una lectura de la red. Los nombres van sin enlazar para no alterar el grafo.

Simulación: 21 notas, 27 enlaces, 6000 rondas, μ = 1.3, semilla 7. Datos de conectoma del 2026-11-20 23:50.
Fuentes de alimento: todas al azar (todavía no hay búsquedas registradas con `hipocampo.py usar`).

![[physarum-del-vault.png]]

## Resumen

- Sobreviven **22 de 27 enlaces** (81 %): ese es el esqueleto.
- 7 de ellos unen regiones distintas: son las vías entre tus temas.
- Parecido con la intermediación clásica de conectoma.py (Spearman ρ = 0.66): coinciden en lo grueso y difieren en el detalle.
- 0 notas quedan fuera del esqueleto: el flujo no pasa por ellas.

## Las 15 vías más gruesas

| Enlace | Grosor | Regiones |
|---|---|---|
| Hipocampo como indice ↔ Cómo funciona el cerebro del vault | 1.00 | Hipocampo como indice / Cómo funciona el cerebro del vault |
| Cómo funciona el cerebro del vault ↔ Claude - método | 0.75 | Cómo funciona el cerebro del vault / Claude - método |
| Hipocampo como indice ↔ Zettelkasten | 0.74 | Hipocampo como indice / Hipocampo como indice |
| Cómo funciona el cerebro del vault ↔ Bienvenida | 0.67 | Cómo funciona el cerebro del vault / Bienvenida |
| Zettelkasten ↔ Repeticion espaciada | 0.40 | Hipocampo como indice / Bienvenida |
| Bienvenida ↔ Registro de decisiones | 0.31 | Bienvenida / Claude - método |
| Claude - método ↔ Claude - quién sabe qué | 0.25 | Claude - método / Claude - método |
| Hipocampo como indice ↔ Ejemplo de fuente - articulo | 0.23 | Hipocampo como indice / Hipocampo como indice |
| Bienvenida ↔ Proyecto de ejemplo - huerto urbano | 0.23 | Bienvenida / Bienvenida |
| Claude - método ↔ Escritura en Windows | 0.23 | Claude - método / Claude - método |
| Zettelkasten ↔ Ejemplo - historia del arte | 0.23 | Hipocampo como indice / Hipocampo como indice |
| Claude - método ↔ Herramientas de .cerebro | 0.22 | Claude - método / Cómo funciona el cerebro del vault |
| Claude - quién sabe qué ↔ Registro de decisiones | 0.22 | Claude - método / Claude - método |
| Claude - método ↔ Correcciones recurrentes | 0.21 | Claude - método / Claude - método |
| Bienvenida ↔ Entorno de trabajo | 0.21 | Bienvenida / Bienvenida |

## Puentes que sobreviven entre regiones

- Hipocampo como indice ↔ Cómo funciona el cerebro del vault (1.00)
- Cómo funciona el cerebro del vault ↔ Claude - método (0.75)
- Cómo funciona el cerebro del vault ↔ Bienvenida (0.67)
- Zettelkasten ↔ Repeticion espaciada (0.40)
- Bienvenida ↔ Registro de decisiones (0.31)
- Claude - método ↔ Herramientas de .cerebro (0.22)
- Cuerpo hongo de la mosca ↔ Hipocampo como indice (0.20)

## Cruces de caminos del esqueleto

Notas con más vías vivas: por aquí pasa casi todo el tránsito entre ideas.

- Claude - método: 7 vías
- Cómo funciona el cerebro del vault: 5 vías
- Hipocampo como indice: 4 vías
- Bienvenida: 4 vías
- Zettelkasten: 3 vías
- Cuerpo hongo de la mosca: 2 vías
- Physarum polycephalum: 2 vías
- Repeticion espaciada: 2 vías
- Registro de decisiones: 2 vías
- Claude - quién sabe qué: 2 vías

## Lo que el moho podaría aunque parezca importante

Enlaces con alta intermediación clásica que no sobreviven: hay otro camino más eficiente entre esas notas.

- Repeticion espaciada ↔ Proyecto de ejemplo - huerto urbano
- Claude - método ↔ Registro de decisiones
- Cómo funciona el cerebro del vault ↔ Herramientas de .cerebro
- Cuerpo hongo de la mosca ↔ Cómo funciona el cerebro del vault
- Cómo medir un cambio ↔ Registro de decisiones

## Notas fuera del esqueleto

Ninguna.

## Cómo leerlo

- Un enlace grueso no es "mejor": es el que más rutas entre tus temas aprovechan.
- Un enlace podado no sobra: solo existe otro camino más corto. Útil para ver redundancias.
- Una nota fuera del esqueleto puede ser un tema nuevo o aislado: candidata a conectarse con algo, o a quedarse como está.
