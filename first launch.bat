@echo off
title J.A.R.V.I.S. NEO - First Launch
cd /d "%~dp0"

echo.
echo ================================================
echo       J.A.R.V.I.S. NEO - FIRST LAUNCH
echo ================================================
echo.

echo [1/2] Installation / mise a jour des dependances...
echo.
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERREUR] L'installation des dependances a echoue.
    echo Verifiez que Python est installe et accessible avec la commande python.
    pause
    exit /b 1
)

echo.
echo [OK] Dependances installees.
echo.
echo [2/2] Lancement de J.A.R.V.I.S. NEO...
echo.
call "%~dp0jarvis.bat"
