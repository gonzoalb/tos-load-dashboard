# ============================================================
# TOS Dashboard - Data Refresh Script
# Run this after downloading a fresh FMC CSV export
# ============================================================
# Usage:
#   Option A: Double-click this file (or right-click > Run with PowerShell)
#   Option B: Schedule with Windows Task Scheduler for auto-push
# ============================================================

$ErrorActionPreference = "Stop"

# --- CONFIGURATION ---
$DASHBOARD_DIR = "C:\Users\gonzoalb\Orcha\ct_1782594304_6294"
$DOWNLOADS_DIR = "C:\Users\gonzoalb\Downloads"
$GIT_PATH = "C:\Users\gonzoalb\AppData\Local\Programs\Git\cmd"
$DATA_FILE = "$DASHBOARD_DIR\data\fmc_export.csv"

# Add Git to PATH
$env:PATH = "$GIT_PATH;$env:PATH"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  TOS Dashboard - Data Refresh" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# --- FIND LATEST FMC CSV ---
# FMC exports use UUID filenames. Find the most recently modified CSV in Downloads.
Write-Host "[1/4] Finding latest FMC CSV export..." -ForegroundColor Yellow

# Look for UUID-pattern CSVs (FMC format) modified in last 24 hours
$latestCSV = Get-ChildItem -Path $DOWNLOADS_DIR -Filter "*.csv" |
    Where-Object { $_.Name -match "^[0-9a-f]{8}-[0-9a-f]{4}-" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $latestCSV) {
    Write-Host "  ERROR: No recent FMC CSV found in Downloads!" -ForegroundColor Red
    Write-Host "  Please download from FMC first:" -ForegroundColor Red
    Write-Host "  https://trans-logistics.amazon.com/fmc/execution/Ge47T3" -ForegroundColor Gray
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "  Found: $($latestCSV.Name)" -ForegroundColor Green
Write-Host "  Modified: $($latestCSV.LastWriteTime)" -ForegroundColor Gray
Write-Host "  Size: $([math]::Round($latestCSV.Length / 1MB, 2)) MB" -ForegroundColor Gray

# --- VALIDATE IT'S FMC DATA ---
Write-Host ""
Write-Host "[2/4] Validating FMC data..." -ForegroundColor Yellow

$header = Get-Content $latestCSV.FullName -TotalCount 1
if ($header -notmatch "Load #" -or $header -notmatch "Lane") {
    Write-Host "  ERROR: File doesn't look like FMC export (missing expected columns)" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

$lineCount = (Get-Content $latestCSV.FullName | Measure-Object).Count
Write-Host "  Valid FMC export: $($lineCount - 1) loads" -ForegroundColor Green

# --- COPY TO DASHBOARD ---
Write-Host ""
Write-Host "[3/4] Updating dashboard data..." -ForegroundColor Yellow

Copy-Item -Path $latestCSV.FullName -Destination $DATA_FILE -Force
Write-Host "  Copied to: $DATA_FILE" -ForegroundColor Green

# --- GIT PUSH ---
Write-Host ""
Write-Host "[4/4] Pushing to GitHub..." -ForegroundColor Yellow

Set-Location $DASHBOARD_DIR

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
git add data/fmc_export.csv
git commit -m "Refresh FMC data - $timestamp ($($lineCount - 1) loads)"

# Push (uses stored credentials or credential manager)
git push origin main 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  SUCCESS! Dashboard updated." -ForegroundColor Green
    Write-Host "  $($lineCount - 1) loads pushed to production." -ForegroundColor Green
    Write-Host "  Dashboard will refresh within 1 minute." -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "  WARNING: Git push may have failed." -ForegroundColor Yellow
    Write-Host "  Check if you need to authenticate with GitHub." -ForegroundColor Yellow
}

Write-Host ""
Read-Host "Press Enter to close"
