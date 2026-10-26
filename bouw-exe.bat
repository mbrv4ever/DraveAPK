@echo off
rem === bouw-exe.bat - bouwt dist\DraveAPK\DraveAPK.exe (met foutcontrole) ===
setlocal
cd /d "%~dp0"
set PY=
for %%V in (3.13 3.12 3.11 3.10) do (
  if not defined PY ( py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V" )
)
if not defined PY ( py -3 -c "import sys" >nul 2>&1 && set "PY=py -3" )
if not defined PY ( python -c "import sys" >nul 2>&1 && set "PY=python" )
if not defined PY ( echo FOUT: geen Python gevonden. & pause & exit /b 1 )
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv
  if errorlevel 1 ( echo FOUT: virtuele omgeving maken mislukt. & pause & exit /b 1 )
)
set "VPY=%~dp0.venv\Scripts\python.exe"
"%VPY%" -m pip install --upgrade pip
"%VPY%" -m pip install -r requirements.txt
if errorlevel 1 ( echo FOUT: pakketten installeren mislukt. & pause & exit /b 1 )
"%VPY%" -m pip install pyinstaller
if errorlevel 1 ( echo FOUT: PyInstaller installeren mislukt. & pause & exit /b 1 )
echo.
echo === Bouwen met PyInstaller... ===
if exist "dist\DraveAPK\DraveAPK.exe" del /q "dist\DraveAPK\DraveAPK.exe"
"%VPY%" -m PyInstaller --noconfirm draveapk.spec
if errorlevel 1 ( echo. & echo FOUT: PyInstaller gaf een fout. Zie de meldingen hierboven. & pause & exit /b 1 )
if not exist "dist\DraveAPK\DraveAPK.exe" ( echo. & echo FOUT: dist\DraveAPK\DraveAPK.exe is niet gemaakt. & pause & exit /b 1 )
echo.
echo KLAAR: dist\DraveAPK\DraveAPK.exe
pause
endlocal