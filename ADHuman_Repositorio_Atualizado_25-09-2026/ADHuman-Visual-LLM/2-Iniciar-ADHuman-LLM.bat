@echo off
cd /d "%~dp0backend"
powershell.exe -NoProfile -ExecutionPolicy Bypass -NoExit -File ".\start-windows.ps1"
