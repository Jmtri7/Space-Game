@echo off
rem Double-click this to open the vertex editor without touching a terminal.
rem Starts the no-cache local server (docs/atlases/serve_nocache.py) minimized
rem in the background if one isn't already running on port 8777, then opens
rem the editor in your default browser. Safe to double-click again later -
rem if the server's already up, the new one just fails to bind and exits;
rem the browser still opens against the existing one.
setlocal
cd /d "%~dp0..\.."
start "graphics pipeline editor server" /min python docs\atlases\serve_nocache.py 8777
timeout /t 1 /nobreak >nul
start "" "http://127.0.0.1:8777/docs/atlases/editor.html"
