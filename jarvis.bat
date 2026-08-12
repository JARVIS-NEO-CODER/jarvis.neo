@echo off
title J.A.R.V.I.S. NEO
cd /d "%~dp0"
echo.
echo ================================================
echo       J.A.R.V.I.S. NEO - CORE + PLATFORM
echo ================================================
echo.
python neo_platform.py
if errorlevel 1 (
    echo.
    echo [Erreur] J.A.R.V.I.S. NEO s'est arrete de maniere inattendue.
    pause
)
