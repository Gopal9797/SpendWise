[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("install", "run", "test", "reset-db", "reset-transactions", "help")]
    [string]$Task = "help",

    [Parameter()]
    [string]$PythonPath = ""
)

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path $ProjectRoot

function Resolve-Python {
    param(
        [string]$InputPath
    )

    if ($InputPath) {
        if (-not (Test-Path -Path $InputPath)) {
            throw "Python path not found: $InputPath"
        }
        return (Resolve-Path -Path $InputPath).Path
    }

    $venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path -Path $venvPython) {
        return $venvPython
    }

    $pythonCommand = Get-Command -Name python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        return $pythonCommand.Source
    }

    throw "Python executable not found. Install Python 3.12+ or pass -PythonPath."
}

function Show-Help {
    Write-Host "SpendWise command helper"
    Write-Host "Usage: .\dev.ps1 <install|run|test|reset-db|reset-transactions|help> [-PythonPath <path>]"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\dev.ps1 install"
    Write-Host "  .\dev.ps1 run"
    Write-Host "  .\dev.ps1 test"
    Write-Host "  .\dev.ps1 reset-db"
    Write-Host "  .\dev.ps1 reset-transactions"
}

if ($Task -eq "help") {
    Show-Help
    exit 0
}

$pythonExe = Resolve-Python -InputPath $PythonPath

switch ($Task) {
    "install" {
        & $pythonExe -m pip install -r requirements-dev.txt
        exit $LASTEXITCODE
    }

    "run" {
        & $pythonExe -m streamlit run app.py
        exit $LASTEXITCODE
    }

    "test" {
        & $pythonExe -m pytest -q
        exit $LASTEXITCODE
    }

    "reset-db" {
        $dbPath = Join-Path $ProjectRoot "spendwise.db"
        if (Test-Path -Path $dbPath) {
            Remove-Item -Path $dbPath -Force
            Write-Host "Deleted database: $dbPath"
        }
        else {
            Write-Host "No database file found at: $dbPath"
        }
        exit 0
    }

    "reset-transactions" {
        & $pythonExe -c "from spendwise.db.repository import SpendWiseRepository; repo = SpendWiseRepository(); repo.initialize(); deleted_count = repo.delete_all_transactions(); print(f'Deleted {deleted_count} transactions.')"
        exit $LASTEXITCODE
    }
}
