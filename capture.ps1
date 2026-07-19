# Launches the live capturer (F1TelemCapture.exe, its own executable so the
# main app can be updated without stopping a live capture).
# Works both next to the exe and from the repo root (dist\F1LiveTelemetry\).
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$candidates = @(
    (Join-Path $root "F1TelemCapture.exe"),
    (Join-Path $root "dist\F1LiveTelemetry\F1TelemCapture.exe")
)
$exe = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($exe) {
    Start-Process -FilePath $exe
    exit 0
}
# compatibilidad con builds viejos (un solo exe)
$legacy = @(
    (Join-Path $root "F1LiveTelemetry.exe"),
    (Join-Path $root "dist\F1LiveTelemetry\F1LiveTelemetry.exe")
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $legacy) {
    Write-Host "F1TelemCapture.exe not found next to this script (run build.ps1 first)."
    exit 1
}
Start-Process -FilePath $legacy -ArgumentList "--capture"
