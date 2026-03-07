# register_task.ps1 — Register NeveWare-Pulse as a Windows startup task.
#
# Run as Administrator (or accept the UAC prompt).
# Uses pythonw.exe so no console window appears.
#
# Task name:   NeveWare-Pulse
# Trigger:     At logon (current user)
# Action:      pythonw.exe tray_app.py
# Run level:   Limited (interactive, not elevated)

$TaskName   = "NeveWare-Pulse"
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ScriptPath = Join-Path $ScriptDir "tray_app.py"

# Find pythonw.exe alongside the current python.exe
$PythonExe  = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    Write-Error "python.exe not found on PATH. Ensure Python is installed and on PATH."
    exit 1
}
$PythonwExe = Join-Path (Split-Path $PythonExe) "pythonw.exe"
if (-not (Test-Path $PythonwExe)) {
    # Fallback to python.exe if pythonw.exe not present
    $PythonwExe = $PythonExe
    Write-Warning "pythonw.exe not found alongside python.exe. Using python.exe instead (console window will appear)."
}

Write-Host "Registering task: $TaskName"
Write-Host "  Executable: $PythonwExe"
Write-Host "  Script:     $ScriptPath"

# Remove existing task if present
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "  Removed existing task."
}

# Build action
$Action  = New-ScheduledTaskAction `
    -Execute $PythonwExe `
    -Argument "`"$ScriptPath`"" `
    -WorkingDirectory $ScriptDir

# Trigger: at logon of current user
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# Settings: run only when user is logged in, no elevation
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -MultipleInstances IgnoreNew

# Principal: run as current user, limited privilege
$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

# Register
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "NeveWare-Pulse — DI presence and heartbeat tool (FoxPur Studios)" `
    -Force | Out-Null

$check = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($check) {
    Write-Host "Task '$TaskName' registered successfully." -ForegroundColor Green
    Write-Host "NeveWare-Pulse will start automatically at next login."
} else {
    Write-Error "Task registration failed. Check permissions and try running as Administrator."
    exit 1
}
