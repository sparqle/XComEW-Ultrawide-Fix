# XCOM: Enemy Within Ultrawide Fix (executable patcher)

> [!IMPORTANT]
> The application `XComEW-Ultrawide-Fix.exe` is no longer necessary. 
> The complete ultrawide fix can now be installed using [PatcherGUI](https://www.nexusmods.com/xcom/mods/448) with just the file
>  [Ultrawide-resolution-fix.txt](https://github.com/sparqle/XComEW-Ultrawide-Fix/releases). 
>
> Together, these replace all ultrawide modifications performed by this executable, without needing to modify `XComEW.exe`.
>
> The legacy executable installation and restoration instructions below are retained for posterity.

## Install 

The installer will try to find your XCOM installation folder in the usual places. If it cannot find it, you need to 
browse to your "XCom-Enemy-Unknown" directory (not the XEW directory inside it).

1. Close the game.
2. Extract the entire archive into a directory.
3. Download and extract [PatcherGUI](https://www.nexusmods.com/xcom/mods/448) separately if you haven't already. 
4. Run `XComEW-Ultrawide-Fix.exe` 
5. Enter your `XCom-Enemy-Unknown` installation folder if needed.
5. Set **UPK tools folder** to the extracted PatcherGUI directory.
6. Click **Install** to install.

It will binary patch `XComEW.exe` and use the PatchUPK from [UPKUtils](https://github.com/wghost/UPKUtils) to modify
various UPK.

## Restore

If you want to restore the original game files after an installation. Or you can use Steam to restore the game files 
to their original state.

1. Close the game.
2. Run `XComEW-Ultrawide-Fix.exe` and choose your `XCom-Enemy-Unknown` folder you previously installed in.
5. Set **UPK tools folder** to the extracted PatcherGUI directory.
4. Click **Restore** to restore.

Restore reverses the binary patch of `XComEW.exe`, and will use PatchUPK to uninstall the earlier modified UPK files.

## Advanced menu

**Advanced → Install EXE only**.
This backs up and patches `XComEW.exe`, leaving UPK files unchanged. PatcherGUI and
the **UPK tools folder** are not required for this option; This is useful if you want to manage these patches yourself in PatcherGUI.

**Advanced → Restore EXE only**.
Reverse the ultrawide patches in `XComEW.exe`, preserving unrelated executable edits.
UPK files and their uninstall script are retained. No UPK tools are required.

**Advanced → Disable Phone Home**.
Replace the executable's `firaxis.com` or PatcherGUI's `yiraxis.com` address with `xcm.invalid`. 
Because guess what? yiraxis.com exists nowadays. Unlike an unregistered `.com`, `.invalid` is 
[reserved for invalid domain names](https://www.rfc-editor.org/rfc/rfc2606).
This option requires no UPK tools and leaves UPK files unchanged.