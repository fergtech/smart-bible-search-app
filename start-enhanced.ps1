# Quick Start - Bible Query System with Enhanced Frontend
# Run this script to start the complete system

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Bible Query System - Enhanced Version " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start Backend
Write-Host "Starting Backend API..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "H:/Apps/book-intel/.venv/Scripts/python.exe h:\Apps\book-intel\backend\app.py" -WindowStyle Normal
Start-Sleep -Seconds 3

Write-Host "✓ Backend started on http://localhost:8000" -ForegroundColor Green
Write-Host ""

# Open Frontend
Write-Host "Opening Frontend..." -ForegroundColor Yellow
Start-Process "h:\Apps\book-intel\frontend\index.html"
Start-Sleep -Seconds 2

Write-Host "✓ Frontend opened in browser" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host " System Ready! " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Frontend: file:///h:/Apps/book-intel/frontend/index.html" -ForegroundColor Cyan
Write-Host "Backend API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "New Features:" -ForegroundColor White
Write-Host "  • Expandable verse cards" -ForegroundColor Gray
Write-Host "  • View full chapter context" -ForegroundColor Gray
Write-Host "  • Highlighted matched verses" -ForegroundColor Gray
Write-Host "  • Responsive mobile/desktop layout" -ForegroundColor Gray
Write-Host ""
Write-Host "Try searching for: 'faith', 'love thy neighbor', or 'valley of the shadow'" -ForegroundColor Yellow
Write-Host ""
