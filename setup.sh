#!/usr/bin/env bash
# Instala tu vault desde esta plantilla (macOS y Linux).
# Uso: bash setup.sh
# Necesitas git, python3 (3.10+) y Claude Code. Obsidian y uv son recomendados.
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"

for cmd in git python3; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "Falta $cmd. Instálalo y vuelve a correr este script."; exit 1; }
done
command -v claude >/dev/null 2>&1 || echo "Aviso: no encontré Claude Code (claude). Instálalo: https://docs.claude.com/en/docs/claude-code"

read -r -p "Tu nombre: " NOMBRE
read -r -p "Tu palabra clave para actualizar el vault [Actualiza]: " CLAVE
CLAVE="${CLAVE:-Actualiza}"
read -r -p "Carpeta del vault [$HOME/SegundoCerebro]: " DESTINO
DESTINO="${DESTINO:-$HOME/SegundoCerebro}"
read -r -p "Carpetas que leerá la actualización, separadas por ; (opcional): " FUENTES

if [ -e "$DESTINO" ] && [ -n "$(ls -A "$DESTINO" 2>/dev/null)" ]; then
  echo "La carpeta $DESTINO ya existe y no está vacía. Elige otra."; exit 1
fi
mkdir -p "$DESTINO"
# copia la plantilla sin su historial: tu vault empieza su propio repo y nunca apunta al público
(cd "$AQUI" && tar --exclude=.git --exclude=setup.sh --exclude=setup.ps1 --exclude=instalar.bat \
  --exclude=README.md --exclude=LICENSE -cf - .) | (cd "$DESTINO" && tar -xf -)

cd "$DESTINO"
python3 .cerebro/personalizar.py --nombre "$NOMBRE" --clave "$CLAVE" --fuentes "$FUENTES"
mkdir -p .claude/agents && cp .cerebro/agentes/fuentes.md .cerebro/agentes/ubicador.md .cerebro/agentes/revisor.md .claude/agents/
git init -q -b main
chmod +x .cerebro/hooks/pre-commit
git config core.hooksPath .cerebro/hooks
python3 .cerebro/hipocampo.py indexar >/dev/null
python3 .cerebro/vault.py indice >/dev/null
python3 .cerebro/pruebas.py | tail -n 1
git add -A && git commit -q -m "vault creado desde la plantilla"

echo
echo "Listo: $DESTINO"
echo "1. Abre Obsidian → Abrir carpeta como bóveda → $DESTINO"
echo "2. Crea un repo PRIVADO en GitHub y conéctalo: git remote add origin <url> && git push -u origin main"
echo "3. En esa carpeta escribe: claude   y luego tu clave: $CLAVE"
