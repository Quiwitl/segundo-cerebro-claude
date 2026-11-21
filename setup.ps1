# Instala tu vault desde esta plantilla (Windows 10/11).
# Uso: doble clic en instalar.bat, o en PowerShell:
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1
# Instala lo que falte con winget (Git, Python, uv, Obsidian, Gitleaks) y Claude Code.
$ErrorActionPreference = "Stop"
$Aqui = Split-Path -Parent $MyInvocation.MyCommand.Path

function Refrescar-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}
function Instalar($comando, $id) {
    if (-not (Get-Command $comando -ErrorAction SilentlyContinue)) {
        Write-Host "Instalando $id..."
        winget install --id $id -e --accept-source-agreements --accept-package-agreements | Out-Null
        Refrescar-Path
    }
}

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "Falta winget: instala «App Installer» desde Microsoft Store y vuelve a correr este script."
    exit 1
}
Instalar git Git.Git
Instalar python Python.Python.3.13
Instalar uv astral-sh.uv
Instalar gitleaks Gitleaks.Gitleaks
if (-not (Test-Path "$env:LOCALAPPDATA\Programs\Obsidian\Obsidian.exe")) {
    Write-Host "Instalando Obsidian..."
    winget install --id Obsidian.Obsidian -e --accept-source-agreements --accept-package-agreements | Out-Null
}
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Host "Instalando Claude Code..."
    Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression
    Refrescar-Path
}

$Nombre = Read-Host "Tu nombre"
$Clave = Read-Host "Tu palabra clave para actualizar el vault [Actualiza]"
if (-not $Clave) { $Clave = "Actualiza" }
$Destino = Read-Host "Carpeta del vault [$env:USERPROFILE\Documents\SegundoCerebro]"
if (-not $Destino) { $Destino = "$env:USERPROFILE\Documents\SegundoCerebro" }
$Fuentes = Read-Host "Carpetas que leerá la actualización, separadas por ; (opcional)"

if ((Test-Path $Destino) -and (Get-ChildItem $Destino -Force | Select-Object -First 1)) {
    Write-Host "La carpeta $Destino ya existe y no está vacía. Elige otra."
    exit 1
}
New-Item -ItemType Directory -Force $Destino | Out-Null
# copia la plantilla sin su historial: tu vault empieza su propio repo y nunca apunta al público
robocopy $Aqui $Destino /E /XD .git /XF setup.ps1 setup.sh instalar.bat README.md LICENSE /NFL /NDL /NJH /NJS | Out-Null

Set-Location $Destino
python .cerebro\personalizar.py --nombre "$Nombre" --clave "$Clave" --fuentes "$Fuentes"
New-Item -ItemType Directory -Force .claude\agents | Out-Null
Copy-Item .cerebro\agentes\fuentes.md, .cerebro\agentes\ubicador.md, .cerebro\agentes\revisor.md .claude\agents\ -Force
git init -q -b main
git config core.hooksPath .cerebro/hooks
python .cerebro\hipocampo.py indexar | Out-Null
python .cerebro\vault.py indice | Out-Null
python .cerebro\pruebas.py | Select-Object -Last 1
git add -A
git commit -q -m "vault creado desde la plantilla"

Write-Host ""
Write-Host "Listo: $Destino"
Write-Host "1. Abre Obsidian -> Abrir carpeta como bóveda -> $Destino"
Write-Host "2. Crea un repo PRIVADO en GitHub y conéctalo: git remote add origin <url>; git push -u origin main"
Write-Host "3. En esa carpeta escribe: claude   y luego tu clave: $Clave"
