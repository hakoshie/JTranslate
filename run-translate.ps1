$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Pythonw = Join-Path $ProjectDir '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $Pythonw)) {
    Write-Error 'Run setup.ps1 in this folder first.'
    exit 1
}
Start-Process -FilePath $Pythonw -ArgumentList ('"' + (Join-Path $ProjectDir 'translate.pyw') + '"') -WorkingDirectory $ProjectDir -WindowStyle Hidden
