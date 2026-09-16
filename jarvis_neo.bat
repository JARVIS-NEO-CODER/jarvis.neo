@echo off
title J.A.R.V.I.S. NEO
cd /d "%~dp0"
echo Lancement des systemes de J.A.R.V.I.S. NEO...
python neo_runtime_launcher.py
if errorlevel 1 (
    echo.
    echo [Erreur] Le systeme s'est arrete de maniere inattendue.
    pause
)
