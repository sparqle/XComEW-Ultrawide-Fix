@echo off
setlocal
cd /d "%~dp0"
cmake --preset native-ui
if errorlevel 1 exit /b %errorlevel%
cmake --build --preset native-ui
if errorlevel 1 exit /b %errorlevel%
cmake --install "%~dp0build\native-ui" --config Release --prefix "%~dp0dist"
if errorlevel 1 exit /b %errorlevel%
rem Chocolatey also provides a cpack command; use the one beside CMake.
for %%I in (cmake.exe) do set "CMAKE_EXE=%%~$PATH:I"
for %%I in ("%CMAKE_EXE%") do set "CPACK_EXE=%%~dpIcpack.exe"
"%CPACK_EXE%" --config "%~dp0build\native-ui\CPackConfig.cmake" -C Release
exit /b %errorlevel%
