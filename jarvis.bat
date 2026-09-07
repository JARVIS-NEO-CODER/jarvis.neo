@echo off
title J.A.R.V.I.S. NEO
cd /d "%~dp0"
set "JARVIS_REMOTE_RELAY_URL=wss://jarvis-neo-relay.onrender.com"
echo.
echo ================================================
echo       J.A.R.V.I.S. NEO - NEO COMMAND CENTER
echo ================================================
echo.
python jarvis_launcher.py
if errorlevel 1 (
    echo.
    echo [Erreur] J.A.R.V.I.S. NEO s'est arrete de maniere inattendue.
    pause
)
