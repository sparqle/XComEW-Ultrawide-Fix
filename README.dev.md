# Build

## Native C++ application

The C++17 application includes a native Windows GUI, game folder discovery and
portable settings, EXE patching, and the full UPK install/restore workflow. It uses
Windows system APIs and does not require Python or a GUI framework. UPK tools must
still be downloaded separately. The EXE-only command-line patcher is also built.

With CMake 3.20+ and a C++17 compiler (MSVC or MinGW on Windows):

```powershell
cmake -S . -B build/cpp
cmake --build build/cpp --config Release
ctest --test-dir build/cpp -C Release --output-on-failure
cmake --install build/cpp --config Release --prefix dist
$cpack = Join-Path (Split-Path (Get-Command cmake).Source) 'cpack.exe'
& $cpack --config build/cpp/CPackConfig.cmake -C Release -B dist
```

Open the root `CMakeLists.txt` in CLion to use its configured C++ toolchain.
The GUI is `build/cpp/XComEW-Ultrawide-Fix.exe` (or inside `Release` with MSVC).
The build copies the patch script to a `mods` directory beside the GUI, so it can
also run directly from CLion. Installation places the same files in `dist`.
The GUI and CLI link the compiler runtimes statically (MinGW or MSVC `/MT`), so
no runtime DLLs need to be distributed alongside them. They still use Windows
system DLLs, including the Universal CRT supplied by Windows 10/11. The patch
script remains in `mods`, and full UPK installation still uses the separately
downloaded PatcherGUI/UPKUtils tools.

`build-windows.bat` runs this native build, tests, installation, and packaging.
The release ZIP contains only explicitly installed files, excluding local settings,
uninstall scripts, backups, Python code, and third-party tools. CPack does not zip
arbitrary files left in `dist` by older builds.

All C++ sources, private headers, Windows resources, and tests live under `cpp/`.
`installer.cpp` implements the workflow independently of the UI; `app.cpp` contains
the Windows interface, and `windows_support.cpp` runs the external tools without
opening console windows. Tool output is captured and failures reported; each tool
has a five-minute timeout. Operations run on a worker thread, and closing the
window is blocked until the transaction finishes.

The GUI provides Install, Restore, Status, Install EXE only, and Disable Phone Home.
Its compact Windows layout has two folder rows, a resizable activity log, and
Install/Restore/Status buttons on the right. EXE-only actions are in the Advanced
menu; the PatcherGUI download link and About dialog are in Help. Controls use the
Windows system font and display scaling, with progress shown in a native status bar.
It saves the game folder in the same UTF-8 `XComEW-Ultrawide-Fix.cfg` used by the
Python app. Discovery checks the same usual Steam folders on C: and D:.
The CLI still accepts an explicit EXE path and reports signature status without
SHA-256 output.

```powershell
build/cpp/xcomew-patcher.exe "C:/Games/XCom-Enemy-Unknown/XEW/Binaries/Win32/XComEW.exe" --status
build/cpp/xcomew-patcher.exe "C:/Games/XCom-Enemy-Unknown/XEW/Binaries/Win32/XComEW.exe" --dry-run
build/cpp/xcomew-patcher.exe "C:/Games/XCom-Enemy-Unknown/XEW/Binaries/Win32/XComEW.exe"
build/cpp/xcomew-patcher.exe "C:/Games/XCom-Enemy-Unknown/XEW/Binaries/Win32/XComEW.exe" --restore
build/cpp/xcomew-patcher.exe "C:/Games/XCom-Enemy-Unknown/XEW/Binaries/Win32/XComEW.exe" --disable-phone-home
```

The CLI's default operation installs only the native executable patches. Each write
keeps the first `.bak`, replaces through a flushed temporary file beside the EXE,
and verifies the written bytes. Restore reverses known blocks while retaining
unrelated modifications. `--dry-run` validates without writing or creating backups.
The native tests use synthetic binaries and fake UPK tool output and never touch
a game installation. They cover multi-package staging, unchanged-package and
missing-undo rejection, rollback, sidecars, subset restores, settings, and EXE-only
operations without UPK tools.
Windows-specific tests also exercise tool argument quoting and output capture,
and start and close a hidden GUI instance from a folder containing no DLLs,
without running a game operation.

## Legacy Python application

The Python implementation remains available as a reference during migration.
Run `python src/app.py` from the source tree. Its older PyInstaller build is still
available through `python build.py` with `requirements-build.txt` installed;
`build-windows.bat` now builds the native app. Both builds use the same executable
name in `dist`, so build the version you intend to use last.
The IDE run configuration named `Build legacy Python executable` invokes this older build.

The legacy build also creates a versioned release ZIP in `dist`. It excludes `third_party`, including any copies
left in `dist` by older builds. The source tree keeps that directory for local use. Release users must
download PatcherGUI or UPKUtils separately and select the folder containing both tools in the UI.

Both implementations read every `UPK_FILE` target from `mods/Fix-ultrawide-UI.txt`, decompress all
targets into one temporary directory, and run PatchUPK once against that directory. The native
installer requires every target to change before any game file is written. Install and restore roll back all written packages,
their size sidecars, and the executable on failure. Restore reads its targets from the generated
uninstall script, so it also supports uninstall scripts that target only a subset of the packages.

The original ultrawide monitor icon is stored in `assets/ultrawide.ico` and embedded in both the executable and the
application window. To regenerate the icon and its PNG preview, run `powershell -File tools/generate-icon.ps1`. The ICO
includes sizes from 16 to 256 pixels.
