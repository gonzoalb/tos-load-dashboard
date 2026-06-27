@echo off
REM === TOS Dashboard Quick Refresh ===
REM Double-click this after downloading FMC CSV
powershell -ExecutionPolicy Bypass -File "%~dp0refresh_data.ps1"
