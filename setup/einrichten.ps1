# Richtet SolidWorks-KI auf diesem Rechner ein. Idempotent: mehrfach ausführbar.
# Aufruf: powershell -ExecutionPolicy Bypass -File setup\einrichten.ps1 [-Jahr 2025] [-OhneMcp] [-OhneApi]
param(
    [int]$Jahr = 0,
    [switch]$OhneMcp,
    [switch]$OhneApi
)
$ErrorActionPreference = "Stop"
$Projekt = Split-Path -Parent $PSScriptRoot
$SwkiHome = Join-Path $env:USERPROFILE ".swki"
$McpRepo = "https://github.com/andrewbartels1/SolidworksMCP-python.git"
# Upstream hat main umgeschrieben: e8d1cdd ist baugleich (gleicher Tree) mit dem früheren Pin 600624f
$McpCommit = "e8d1cddca3fd537973433714fb7578889b36322b"

function Pruefe([string]$Schritt) {
    if ($LASTEXITCODE -ne 0) { throw "Fehlgeschlagen: $Schritt (Exit-Code $LASTEXITCODE)" }
}

function Finde-Python {
    foreach ($kandidat in @("python", "py")) {
        $cmd = Get-Command $kandidat -ErrorAction SilentlyContinue
        if ($cmd) {
            $version = & $cmd.Source -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"
            $teile = $version.Split(".")
            if ([int]$teile[0] -eq 3 -and [int]$teile[1] -ge 13) { return $cmd.Source }
        }
    }
    throw "Python >= 3.13 nicht gefunden."
}

Write-Host "== 1/5 Python-Umgebung des Projekts"
$Python = Finde-Python
$VenvPy = Join-Path $Projekt ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPy)) { & $Python -m venv (Join-Path $Projekt ".venv"); Pruefe "venv anlegen" }
& $VenvPy -m pip install --quiet -e "$Projekt[dev,pdf,schnellbau]"; Pruefe "pip install swki (mit dev, pdf, schnellbau)"

Write-Host "== 2/5 Rechnerkonfiguration"
New-Item -ItemType Directory -Force -Path $SwkiHome | Out-Null
$initArgs = @("-m", "swki", "rechner", "init")
if ($Jahr -gt 0) { $initArgs += @("--jahr", "$Jahr") }
& $VenvPy @initArgs; Pruefe "swki rechner init"
$Rechner = (& $VenvPy -m swki rechner zeigen) -join "`n" | ConvertFrom-Json
Pruefe "swki rechner zeigen"

Write-Host "== 3/5 Umgebungsvariable SWKI_SW_YEAR = $($Rechner.sw_jahr)"
[Environment]::SetEnvironmentVariable("SWKI_SW_YEAR", "$($Rechner.sw_jahr)", "User")
$env:SWKI_SW_YEAR = "$($Rechner.sw_jahr)"

if (-not $OhneMcp) {
    Write-Host "== 4/5 MCP-Server SolidworksMCP-python @ $McpCommit"
    $McpDir = Join-Path $SwkiHome "SolidworksMCP-python"
    if (-not (Test-Path (Join-Path $McpDir ".git"))) { git clone --quiet $McpRepo $McpDir; Pruefe "git clone" }
    # Commit gezielt holen: ein Fetch der Branches erreicht ihn nicht mehr, sobald Upstream die Historie umschreibt
    git -C $McpDir fetch --quiet origin $McpCommit; Pruefe "git fetch"
    git -C $McpDir checkout --quiet $McpCommit; Pruefe "git checkout"
    $McpPy = Join-Path $McpDir ".venv\Scripts\python.exe"
    if (-not (Test-Path $McpPy)) { & $Python -m venv (Join-Path $McpDir ".venv"); Pruefe "MCP-venv anlegen" }
    & $McpPy -m pip install --quiet -e $McpDir; Pruefe "pip install MCP-Server (ohne Extras)"
}

if (-not $OhneApi) {
    Write-Host "== 5/5 API-Nachschlagewerk (kann einige Minuten dauern)"
    & $VenvPy -m swki api bauen; Pruefe "swki api bauen"
}

Write-Host "Fertig. Claude Code neu starten, damit SWKI_SW_YEAR wirkt."
