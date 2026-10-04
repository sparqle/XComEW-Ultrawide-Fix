# Build

Version 2.0.0 is a native Windows C++17 GUI. Build with CMake 3.21+ and Ninja using
Microsoft Visual C++ (MSVC). Install Visual Studio Build Tools 2019 or newer with
Desktop development with C++ and a Windows SDK. Compiler runtimes are linked
statically; the app uses only Windows system DLLs, including the Universal CRT
supplied by Windows 10/11.

## Release

Run `build-windows.bat` from a regular command prompt; it locates Visual Studio
and loads the x64 MSVC environment automatically. CMake must be on PATH; the
script uses Ninja on PATH or the copy bundled with Visual Studio.

Alternatively, use the `native-ui` release preset from an x64 Visual Studio
developer command prompt with CMake and Ninja on PATH:

```powershell
cmake --preset native-ui
cmake --build --preset native-ui
cmake --install build/native-ui-msvc --config Release --prefix dist
$cpack = Join-Path (Split-Path (Get-Command cmake).Source) 'cpack.exe'
& $cpack --config build/native-ui-msvc/CPackConfig.cmake -C Release
```

The build produces `build/native-ui-msvc/XComEW-Ultrawide-Fix.exe`. Installation puts
it in `dist`, alongside `mods/Fix-ultrawide-UI.txt`, README and LICENSE. The release
archive is `dist/XComEW-Ultrawide-Fix-2.0.0.zip`. It contains no runtime DLLs, backups,
local settings, uninstall scripts or third-party tools. CPack packages only
explicitly installed files, excluding stale files from older builds.
CPack stages packages under `build/native-ui-msvc/packages` and copies completed ZIPs
to `dist`, keeping its `_CPack_Packages` working directory out of the release folder.

In CLion, select a Visual Studio toolchain (x64) under Settings > Build, Execution,
Deployment > Toolchains, then reload the CMake project and select the `native-ui` release profile and
run configuration. This is the only default application target. Tests are opt-in;
the old CLI, Python build and CTest dashboard targets have been removed.
The patch script is copied beside the executable so it can run from CLion.
Full UPK installation still uses separately downloaded PatcherGUI/UPKUtils tools.

## Tests

Temporarily enable tests in the same build directory:

```powershell
cmake --preset native-ui -DBUILD_TESTING=ON
cmake --build build/native-ui-msvc
ctest --test-dir build/native-ui-msvc --output-on-failure
cmake --preset native-ui
```

The final configure restores the release profile with test targets disabled.
Tests use synthetic binaries and fake UPK output without touching a game installation.
They cover signatures, multi-package staging, rollback and size sidecars, subset
restores, settings and EXE-only operations without tools. Windows tests check
argument quoting, output capture and hidden GUI startup from a folder with no DLLs.

## Application

All C++ sources, private headers, resources and tests live in `src/`.
`app.cpp` implements the Windows UI; `installer.cpp` handles the installer workflow;
`windows_support.cpp` runs external tools without console windows. Each tool has
a five-minute timeout. Operations run on a worker thread; closing the window is
blocked until the transaction finishes.

The UI has two folder rows, a resizable activity log, Install/Restore/Status buttons
and a native status bar. Advanced provides Install EXE only and Disable Phone Home.
Help contains the PatcherGUI download link and About dialog. The game directory is
saved in UTF-8 `XComEW-Ultrawide-Fix.cfg` beside the app. Discovery checks the usual
Steam folders on C: and D:.

The UPK workflow reads every `UPK_FILE` target from `mods/Fix-ultrawide-UI.txt`,
decompresses all targets into one staging directory and runs PatchUPK once.
Every target must change and an uninstall script must be generated before game
files are written. Install/restore roll back attempted writes to packages, size
sidecars and the executable on failure. Restore uses the generated uninstall
script's targets, including scripts covering only a subset of packages. EXE
restore reverses known instruction blocks while retaining unrelated edits.

The version in `CMakeLists.txt` drives the window title, executable metadata,
manifest and ZIP name. The monitor icon in `assets/ultrawide.ico` is embedded
in the executable. Regenerate it and its PNG preview with
`powershell -File tools/generate-icon.ps1`; the ICO includes sizes from 16 to 256 pixels.
