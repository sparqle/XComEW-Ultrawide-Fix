# XCOM: Enemy Within Ultrawide Fix

> [!IMPORTANT]
> The application `XComEW-Ultrawide-Fix.exe` is no longer necessary. 
> The complete ultrawide fix can now be installed using [PatcherGUI](https://www.nexusmods.com/xcom/mods/448) with just the file
> [`mods/Ultrawide-resolution-fix.txt`](mods/Ultrawide-resolution-fix.txt). 
>
> Together, these replace all ultrawide modifications performed by this executable, without needing to modify `XComEW.exe`.

An ultrawide resolution fix for **XCOM: Enemy Within** and **Long War** to make it properly expand horizontally, turning it into a [Hor+](https://www.wsgf.org/article/screen-change) game.

It addresses several visual and input problems at wide aspect ratios:

- Cursor doesn't match the highlighted square on the ground.
- Camera is too zoomed in when in headquarters.
- Camera is a bit too zoomed out when on missions or main screen.
- The health bars and other hovering UI elements don't follow units.

The fix modifies `XComEW.exe` for the camera and mouse/ground selection, and patches several UPK files for additional UI fixes.

## Install (PatchGUI)

1. Close the game.
2. Download and extract [PatcherGUI](https://www.nexusmods.com/xcom/mods/448).
3. Download mode file: [`mods/Ultrawide-resolution-fix.txt`](mods/Ultrawide-resolution-fix.txt).
4. Open PatcherGUI.
5. Browse to your "XCom-Enemy-Unknown/XEW" directory.
6. Browse to the mod file: `Ultrawide-resolution-fix.txt`
7. Click **Apply** to install.

## Install (legacy)

> The legacy executable installation and restoration instructions below are retained for posterity.

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

## Tested configurations

Tested at 3440x1440 in **XCOM: Enemy Within** and **Long War**, starting missions and screens.

* Fixes are general, so should work for untested game screens as well.
* Will probably work for other ultrawide or super ultrawide resolutions.
* XCOM: Enemy Unknown not supported
* Game still works fine on 16:9 resolutions.
* Game will not work well on narrower aspect ratios such as 5:4 or 4:3.

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

## What was borked

X-Com EW has limited to no support for ultrawide resolutions. Aspect ratio logic that exists targets resolutions with
aspect ratios narrower than 16:9, such as 5:4 and 4:3.

### UI to Screen mapping

Internally the Scaleform/Flash UI uses a fixed and normalized coordinate system of 1280x720 (16:9 aspect ratio). The
game converts between these UI coordinates and normal Unreal Engine screen coordinates using two mapping functions.

There is a native function which is used to map your UI mouse position to the square or enemy unit underneath the
cursor:
```
class XComInputBase

// Export UXComInputBase::execConvertUIPointToScreenCoordinate(FFrame&, void* const)
native simulated function Vector2D ConvertUIPointToScreenCoordinate(Vector2D kPoint);
```

There is also a native function that does the reverse, but it isn't actually used by the game. Instead this reverse
mapping is done in UnrealScript code, and it is used to place UI elements such as health bars next to units:

```
class UIFxsMovie

simulated function Vector2D ConvertNormalizedUICoordsToScreenCoords(float X, float Y)
```
*(The name of this function is actually quite confusing, it should have been named
ConvertScreenCoordsToNormalizedUICoords)*

The Scaleform/Flash UI applies a scale-to-fit on either width or height, depending on the aspect ratio.
But the mapping functions assume it will always be scaled-to-fit on width. In the case of ultrawide resolutions, the
UI uses scaled-to-fit on height, leading to the discrepancy. 

The UI resolution also remains centered on 640 (1280 / 2), meaning that the X coordinate operates in the range -220 to 1500
when using a resolution of 3440x1440.

The patch changes the two mapping functions to assume the UI resolution is scaled-to-fit on height, and centered on 640.

**Executable implementation:** We patch the native UXComInputBase::execConvertUIPointToScreenCoordinate() function directly. 

**PatchUPK implementation:** We patch XComInputBase.ConvertUIPointToScreenCoordinate by modifying the UPK metadata bits
to turn the native function into an UnrealScript function. We also retain support for the sub-16:9 aspect ratio.

### Camera FOV aspect ratio adjustments

The FOV value determines how "zoomed in" the camera is.
However, in ultrawide resolutions the camera is sometimes too zoomed in (Headquarters and dropship loading screens),
and sometimes a bit too zoomed out (missions, and main menu screen).

A modified version of the native Unreal Engine function `ULocalPlayer::CalcSceneView()` is responsible for the final
FOV calculations. But this function was lacking proper support for adjusting the FOV based on the aspect ratio:

* It never applies any FOV adjustments in maps `Command1`, `CIN_LoadScreen`, and `CIN_HQLoadScreen`. This includes
  both the headquarters and dropship loading screens.
  This means that the camera effectively "chops off" the top and bottom of the screens in ultrawide resolutions,
  resulting in a [Vert-](https://www.wsgf.org/article/screen-change) game. 
* In other maps it does apply a linear FOV adjustment based on the aspect ratio, which is not actually the proper
  algorithm to keep the FOV the same vertically, leading to a visual zoom out.

This function was patched from the linear algorithm:
  ```
  halfFOV *= (width / height) * 0.5625
  ```
  To a trigonometric FOV calculation:
  ```
  halfFOV = atan(tan(halfFOV) * ((width / height) * 0.5625))
  ```

**Executable implementation:** We patch ULocalPlayer::CalcSceneView() directly to update the FOV calculation. Additionally, 
we disable the map exclusion branches directly.

**PatchUPK implementation:** We patch Camera.DoUpdateCamera in `Engine.upk`, modifying the FOV just before `FillCameraCache(NewPOV)` is called. 
This is the closest UnrealScript 
function before we dive into compiled code. Because the original linear algorithm is still applied, we compensate for it in our logic.
We also compensate for the map exclusions as we cannot disable them outright. We also retain support for the sub-16:9 aspect ratio.


### Smaller UI fixes

A few UI elements were no longer positioned quite right in ultrawide resolutions, and have been adjusted to be more aesthetically pleasing:

* Dialogue window popup wasn't centered.
* The Headquarters top menu bar didn't extend all the way across.
* The Headquarters top menu bar wasn't immediately anchored to the right.

## License

This project's original code and documentation are available under the [MIT license](LICENSE).
UPKUtils is licensed separately under GPLv2 and is not included in the release ZIP.
The source repository retains the tools, licenses, and corresponding source in `third_party` for local use.

## Tools used

Many thanks to the following utilities that made this fix possible:

* [Nexus mods for XCOM](https://www.nexusmods.com/games/xcom): A great collection of mods and improvements, which
  showed that this fix was possible, and tools exist to do it.
* [UPK Utils](https://github.com/wghost/UPKUtils): A great collection of tools for inspecting and modifying UPK files.
* [GUI Patcher](https://github.com/wghost/GUIPatcher): The GUI interface to apply UPK patches for XCOM, which inspired
  this tool's interface.
* [UE Explorer](https://github.com/UE-Explorer/UE-Explorer): For providing a way to show and search UnrealScript code
  inside UPK files.
* [Ghidra](https://github.com/nationalsecurityagency/ghidra): To decompile XCOM.exe assembly with, to find native
  functions mentioned in UPK files.
* [dbg](https://github.com/x64dbg/x64dbg): To debug XCOM.exe live with, used to track down the completely internal
  CalcSceneView() function.
* [ChatGPT](https://chatgpt.com/): Which is much better than me at translating and creating assembly code, and pretty
  great at explaining how these various tools operate.
