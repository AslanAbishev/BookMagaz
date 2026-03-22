# GoodBooks - Run Test Suite
# Usage: .\run_tests.ps1
# Make sure MongoDB is running

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GoodBooks Test Suite" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Activate venv if exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
}

Write-Host ""
Write-Host "[1] Running Unit + API + Route + Search + Recommendation tests..." -ForegroundColor Yellow
python -m pytest tests/test_auth.py tests/test_api.py tests/test_routes.py tests/test_search.py tests/test_recommendations.py tests/test_models.py -v --ignore=tests/e2e
$result = $LASTEXITCODE

Write-Host ""
if ($result -eq 0) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "All tests PASSED!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Some tests FAILED. See output above." -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
}

exit $result
