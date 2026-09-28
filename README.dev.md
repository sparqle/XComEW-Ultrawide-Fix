# Build

To build the app from source on Windows, install Python 3 and run `build-windows.bat`. The resulting app is
`dist\XComEW-Ultrawide-Fix.exe`.

The build also creates a versioned release ZIP in `dist`. It excludes `third_party`, including any copies
left in `dist` by older builds. The source tree keeps that directory for local use. Release users must
download PatcherGUI or UPKUtils separately and select the folder containing both tools in the UI.

The original ultrawide monitor icon is stored in `assets/ultrawide.ico` and embedded in both the executable and the
application window. To regenerate the icon and its PNG preview, run `powershell -File tools/generate-icon.ps1`. The ICO
includes sizes from 16 to 256 pixels.
