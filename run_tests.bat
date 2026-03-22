@echo off
REM GoodBooks - Run Test Suite
REM Make sure MongoDB is running and venv is activated

echo ========================================
echo GoodBooks Test Suite
echo ========================================

call venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
    echo Warning: Could not activate venv. Using system Python.
)

echo.
echo [1] Running Unit + API + Route tests...
python -m pytest tests/test_auth.py tests/test_api.py tests/test_routes.py tests/test_search.py tests/test_recommendations.py tests/test_models.py -v --ignore=tests/e2e
set RESULT=%ERRORLEVEL%

echo.
if %RESULT%==0 (
    echo ========================================
    echo All tests PASSED!
    echo ========================================
) else (
    echo ========================================
    echo Some tests FAILED. See output above.
    echo ========================================
)

exit /b %RESULT%
