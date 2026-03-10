param(
  [string]$Root = "C:\smarthouse",
  [string]$PythonVersion = "3.12"
)

$ErrorActionPreference = "Stop"

if (!(Test-Path $Root)) {
  Write-Output "SETUP_VENV=failed reason=missing_root path=$Root"
  exit 1
}

Set-Location $Root

if (!(Get-Command py -ErrorAction SilentlyContinue)) {
  Write-Output "SETUP_VENV=failed reason=py_launcher_missing"
  exit 1
}

if (!(Test-Path ".venv")) {
  py -$PythonVersion -m venv .venv
  if ($LASTEXITCODE -ne 0) {
    Write-Output "SETUP_VENV=failed reason=venv_create_failed python=$PythonVersion"
    exit $LASTEXITCODE
  }
}

$python = Join-Path $Root ".venv\Scripts\python.exe"
if (!(Test-Path $python)) {
  Write-Output "SETUP_VENV=failed reason=missing_interpreter path=$python"
  exit 1
}

$actualVersion = (& $python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if ($LASTEXITCODE -ne 0) {
  Write-Output "SETUP_VENV=failed reason=python_version_probe_failed"
  exit $LASTEXITCODE
}

if ($actualVersion -ne $PythonVersion) {
  Write-Output "SETUP_VENV=failed reason=python_version_mismatch expected=$PythonVersion actual=$actualVersion"
  Write-Output "Hint: remove .venv and rerun with Python $PythonVersion installed (py -$PythonVersion)."
  exit 1
}

& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
  Write-Output "SETUP_VENV=failed reason=pip_upgrade_failed"
  exit $LASTEXITCODE
}

$requirements = Get-ChildItem -Recurse -Filter requirements.txt | Where-Object { $_.FullName -notmatch "\\.venv\\" } | Sort-Object FullName
foreach ($req in $requirements) {
  Write-Output "Installing $($req.FullName)"
  & $python -m pip install -r $req.FullName
  if ($LASTEXITCODE -ne 0) {
    Write-Output "SETUP_VENV=failed reason=requirements_install_failed file=$($req.FullName)"
    exit $LASTEXITCODE
  }
}

Write-Output "SETUP_VENV=ok interpreter=$python python=$actualVersion"
