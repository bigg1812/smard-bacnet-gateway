@echo off
title SMARD Strompreis CSV-Exporter
cd /d "%~dp0"

echo =======================================================
echo  SMARD Strompreis CSV-Exporter ausfuehren...
echo =======================================================
echo.

python src\strompreis_csv.py

echo.
echo =======================================================
echo  Fertig. Beliebige Taste zum Beenden druecken.
echo =======================================================
pause > nul
