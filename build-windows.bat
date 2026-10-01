@echo off
setlocal
cmake -S "%~dp0" -B "%~dp0build\cpp" -DCMAKE_BUILD_TYPE=Release
if errorlevel 1 exit /b %errorlevel%
cmake --build "%~dp0build\cpp" --config Release
if errorlevel 1 exit /b %errorlevel%
ctest --test-dir "%~dp0build\cpp" -C Release --output-on-failure
if errorlevel 1 exit /b %errorlevel%
cmake --install "%~dp0build\cpp" --config Release --prefix "%~dp0dist"
if errorlevel 1 exit /b %errorlevel%
rem Chocolatey also provides a cpack command; use the one beside CMake.
for %%I in (cmake.exe) do set "CMAKE_EXE=%%~$PATH:I"
for %%I in ("%CMAKE_EXE%") do set "CPACK_EXE=%%~dpIcpack.exe"
"%CPACK_EXE%" --config "%~dp0build\cpp\CPackConfig.cmake" -C Release -B "%~dp0dist"
exit /b %errorlevel%
