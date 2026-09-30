# Build

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
