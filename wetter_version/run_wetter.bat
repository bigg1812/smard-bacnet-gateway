@echo off
title Wetterprognose CSV-Exporter
cd /d "%~dp0"

echo =======================================================
echo  Wetterprognose CSV-Exporter ausfuehren...
echo =======================================================
echo.

..\venv\Scripts\python.exe src\wetter_prognose_csv.py

echo.
echo =======================================================
echo  Fertig. Beliebige Taste zum Beenden druecken.
echo =======================================================
pause > nul
