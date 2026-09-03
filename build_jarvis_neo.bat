@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set PY=py) else (set PY=python)
%PY% -m pip install -r requirements.txt pyinstaller
if errorlevel 1 exit /b 1
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name JARVIS_NEO --additional-hooks-dir=. --hidden-import=sitecustomize assistant.py
if errorlevel 1 exit /b 1
echo.
echo Build termine : dist\JARVIS_NEO.exe
endlocal
