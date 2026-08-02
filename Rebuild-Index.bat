@echo off
rem Double-click launcher for the Recoll Next semantic index rebuilder.
rem Runs the Tk GUI with no console window using the project's own virtual environment.
setlocal
set "ROOT=%~dp0"
start "" "%ROOT%.venv\Scripts\pythonw.exe" "%ROOT%src\semantic\recoll_ai_index_builder.py" %*
