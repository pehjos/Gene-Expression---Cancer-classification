$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$taskPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    throw 'Create the .venv environment and install requirements.txt first. See README.md.'
}
New-Item -ItemType Directory -Force 'tmp' | Out-Null
$env:TEMP = Join-Path $PSScriptRoot 'tmp'
$env:TMP = $env:TEMP
$env:MPLCONFIGDIR = Join-Path $PSScriptRoot 'tmp/matplotlib'
foreach ($taskScript in @('src/load_data.py','src/analysis.py','src/build_report.py','tests/verify_artifacts.py')) {
    & $taskPython $taskScript
    if ($LASTEXITCODE -ne 0) { throw "Failed: $taskScript" }
}
