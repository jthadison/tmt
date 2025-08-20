# PowerShell script to forcefully restart the dashboard
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DASHBOARD FORCE RESTART SCRIPT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Kill all Node.js processes (be careful, this kills ALL node processes)
Write-Host "Stopping all Node.js processes..." -ForegroundColor Yellow
$nodeProcesses = Get-Process -Name "node" -ErrorAction SilentlyContinue
if ($nodeProcesses) {
    $nodeProcesses | ForEach-Object {
        Write-Host "  Stopping process $($_.Id)..." -ForegroundColor Gray
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "All Node.js processes stopped." -ForegroundColor Green
} else {
    Write-Host "No Node.js processes found." -ForegroundColor Gray
}

Write-Host ""
Start-Sleep -Seconds 2

# Navigate to the legacy dashboard directory
Write-Host "Navigating to legacy dashboard directory..." -ForegroundColor Yellow
Set-Location -Path "src\dashboard"
Write-Host "Current directory: $(Get-Location)" -ForegroundColor Gray

Write-Host ""
Write-Host "Building the application with latest changes..." -ForegroundColor Yellow
& npm run build

Write-Host ""
Write-Host "Starting the dashboard server..." -ForegroundColor Green
Write-Host "The dashboard will be available at http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "IMPORTANT STEPS:" -ForegroundColor Red
Write-Host "1. Clear your browser cache (Ctrl+Shift+Delete)" -ForegroundColor Yellow
Write-Host "2. Navigate to http://localhost:3000" -ForegroundColor Yellow
Write-Host "3. Click 'Performance Analytics' button" -ForegroundColor Yellow
Write-Host "4. You should see the Performance Analytics page, NOT 'coming soon'" -ForegroundColor Yellow
Write-Host ""
Write-Host "Starting server now..." -ForegroundColor Green

& npm run dev