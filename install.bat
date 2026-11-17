@echo off
setlocal EnableDelayedExpansion

echo ===================================================
echo     OmniHub 3.0 Installer (Windows) - SojibLabs
echo ===================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

echo [1/3] Checking Python version...
python --version

echo.
echo [2/3] Installing Python dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [3/3] Creating Windows launcher shortcut...
echo @echo off > "%~dp0run.bat"
echo start "" pythonw "%~dp0main.py" >> "%~dp0run.bat"

echo.
echo ===================================================
echo     OmniHub installed successfully!
echo     Run 'run.bat' or 'python main.py' to launch.
echo ===================================================
echo.
pause
