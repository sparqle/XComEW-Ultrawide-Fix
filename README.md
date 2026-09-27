# XCOM: Enemy Within Ultrawide Fix

An ultrawide fix for **XCOM: Enemy Within** and **Long War**. It addresses three visible problems at wide aspect ratios:

- **Zoomed-in camera:** The game shows too little of the scene at ultrawide resolutions.
- **Misaligned mouse and ground selection:** The position selected in the game does not match where you point on screen.
- **Misplaced health bars:** Unit health bars do not line up with their units.

The fix changes `XComEW.exe` for the camera and mouse/ground selection, and `XComGame.upk` for the health bars.

## Tested configurations

Tested at **21:9** in **XCOM: Enemy Within** and **Long War**. **Enemy Unknown has not been tested.** Other 
aspect ratios have not been verified.

## Install

1. Close the game.
2. Run `XComEW-Ultrawide-Fix.exe` and choose your **`XCom-Enemy-Unknown`** folder. Select the main game folder, not the `XEW` folder inside it.
3. Leave **“Skip installing/restoring HP bar patch (XComGame.upk), I will patch it myself”** unchecked and click **Install**. 
   This applies all three fixes.

If you plan to apply the health bar patch yourself using PatcherGUI, check **Skip installing/restoring HP bar patch** 
before clicking **Install**. In that case, the app only changes `XComEW.exe`, and the UPKUtils tools are not required by the app.

## Restore

Close the game, select the same `XCom-Enemy-Unknown` folder, and click **Restore**. Leave the skip checkbox unchecked 
if this app installed the health bar patch; check it if you managed that patch yourself.

Keep the EXE backup and the app's state file until you restore the fix. The app uses the EXE backup to restore `XComEW.exe` 
and an uninstall patch to restore the health bar change in `XComGame.upk`. If you installed the health bar patch separately,
restore it using the tool you used to install it.

The app expects an unmodified, compatible `XComEW.exe` when installing. If another mod has changed the same executable 
areas, the install may be refused.

