# Builds the Windows executable with PyInstaller.
# Output: dist\F1LiveTelemetry\F1LiveTelemetry.exe
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Creating virtual environment and installing dependencies..."
    python -m venv (Join-Path $root ".venv")
    & $python -m pip install --disable-pip-version-check -q -r (Join-Path $root "requirements.txt") pyinstaller
}

# rutas absolutas: PyInstaller resuelve dist/build contra el CWD si no
& $python -m PyInstaller --noconfirm --clean `
    --distpath (Join-Path $root "dist") `
    --workpath (Join-Path $root "build") `
    (Join-Path $root "f1telem.spec")
if ($LASTEXITCODE -eq 0) {
    $app = Join-Path $root "dist\F1LiveTelemetry"
    # el capturador sale como carpeta hermana 'capture': moverla dentro de la
    # app (su propio _internal, para actualizar la app sin frenar la captura)
    $capSrc = Join-Path $root "dist\capture"
    $capDst = Join-Path $app "capture"
    if (Test-Path $capSrc) {
        if (Test-Path $capDst) { Remove-Item $capDst -Recurse -Force }
        Move-Item $capSrc $capDst -Force
    }
    Copy-Item (Join-Path $root "capture.ps1") $app -Force
    # extensión de Chrome para el login F1TV (cargar descomprimida)
    Copy-Item (Join-Path $root "extension") $app -Recurse -Force
    # zip listo para subir al release de GitHub (el actualizador lo busca por
    # este nombre y espera la carpeta F1LiveTelemetry\ en la raíz del zip)
    $zip = Join-Path $root "dist\F1LiveTelemetry-win64.zip"
    Write-Host "Zipping release asset..."
    if (Test-Path $zip) { Remove-Item $zip -Force }
    Compress-Archive -Path (Join-Path $root "dist\F1LiveTelemetry") -DestinationPath $zip
    # instalador (si Inno Setup 6 esta disponible): dist\F1LiveTelemetry-setup.exe
    $iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
              "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
              "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") |
        Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $iscc) {
        $cmd = Get-Command iscc.exe -ErrorAction SilentlyContinue
        if ($cmd) { $iscc = $cmd.Source }
    }
    if ($iscc) {
        $initPy = Get-Content (Join-Path $root "src\f1telem\__init__.py") -Raw
        $version = if ($initPy -match '__version__\s*=\s*"([^"]+)"') { $Matches[1] } else { "0.0.0" }
        Write-Host "Building installer (Inno Setup, v$version)..."
        & $iscc /Q "/DAppVersion=$version" "/O$(Join-Path $root 'dist')" `
            (Join-Path $root "installer\F1LiveTelemetry.iss")
        if ($LASTEXITCODE -eq 0) {
            Write-Host "      $(Join-Path $root 'dist\F1LiveTelemetry-setup.exe')"
        }
    } else {
        Write-Host "Inno Setup not found - skipping installer (winget install JRSoftware.InnoSetup)"
    }
    Write-Host ""
    Write-Host "Done: $(Join-Path $root 'dist\F1LiveTelemetry\F1LiveTelemetry.exe')"
    Write-Host "      $zip"
}
