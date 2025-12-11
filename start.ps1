# Bible Query System - Quick Start Script
# Run this script to start the prototype

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Bible Query System - Starting Prototype  " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is installed
Write-Host "Checking Docker installation..." -ForegroundColor Yellow
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Docker is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop" -ForegroundColor Red
    exit 1
}

# Check if docker-compose is available
if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: docker-compose is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Docker is installed" -ForegroundColor Green
Write-Host ""

# Check if kjv_chunks.jsonl exists
Write-Host "Checking for verse data..." -ForegroundColor Yellow
if (-not (Test-Path "kjv_chunks.jsonl")) {
    Write-Host "ERROR: kjv_chunks.jsonl not found in current directory" -ForegroundColor Red
    Write-Host "Please ensure kjv_chunks.jsonl is in the project root" -ForegroundColor Red
    exit 1
}

$fileSize = (Get-Item "kjv_chunks.jsonl").Length / 1MB
Write-Host "✓ Found kjv_chunks.jsonl ($("{0:N2}" -f $fileSize) MB)" -ForegroundColor Green
Write-Host ""

# Stop any existing containers
Write-Host "Stopping any existing containers..." -ForegroundColor Yellow
docker-compose down 2>$null
Write-Host ""

# Build and start services
Write-Host "Building and starting services..." -ForegroundColor Yellow
Write-Host "This may take a few minutes on first run..." -ForegroundColor Gray
Write-Host ""

docker-compose up --build -d

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  ✓ Bible Query System is Running!         " -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Frontend UI:  http://localhost:3000" -ForegroundColor Cyan
    Write-Host "Backend API:  http://localhost:8000" -ForegroundColor Cyan
    Write-Host "API Docs:     http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Press Ctrl+C to view logs, or run:" -ForegroundColor Gray
    Write-Host "  docker-compose logs -f" -ForegroundColor Gray
    Write-Host ""
    Write-Host "To stop the system, run:" -ForegroundColor Gray
    Write-Host "  docker-compose down" -ForegroundColor Gray
    Write-Host ""
    
    # Wait a moment for services to start
    Start-Sleep -Seconds 3
    
    # Open browser
    Write-Host "Opening browser..." -ForegroundColor Yellow
    Start-Process "http://localhost:3000"
    
} else {
    Write-Host ""
    Write-Host "ERROR: Failed to start services" -ForegroundColor Red
    Write-Host "Check logs with: docker-compose logs" -ForegroundColor Yellow
    exit 1
}
