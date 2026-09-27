# Build

To build the app from source on Windows, install Python 3 and run `build-windows.bat`. The resulting app is
`dist\XComEW-Ultrawide-Fix.exe`.

The original ultrawide monitor icon is stored in `assets/ultrawide.ico` and embedded in both the executable and the
application window. To regenerate the icon and its PNG preview, run `powershell -File tools/generate-icon.ps1`. The ICO
includes sizes from 16 to 256 pixels.
