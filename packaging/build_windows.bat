@echo off
REM Builds a standalone Windows build of the game (no Python/pygame install
REM required to run it) using PyInstaller. Output: build\dist\SpaceGame\SpaceGame.exe
REM Can be run from anywhere - it always operates against the repo root
REM (this script's parent directory), which is also where the output lands.

pushd "%~dp0.."

pip show pyinstaller >nul 2>nul
if errorlevel 1 (
    echo Installing pyinstaller...
    pip install -r packaging\requirements-dev.txt
)

rmdir /s /q build 2>nul

REM --onedir, not --onefile: onefile's two-process bootloader handoff can
REM silently fail to launch under --windowed depending on how the exe is
REM invoked (confirmed while setting this up - the app never opened a
REM window, with no error, since --windowed has no console to show one).
REM onedir is a single real process and doesn't have that failure mode.
python -m PyInstaller --onedir --windowed --name SpaceGame --distpath build\dist --workpath build\pyinstaller --specpath build\pyinstaller main.py

xcopy /e /i /y config build\dist\SpaceGame\config >nul
REM Design reference (HTML atlases under config\stories\*\atlases) is not
REM runtime config - keep it out of the shipped build.
for /d /r build\dist\SpaceGame\config %%d in (atlases) do rmdir /s /q "%%d" 2>nul

echo.
echo Build complete: build\dist\SpaceGame\SpaceGame.exe
echo Ship the whole build\dist\SpaceGame folder - the exe needs config\ next to it.

popd
