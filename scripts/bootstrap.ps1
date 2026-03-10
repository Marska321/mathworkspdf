param(
    [string]$PythonExe = "",
    [switch]$RunTests,
    [switch]$RunServer
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path $PSScriptRoot -Parent
$venvPath = Join-Path $projectRoot ".venv"
$requirementsPath = Join-Path $projectRoot "requirements.txt"

function Resolve-PythonExe {
    param([string]$Requested)

    if ($Requested -and (Test-Path $Requested)) {
        return $Requested
    }

    $candidates = @(
        "C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe",
        "C:\Users\User\AppData\Local\Programs\Python\Python311\python.exe",
        "C:\Python312\python.exe",
        "C:\Python311\python.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    throw "No Python interpreter found. Pass -PythonExe or install Python 3.11+ first."
}

$python = Resolve-PythonExe -Requested $PythonExe
& $python -m venv $venvPath
$venvPython = Join-Path $venvPath "Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r $requirementsPath

if ($RunTests) {
    & $venvPython -m pytest -q
}

if ($RunServer) {
    & $venvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8000
}
