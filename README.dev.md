# Build

## C++ migration

The initial C++17 port builds a standalone EXE-only command-line patcher with
no Python runtime or external libraries. The Python GUI remains the full installer
while its UI, game discovery/settings, UPK staging/rollback, and release packaging
are still to be ported. SHA-256 reporting and automatic EXE discovery are also pending.

With CMake 3.20+ and a C++17 compiler (MSVC or MinGW on Windows):

```powershell
cmake -S . -B build/cpp
cmake --build build/cpp --config Release
ctest --test-dir build/cpp -C Release --output-on-failure
```

Open the root `CMakeLists.txt` in CLion to use its configured C++ toolchain.
The executable is `build/cpp/xcomew-patcher.exe` (or inside `Release` with MSVC).
For MinGW builds, keep the compiler's `bin` folder on `PATH` when running the
application/tests, or distribute its required runtime DLLs beside the executable.

```powershell
build/cpp/xcomew-patcher.exe "C:/Games/XCom-Enemy-Unknown/XEW/Binaries/Win32/XComEW.exe" --status
build/cpp/xcomew-patcher.exe "C:/Games/XCom-Enemy-Unknown/XEW/Binaries/Win32/XComEW.exe" --dry-run
build/cpp/xcomew-patcher.exe "C:/Games/XCom-Enemy-Unknown/XEW/Binaries/Win32/XComEW.exe"
build/cpp/xcomew-patcher.exe "C:/Games/XCom-Enemy-Unknown/XEW/Binaries/Win32/XComEW.exe" --restore
build/cpp/xcomew-patcher.exe "C:/Games/XCom-Enemy-Unknown/XEW/Binaries/Win32/XComEW.exe" --disable-phone-home
```

The default operation installs only the native executable patches. Each write
keeps the first `.bak`, replaces through a flushed temporary file beside the EXE,
and verifies the written bytes. Restore reverses known blocks while retaining
unrelated modifications. `--dry-run` validates without writing or creating backups.
The native tests use synthetic binaries and never touch a game installation.

## Python application

To build the app from source on Windows, install Python 3 and run `build-windows.bat`. The resulting app is
`dist\XComEW-Ultrawide-Fix.exe`.

The build also creates a versioned release ZIP in `dist`. It excludes `third_party`, including any copies
left in `dist` by older builds. The source tree keeps that directory for local use. Release users must
download PatcherGUI or UPKUtils separately and select the folder containing both tools in the UI.

The UPK workflow reads every `UPK_FILE` target from `mods/Fix-ultrawide-UI.txt`, decompresses all
targets into one temporary directory, and runs PatchUPK once against that directory. Every target
must change before any game file is written. Install and restore roll back all written packages,
their size sidecars, and the executable on failure. Restore reads its targets from the generated
uninstall script, so it also supports uninstall scripts that target only a subset of the packages.

The original ultrawide monitor icon is stored in `assets/ultrawide.ico` and embedded in both the executable and the
application window. To regenerate the icon and its PNG preview, run `powershell -File tools/generate-icon.ps1`. The ICO
includes sizes from 16 to 256 pixels.
