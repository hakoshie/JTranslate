$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Pythonw = Join-Path $ProjectDir '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $Pythonw)) {
    # Reuse the existing installation on this PC without changing it.
    $Pythonw = Join-Path $env:USERPROFILE 'Downloads\jhenkan\.venv\Scripts\pythonw.exe'
}
if (-not (Test-Path -LiteralPath $Pythonw)) {
    Write-Error 'Python environment missing. See TRANSLATE.md.'
    exit 1
}
Start-Process -FilePath $Pythonw -ArgumentList ('"' + (Join-Path $ProjectDir 'translate.pyw') + '"') -WorkingDirectory $ProjectDir -WindowStyle Hidden
