# create_defibrillator.ps1
# Creates a "Pulse Defibrillator" desktop shortcut to relaunch NeveWare-Pulse.
# Run once. No admin required.

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$TrayScript  = Join-Path $ScriptDir "tray_app.py"
$IconFile    = Join-Path $ScriptDir "assets\nevaware_logo_256.png"
$ShortcutPath = [System.IO.Path]::Combine(
    [System.Environment]::GetFolderPath("Desktop"),
    "Pulse Defibrillator.lnk"
)

# Find pythonw.exe
$PythonExe  = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    Write-Error "python.exe not found on PATH."
    exit 1
}
$PythonwExe = Join-Path (Split-Path $PythonExe) "pythonw.exe"
if (-not (Test-Path $PythonwExe)) {
    $PythonwExe = $PythonExe
}

# Create shortcut via WScript.Shell
$WS = New-Object -ComObject WScript.Shell
$SC = $WS.CreateShortcut($ShortcutPath)
$SC.TargetPath       = $PythonwExe
$SC.Arguments        = "`"$TrayScript`""
$SC.WorkingDirectory = $ScriptDir
$SC.Description      = "Relaunch NeveWare-Pulse. Bring her back online."
$SC.WindowStyle      = 7  # Minimised (no console flash)
$SC.Save()

Write-Host ""
Write-Host "  Pulse Defibrillator created on your desktop." -ForegroundColor Cyan
Write-Host "  Double-click it any time to relaunch NeveWare-Pulse." -ForegroundColor Cyan
Write-Host ""
