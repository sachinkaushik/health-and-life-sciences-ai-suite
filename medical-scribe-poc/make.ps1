# Windows counterpart of the Makefile: .\make.ps1 <setup|download-models|list-models|run> [-Models a,b] [-Config file]
param(
    [ValidateSet('help', 'setup', 'download-models', 'list-models', 'run')]
    [string]$Target = 'help',
    [string]$Models = '',
    [string]$Config = 'configs\models.yaml'
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$Py = Join-Path $PSScriptRoot 'workers\.venv\Scripts\python.exe'

switch ($Target) {
    'help' {
        Write-Host '.\make.ps1 setup             install tools, Python envs and frontend'
        Write-Host ".\make.ps1 download-models   download models from $Config (-Models name1,name2 to pick)"
        Write-Host '.\make.ps1 list-models       show model folders and their size'
        Write-Host '.\make.ps1 run               start the web UI (port from frontend\.env)'
    }
    'setup' {
        & "$PSScriptRoot\scripts\setup_win.bat"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        if (-not (Test-Path 'frontend\.env')) { Copy-Item 'frontend\.env.example' 'frontend\.env' }
    }
    'download-models' {
        if (-not (Test-Path $Py)) { throw "Run '.\make.ps1 setup' first" }
        $cmdArgs = @('scripts\download_models.py', '--config', $Config)
        if ($Models) { $cmdArgs += @('--only', $Models) }
        & $Py @cmdArgs
        exit $LASTEXITCODE
    }
    'list-models' {
        if (-not (Test-Path 'models')) { Write-Host 'No models downloaded yet'; break }
        Get-ChildItem 'models' -Directory | ForEach-Object {
            $bytes = (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
            '{0,8:N1} GB  {1}' -f ($bytes / 1GB), $_.Name
        }
    }
    'run' {
        & "$PSScriptRoot\scripts\start_win.bat"
    }
}
