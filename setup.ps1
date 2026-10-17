$ErrorActionPreference = 'Stop'
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectDir '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    python -m venv (Join-Path $ProjectDir '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed.' }
}
& $Python -m pip install -r (Join-Path $ProjectDir 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
$Shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $ProjectDir 'JTranslate.lnk'))
$Shortcut.TargetPath = Join-Path $ProjectDir '.venv\Scripts\pythonw.exe'
$Shortcut.Arguments = '"' + (Join-Path $ProjectDir 'translate.pyw') + '"'
$Shortcut.IconLocation = (Join-Path $ProjectDir 'assets\jtranslate-d-yaku.ico') + ',0'
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.Save()
Write-Output 'Ready. Run JTranslate.cmd. No startup or login settings were changed.'
