@echo off
rem Double-click to open the graphics-pipeline vertex editor - no terminal needed.
rem Starts the local dev server (config\serve_nocache.py) minimized in the
rem background if one isn't already running on port 8777, then opens the editor
rem in your default browser. Safe to double-click again later - if the server's
rem already up, the new one just fails to bind and exits; the browser still
rem opens against the existing one.
rem
rem Served this way, "save checked to repo" in the editor works in any browser
rem (the server writes the files). Opening config\editor.html straight from
rem disk also works, but save then needs Chrome/Edge (File System Access API).
setlocal
cd /d "%~dp0.."
start "graphics pipeline editor server" /min python config\serve_nocache.py 8777
timeout /t 1 /nobreak >nul
start "" "http://127.0.0.1:8777/config/editor.html"
