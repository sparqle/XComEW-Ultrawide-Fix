@echo off
setlocal
cd /d "%~dp0"
py -3 -m pip install --user pyinstaller
if errorlevel 1 exit /b 1
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name XComEW-Ultrawide-Fix --add-data "Fix-ultrawide-HPBars.txt;." --add-data "Fix-ultrawide-HPBars.txt.uninstall.txt;." ultrawide_app.py
if errorlevel 1 exit /b 1
echo Built dist\XComEW-Ultrawide-Fix.exe
echo Place DecompressLZO.exe and PatchUPK.exe in dist\binaries\ or select their folder in the app.
