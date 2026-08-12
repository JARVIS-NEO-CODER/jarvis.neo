@echo off
title J.A.R.V.I.S. NEO
cd /d "%~dp0"
echo.
echo ================================================
echo       J.A.R.V.I.S. NEO - CORE + PLATFORM V4
echo ================================================
echo.
python neo_platform_v2.py
if errorlevel 1 (
    echo.
    echo [Erreur] J.A.R.V.I.S. NEO s'est arrete de maniere inattendue.
    pause
)
