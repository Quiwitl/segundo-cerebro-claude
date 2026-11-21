---
type: meta
title: "Escritura en Windows"
id: n54f65c3d
description: "Lecciones: escribir archivos en Windows sin romper acentos, PATH tras winget y salida de comandos"
created: 2026-11-20
updated: 2026-11-20
tags: ["meta", "claude", "leccion", "windows"]
status: evergreen
related: ["[[Claude - método]]"]
---

# Escritura en Windows

- **Acentos rotos al escribir con PowerShell en línea** → la consola no garantiza UTF-8 → escribir con Python `open(p, 'w', encoding='utf-8', newline='\n')`.
- **`.ps1` con acentos** → guardarlo como UTF-8 **con BOM** (`utf-8-sig`) y ejecutarlo con `-ExecutionPolicy Bypass`.
- **PATH desactualizado tras winget** → `$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')`.
- **IDs de winget**: `Git.Git`, `Obsidian.Obsidian`, `Python.Python.3.13`, `astral-sh.uv`, `Gitleaks.Gitleaks`.
- **`python3` abre la Microsoft Store** → en Windows usar `python` (o desactivar los alias de ejecución de aplicaciones).
- **Abrir Claude Code en la carpeta del vault**, no en `C:\WINDOWS\system32` (pasa si la terminal se abre como administrador).
