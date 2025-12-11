# Stop the Bible Query System

Write-Host "Stopping Bible Query System..." -ForegroundColor Yellow
docker-compose down

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ System stopped successfully" -ForegroundColor Green
} else {
    Write-Host "ERROR: Failed to stop services" -ForegroundColor Red
}
