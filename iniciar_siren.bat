@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

rem Versao "sem console" - o SIREN roda em segundo plano (pythonw), sem janela de
rem terminal nenhuma (mesmo padrao do iniciar_echo.bat/iniciar_iris.bat). A janela
rem do player (Leve ou Completo, ver data/config.json::modo_ui) abre normalmente -
rem pythonw so esconde o CONSOLE, nunca a interface grafica em si.

start "" /B ".venv\Scripts\pythonw.exe" -m siren.main
