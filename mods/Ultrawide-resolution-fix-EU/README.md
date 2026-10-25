# XCOM: Enemy Unknown Ultrawide Fix

An ultrawide resolution fix for **XCOM: Enemy Unknown** to make it properly expand horizontally, turning it into a [Hor+](https://www.wsgf.org/article/screen-change) game.

It addresses several visual and input problems at wide aspect ratios:

- Cursor doesn't match the highlighted square on the ground.
- Camera is too zoomed in when in headquarters.
- Camera is a bit too zoomed out when on missions or main screen.
- The health bars and other hovering UI elements don't follow units.

## Install

1. Close the game.
2. Download and extract [PatcherGUI](https://www.nexusmods.com/xcom/mods/448).
3. Download and extract the EU mod file variant [Ultrawide-resolution-fix-EU.txt](https://github.com/sparqle/XComEW-Ultrawide-Fix/releases).
4. Open PatcherGUI.
5. Browse to your "XCom-Enemy-Unknown" directory. (Not "XCom-Enemy-Unknown/XEW"!)
6. Disable hash check: Menu > Tools > "Disable hash check"
7. Browse to the mod file: `Ultrawide-resolution-fix-EU.txt`
8. Click **Apply** to install.

## Tested configurations

Tested at 3440x1440 in **XCOM: Enemy Unknown**: starting missions and screens.

* Fixes are general, so should work for untested game screens as well.
* Will probably work for other ultrawide or super ultrawide resolutions.
* Game still works fine on other aspect ratios, including narrow aspect ratios such as 5:4 or 4:3.

## What was borked

See the Enemy Within mod [What was borked](../Ultrawide-resolution-fix/README.md#what-was-borked) section, both game versions
mostly share the same shortcomings. Below I describe the main additional fix required.

### Avoid patching Startup.upk

X-COM EU differs from X-COM EW in a few places:

* It requires PatcherGUI to disable hash checks
* It has Dialogue UI is in Startup.upk file (instead of UICollection_Common_SF.upk)

Unfortunately, Startup.upk is one of the files that is hash checked, but PatcherGUI doesn't disable this check.
This means that fixing the Dialogue UI in Startup.upk would require a fix in PatcherGUI or a custom executable patch.

As PatcherGUI hasn't been updated in 8 years, and including an executable in our own mod would require a manual
review by Nexus Mods, we opt for a second approach: We add the fixed Dialogue UI in its entirety into XComGame.upk,
and make its UnrealScript use that instance instead of the broken one in Startup.upk.

## License

This project's original code and documentation are available under the [MIT license](LICENSE).
UPKUtils is licensed separately under GPLv2 and is not included in the release ZIP.
The source repository retains the tools, licenses, and corresponding source in `third-party` for local use.

## Tools used

Many thanks to the following utilities that made this fix possible:

* [Nexus Mods for XCOM](https://www.nexusmods.com/games/xcom): A great collection of mods and improvements, which
  showed that this fix was possible, and tools exist to do it.
* [UPK Utils](https://github.com/wghost/UPKUtils): An amazing collection of tools for inspecting and modifying UPK files.
* [PatcherGUI](https://github.com/wghost/PatcherGUI): The GUI interface to apply UPK patches for XCOM, which inspired
  this tool's interface.
* [UE Explorer](https://github.com/UE-Explorer/UE-Explorer): For providing a way to show and search UnrealScript code
  inside UPK files.
* [JPEXS Decompiler](https://github.com/jindrapetrik/jpexs-decompiler): Used to inspect ScaleForm UI elements and to determine how to resize them.
* [Ghidra](https://github.com/nationalsecurityagency/ghidra): To decompile XCOM.exe assembly with, to find native
  functions mentioned in UPK files.
* [dbg](https://github.com/x64dbg/x64dbg): To debug XCOM.exe live with, used to track down the completely internal
  CalcSceneView() function.
* [ChatGPT](https://chatgpt.com/): Which is much better than me at translating and creating assembly code, and pretty
  great at explaining how these various tools operate.
