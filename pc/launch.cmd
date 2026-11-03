@echo off
setlocal
cd /d "%~dp0"
py -3 app.py
if errorlevel 1 (
  echo Launch failed. Install Python 3.9 or newer with Tcl/Tk and the Python launcher.
  pause
)
