@echo off
REM Development placeholder for sidecar-server
REM This script launches the Python sidecar directly during development
cd /d "%~dp0..\..\sidecar\src"
python server.py %*
