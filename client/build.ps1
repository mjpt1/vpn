# VPN Client - Quick Build Script
# Usage: .\build.ps1

param(
    [switch]$Clean,           # Clean old builds
    [switch]$Install,         # Install after build
    [switch]$Package,         # Create release package
    [switch]$SkipOptimize     # Skip optimization
)

$ErrorActionPreference = "Stop"

Write-Host "=" * 60
Write-Host "VPN Client Builder"
Write-Host "=" * 60
Write-Host ""

# Colors
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Error { Write-Host $args -ForegroundColor Red }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Info { Write-Host $args -ForegroundColor Cyan }

# Check if in client directory
if (-not (Test-Path "gui_main.py")) {
    Write-Error "ERROR: Run this script from the client directory!"
    Write-Error "cd c:\Users\mjpt1\Desktop\vpn\client"
    exit 1
}

# Check prerequisites
Write-Info "Checking prerequisites..."

$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python not found. Install Python 3.11+"
    exit 1
}
Write-Success "✓ Python: $pythonVersion"

$pyinstallerVersion = pyinstaller --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller not found. Install with:"
    Write-Error "  pip install PyInstaller==6.1.0"
    exit 1
}
Write-Success "✓ PyInstaller: $pyinstallerVersion"

# Clean if requested
if ($Clean) {
    Write-Info "Cleaning old builds..."
    if (Test-Path "build") {
        Remove-Item build -Recurse -Force
        Write-Success "✓ Removed build directory"
    }
    if (Test-Path "dist") {
        Remove-Item dist -Recurse -Force
        Write-Success "✓ Removed dist directory"
    }
}

# Check for existing builds
if ((Test-Path "build") -or (Test-Path "dist")) {
    Write-Warning "Old builds found. Use -Clean to remove them."
}

# Run build script
Write-Info "Running build script..."
Write-Info ""

python build.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed!"
    exit 1
}

Write-Success "✓ Build completed successfully!"
Write-Info ""

# Get build info
$exePath = Get-ChildItem dist\VPN_Client\VPN_Client.exe -ErrorAction SilentlyContinue
if ($exePath) {
    $exeSize = [math]::Round($exePath.Length / 1MB, 1)
    $distSize = [math]::Round(
        (Get-ChildItem dist -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 
        1
    )
    
    Write-Info "Build Statistics:"
    Write-Info "  EXE Size: ${exeSize} MB"
    Write-Info "  Total Dist: ${distSize} MB"
    Write-Info ""
}

# Installation step
if ($Install) {
    Write-Info "Installing VPN Client..."
    Write-Warning "This requires Administrator privileges!"
    
    # Check admin
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    
    if (-not $isAdmin) {
        Write-Error "Installation requires Administrator privileges!"
        Write-Error "Please run PowerShell as Administrator and try again."
        exit 1
    }
    
    # Run installer
    python installer.py dist\VPN_Client\VPN_Client.exe
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Installation failed!"
        exit 1
    }
    
    Write-Success "✓ Installation completed!"
}

# Package step
if ($Package) {
    Write-Info "Creating release package..."
    
    $version = "1.0.0"
    $packageDir = "VPN_Client_${version}"
    
    if (Test-Path $packageDir) {
        Remove-Item $packageDir -Recurse -Force
    }
    
    # Copy files
    Copy-Item -Path dist\VPN_Client -Destination $packageDir -Recurse
    
    # Copy documentation
    Copy-Item README_GUI.md "${packageDir}\SETUP.md" -ErrorAction SilentlyContinue
    Copy-Item README_CLIENT.md "${packageDir}\README.md" -ErrorAction SilentlyContinue
    
    # Create ZIP
    Compress-Archive -Path $packageDir -DestinationPath "${packageDir}.zip" -Force
    
    $zipSize = [math]::Round((Get-Item "${packageDir}.zip").Length / 1MB, 1)
    Write-Success "✓ Package created: ${packageDir}.zip (${zipSize} MB)"
}

Write-Info ""
Write-Success "=" * 60
Write-Success "Build completed successfully!"
Write-Success "=" * 60
Write-Info ""

# Next steps
Write-Info "Next steps:"
Write-Info "1. Test the EXE: .\dist\VPN_Client\VPN_Client.exe"
Write-Info "2. Install: .\build.ps1 -Install"
Write-Info "3. Package: .\build.ps1 -Package"
Write-Info ""
Write-Info "For more info, see: BUILD_DEPLOYMENT_GUIDE.md"
