# XCOM: Enemy Within Ultrawide Fix

An ultrawide resolution fix for **XCOM: Enemy Within** and **Long War** to make it properly expand horizontally, turning it into a [Hor+](https://www.wsgf.org/article/screen-change) game.

It addresses several visual and input problems at wide aspect ratios:

- Cursor doesn't match the highlighted square on the ground.
- Camera is too zoomed in when in headquarters.
- Camera is a bit too zoomed out when on missions or main screen.
- The health bars and other hovering UI elements don't follow units.

The fix modifies `XComEW.exe` for the camera and mouse/ground selection, and `XComGame.upk` for the health bars.

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

If **UPK tools folder** is blank, the app checks the `third_party` directory beside the executable
(or in the repository root when running from source), then its `Binaries` subdirectory. Both executables must be together in one of these directories.

It will binary patch `XComEW.exe` and use the PatchUPK from [UPKUtils](https://github.com/wghost/UPKUtils) to modify
`XComGame.upk`.

## Restore

If you want to restore the original game files after an installation. Or you can use Steam to restore the game files 
to their original state.

1. Close the game.
2. Run `XComEW-Ultrawide-Fix.exe` and choose your `XCom-Enemy-Unknown` folder you previously installed in.
5. Set **UPK tools folder** to the extracted PatcherGUI directory.
4. Click **Restore** to restore.

This will restore the original `XComEW.exe` that was backed up in the `backups` directory, checking whether the binary was changed in the meantime. It will also use an uninstall patch to restore the health
bar modification in `XComGame.upk`. 

You can also **force a restore**, which will use the last backup and ignore any checks on whether the binary was changed in the meantime.

## Tested configurations

Tested at 3440x1440 in **XCOM: Enemy Within** and **Long War**, starting missions and screens.

* Fixes are general, so should work for untested game screens as well.
* Will probably work for other ultrawide or super ultrawide resolutions.
* XCOM: Enemy Unknown not supported
* Game still works fine on 16:9 resolutions.
* Game will not work well on narrower aspect ratios such as 5:4 or 4:3.

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

Additionally, FOV adjustments are now always applied. The maps `Command1`, `CIN_LoadScreen`, and `CIN_HQLoadScreen` are no
longer excluded.

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
