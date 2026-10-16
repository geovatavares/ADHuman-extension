@echo off
cd /d "%~dp0backend"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\setup-windows.ps1"
pause
