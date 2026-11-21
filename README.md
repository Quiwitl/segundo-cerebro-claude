# Segundo cerebro con Claude y Obsidian

**[Español](#español) · [English](#english)**

---

## Español

Una plantilla de vault de Obsidian que **Claude Code mantiene contigo**. Tú escribes o le pasas fuentes (exports de chats, PDFs, apuntes) y Claude las ubica, las enlaza y las encuentra después leyendo lo mínimo.

Lo distinto: el vault trae un pequeño «cerebro» en `.cerebro/`, con ideas tomadas de la neurociencia y **medidas antes de activarse**.

| Pieza | Inspiración | Qué hace |
|---|---|---|
| `hipocampo.py` | Teoría del índice hipocampal | Busca con una línea por candidata; Claude abre solo la nota que sirve y el buscador aprende de lo que de verdad usaste |
| Cuerpo hongo (FlyHash) | Células de Kenyon de la mosca (Dasgupta et al., 2017) | Encuentra parecidos sin palabras exactas y avisa duplicados antes de escribir |
| `physarum.py` + `ruta.py` | El moho que copió la red de trenes de Tokio (Tero et al., 2010) | Los caminos entre notas que se usan engordan y se leen primero |
| `conectoma.py` | Análisis de conectomas | Hubs, puentes y regiones de tu vault |
| Pendientes con señal | Memoria prospectiva | Un pendiente «despierta» (⏰) cuando buscas su tema |
| Olvido activo | Olvido por dopamina en la mosca | Lo reemplazado baja a «Historial»; arriba solo queda lo vigente |
| Lecciones con contadores | ACE (ICLR 2026) | Claude anota qué le ayudó y qué le estorbó, sin reescribir su memoria |

**Regla de corte:** una idea entra solo si mejora la puntería del buscador (`hipocampo.py evaluar`, con tus preguntas) o baja los tokens, sin bajar un conjunto de control.

### Requisitos

- Windows 10/11, macOS o Linux.
- [Claude Code](https://docs.claude.com/en/docs/claude-code) con una cuenta Claude Pro o Max (o una API key).
- Git, Python 3.10+ y [Obsidian](https://obsidian.md). Recomendados: [uv](https://docs.astral.sh/uv/) (para las herramientas de red) y [gitleaks](https://github.com/gitleaks/gitleaks).

### Instalación

**Windows:** descarga o clona este repo y haz doble clic en `instalar.bat`. Instala lo que falte con winget, te pregunta tu nombre, tu palabra clave y la carpeta del vault, y deja todo listo.

**macOS / Linux:**

```bash
git clone <url de este repo> plantilla-vault
cd plantilla-vault
bash setup.sh
```

El instalador **copia** la plantilla a una carpeta nueva y empieza un repo propio: tu vault nunca queda conectado a este repo público.

### Primer uso

1. En Obsidian: **Abrir carpeta como bóveda** → la carpeta de tu vault.
2. Crea un repo **privado** en GitHub y conéctalo (`git remote add origin <url>` y `git push -u origin main`). Tus notas nunca deben ir a un repo público.
3. En la carpeta del vault, escribe `claude` y luego tu palabra clave: Claude hace una **actualización** completa (lee lo nuevo, lo integra, verifica, hace commit y push).
4. Pregunta lo que quieras sobre tus notas. Empieza por `wiki/areas/Bienvenida.md`.

Las notas de ejemplo son inventadas: bórralas cuando quieras. Luego escribe tus propias preguntas en `.cerebro/preguntas.json` para medir el buscador con tus palabras.

### Qué hay dentro

```
CLAUDE.md                  reglas que sigue Claude (con tu nombre y tu clave)
wiki/                      tus notas: areas, concepts, learning, sources, meta
wiki/meta/claude/          la bóveda de método de Claude: lo que aprende al trabajar contigo
.cerebro/                  las herramientas (ver .cerebro/LEEME.md)
.claude/skills/            la skill de actualización
.raw/                      fuentes sin procesar (exports, PDFs); no se editan
_templates/                plantilla de nota para Obsidian
```

### Privacidad

- `privado: true` en el frontmatter: la nota no sale en el catálogo ni se cita en otras notas.
- El hook de pre-commit corre gitleaks: un secreto (token, contraseña) detiene el commit.
- Los exports completos de chats (`.raw/export-*/`) no van a git.

### Créditos

Creado por Atlahua Quiahuitl Martínez Obregón con Claude, a partir de su propio vault. Licencia MIT.

---

## English

An Obsidian vault template that **Claude Code maintains with you**. You write notes or hand it sources (chat exports, PDFs, class notes), and Claude files them, links them and finds them later while reading as little as possible.

What makes it different: the vault ships with a small "brain" in `.cerebro/`, built from neuroscience ideas that were **measured before being switched on**.

| Piece | Inspiration | What it does |
|---|---|---|
| `hipocampo.py` | Hippocampal indexing theory | Search returns one line per candidate; Claude opens only the note it needs, and search learns from the notes you actually used |
| Mushroom body (FlyHash) | Fruit-fly Kenyon cells (Dasgupta et al., 2017) | Finds similar notes without exact words and flags duplicates before writing |
| `physarum.py` + `ruta.py` | The slime mold that rebuilt the Tokyo rail network (Tero et al., 2010) | Paths between notes that get used grow thicker and are read first |
| `conectoma.py` | Connectome analysis | Hubs, bridges and regions of your vault |
| Cued to-dos | Prospective memory | A to-do "wakes up" (⏰) when you search its topic |
| Active forgetting | Dopamine-driven forgetting in flies | Superseded facts move to a "Historial" section; only current facts stay on top |
| Lessons with counters | ACE (ICLR 2026) | Claude records what helped and what got in the way, without rewriting its memory |

**Cut-off rule:** an idea goes in only if it improves search accuracy (`hipocampo.py evaluar`, with your own questions) or lowers token use, without hurting a control set.

### Requirements

- Windows 10/11, macOS or Linux.
- [Claude Code](https://docs.claude.com/en/docs/claude-code) with a Claude Pro or Max plan (or an API key).
- Git, Python 3.10+ and [Obsidian](https://obsidian.md). Recommended: [uv](https://docs.astral.sh/uv/) (for the network tools) and [gitleaks](https://github.com/gitleaks/gitleaks).

### Install

**Windows:** download or clone this repo and double-click `instalar.bat`. It installs anything missing with winget, asks for your name, your trigger word and the vault folder, and sets everything up.

**macOS / Linux:**

```bash
git clone <this repo's url> vault-template
cd vault-template
bash setup.sh
```

The installer **copies** the template into a new folder and starts a fresh repo: your vault is never connected to this public repo.

### First steps

1. In Obsidian: **Open folder as vault** → your vault folder.
2. Create a **private** GitHub repo and connect it (`git remote add origin <url>` and `git push -u origin main`). Your notes should never go to a public repo.
3. In the vault folder, run `claude` and type your trigger word: Claude runs a full **update** (reads what's new, files it, verifies, commits and pushes).
4. Ask anything about your notes. Start with `wiki/areas/Bienvenida.md`.

The notes and tools are in Spanish; Claude works fine in other languages, and you can write your notes in yours. The sample notes are made up: delete them whenever you like. Then write your own questions in `.cerebro/preguntas.json` to measure search with your own words.

### What's inside

```
CLAUDE.md                  rules Claude follows (with your name and trigger word)
wiki/                      your notes: areas, concepts, learning, sources, meta
wiki/meta/claude/          Claude's method vault: what it learns while working with you
.cerebro/                  the tools (see .cerebro/LEEME.md)
.claude/skills/            the update skill
.raw/                      raw sources (exports, PDFs); never edited
_templates/                Obsidian note template
```

### Privacy

- `privado: true` in a note's frontmatter keeps it out of the catalog and out of other notes.
- The pre-commit hook runs gitleaks: a secret (token, password) stops the commit.
- Full chat exports (`.raw/export-*/`) are git-ignored.

### Credits

Created by Atlahua Quiahuitl Martínez Obregón with Claude, from his own vault. MIT license.
