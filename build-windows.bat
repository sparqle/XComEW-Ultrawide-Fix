@echo off
setlocal
cd /d "%~dp0"
rem Locate MSVC and load its compiler, linker and Windows SDK environment.
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%VSWHERE%" (
    echo Microsoft Visual Studio Build Tools with Desktop development with C++ is required.
    exit /b 1
)
set "VSINSTALL="
for /f "usebackq tokens=*" %%I in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VSINSTALL=%%I"
if not defined VSINSTALL (
    echo No Microsoft C++ toolchain found. Install Desktop development with C++.
    exit /b 1
)
call "%VSINSTALL%\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64
if errorlevel 1 exit /b %errorlevel%
rem Use Visual Studio's bundled Ninja if it is not already on PATH.
where ninja.exe >nul 2>nul
if errorlevel 1 set "PATH=%VSINSTALL%\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%"
cmake --preset native-ui
if errorlevel 1 exit /b %errorlevel%
cmake --build --preset native-ui
if errorlevel 1 exit /b %errorlevel%
cmake --install "%~dp0build\native-ui-msvc" --config Release --prefix "%~dp0dist"
if errorlevel 1 exit /b %errorlevel%
rem Chocolatey also provides a cpack command; use the one beside CMake.
for %%I in (cmake.exe) do set "CMAKE_EXE=%%~$PATH:I"
for %%I in ("%CMAKE_EXE%") do set "CPACK_EXE=%%~dpIcpack.exe"
"%CPACK_EXE%" --config "%~dp0build\native-ui-msvc\CPackConfig.cmake" -C Release
exit /b %errorlevel%
