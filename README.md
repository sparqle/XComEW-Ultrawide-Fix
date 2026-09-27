# XCOM: Enemy Within Ultrawide Fix

An ultrawide fix for **XCOM: Enemy Within** and **Long War**. It addresses visual and input problems at wide aspect ratios:

- Cursor doesn't match the highlighted square on the ground.
- Camera is too zoomed in when in headquarters.
- Camera is a bit too zoomed out when on missions or main screen.
- The Health bars and other hovering UI elements don't follow units.

The fix modifies `XComEW.exe` for the camera and mouse/ground selection, and `XComGame.upk` for the health bars.

## Tested configurations

Tested at 3440x1440 in **XCOM: Enemy Within** and **Long War**, starting missions and screens. 

* Fixes are general, so should work for untested game screens as well.
* Will probably work for other ultrawide or super ultrawide resolutions. 
* XCOM: Enemy Unknown not supported
* Game still works fine on 16:9 resolutions. 
* Game will not work on narrower aspect ratios such as 5:4 or 4:3.
 
## Install

Find your XCOM installation folder, for example `C:\Program Files (x86)\Steam\steamapps\common\XCom-Enemy-Unknown`.

1. Close the game.
2. Run `XComEW-Ultrawide-Fix.exe` and enter your `XCom-Enemy-Unknown` installation folder. NB: Select the main game folder, not the `XEW` folder inside it.
3. Click **Install** to install.

It will binary patch `XComEW.exe` and use the PatchUPK from [UPKUtils](https://github.com/wghost/UPKUtils) to modify `XComGame.upk`.

## Restore

If you want to restore the original game files after an installation.

1. Close the game.
2. Run `XComEW-Ultrawide-Fix.exe` and choose your **`XCom-Enemy-Unknown`** folder you previously installed in. 
3. Click **Restore** to restore.

The will restore old `XComEW.exe` was backed up to `XComEW.exe.ultrawide-complete-backup-YYYYMMDD-HHIISS.exe`. Will also use an uninstall patch to restore the health bar modification in `XComGame.upk`.

## What was borked

X-Com EW has limited to no support for ultrawide resolutions. Aspect ratio logic that exists targets resolutions with 
aspect ratios narrower than 16:9, such as 5:4 and 4:3. 

### UI to Screen mapping

Internally the Scaleform/Flash UI uses a fixed and normalized coordinate system of 1280x720 (16:9 aspect ratio). The game converts between these UI coordinates 
and normal Unreal Engine screen coordinates. 

However in ultrawide resolutions, this UI resolution isn't stretched or expanded, 
instead it is centered and scaled to fit vertically. For example, in the resolution 3440x1440 the X coordinate operates in the range -220 to 1500. This is 1280 centered (220 <- 1280 -> 220). 

There is a native function function which is used to map your UI mouse position to the square or enemy unit underneath the cursor:
```
class XComInputBase

// Export UXComInputBase::execConvertUIPointToScreenCoordinate(FFrame&, void* const)
native simulated function Vector2D ConvertUIPointToScreenCoordinate(Vector2D kPoint);
```

Additionally, there is also mapping done in UnrealScript code, which is used to position 2D elements that are not part of 
the normalized UI, such as unit health bars:

```
class UIFxsMovie

simulated function Vector2D ConvertNormalizedUICoordsToScreenCoords(float X, float Y)
```

The Scaleform/Flash UI applies a scale-to-fit on either width or height, depending on the aspect ratio.
But the mapping function assumed it would always be scale-to-fit on width. But in the case of ultrawide resolutions, the UI uses scale-to-fit on height, leading to the discrepancy.

The patch effectively changes this logic such that the scale-to-fit on height is always used.



### Camera FOV aspect ratio adjustments

The FOV value determines how "zoomed in" the camera is. 
However, in ultrawide resolutions the camera is sometimes too zoomed in (Headquarters and dropship loading screens), 
and sometimes a bit too zoomed out (missions, and main menu screen).

The modified version of the native Unreal Engine function `ULocalPlayer::CalcSceneView()` is responsible for the final FOV caclulations. But this function was lacking proper support for adjusting the FOV based on the aspect ratio:

* It never applies any FOV adjustments in maps `Command1`, `CIN_LoadScreen`, and `CIN_HQLoadScreen`. This includes both the headquarters and dropship loading screens.
  This means that the camera effectively "chops off" the top and bottom of the screens in ultrawide resolutions, appearing zoomed in.
* In other maps it does apply a linear FOV adjustment based on the aspect ratio, which is not actually the proper algoritm to keep the FOV the same.

This function was patched from the linear algorithm:
  ```
  halfFOV *= (width / height) * 0.5625
  ```
  To a logarithmic FOV calculation: 
  ```
  halfFOV = atan(tan(halfFOV) * ((width / height) * 0.5625))
  ```

Additionally, FOV adjustments are always applied, the maps `Command1`, `CIN_LoadScreen`, and `CIN_HQLoadScreen` are no 
longer excluded. 

## Tools used

Many thanks to the following utilities that made this fix possible:

* [Nexus mods for XCOM](https://www.nexusmods.com/games/xcom): A great collection of mods and improvements, which showed that this fix was possible, and tools exist to do it.
* [UPK Utils](https://github.com/wghost/UPKUtils): A great collection of tools for inspecting and modifying UPK files.
* [GUI Patcher](https://github.com/wghost/GUIPatcher): The GUI interface to apply UPK patches for XCOM, which inspired this tools interface.
* [UE Explorer](https://github.com/UE-Explorer/UE-Explorer): For providing a way to show and search Unreal Script code inside UPK files.
* [Ghidra](https://github.com/nationalsecurityagency/ghidra): To decompile XCOM.exe assembly with, to find native functions mentioned in UPK files.
* [dbg](https://github.com/x64dbg/x64dbg): To debug XCOM.exe live with, used to and track down the completely internal CalcSceneView() function.
* [ChatGPT](https://chatgpt.com/): Which is much bettter than me at translating and creating assembly code, and pretty great at explaining how these various tools operate.  

