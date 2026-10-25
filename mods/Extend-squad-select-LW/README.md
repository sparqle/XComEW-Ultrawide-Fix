# XCOM: Enemy Within - Show eight soldiers in squad select screen (LW)

Show eight squad members at once in the hangar for **Long War 1.0**, and allow editing them all at once 
on ultrawide resolutions.

* Shows 8 squad members on 16:9, just half offscreen as an indication that they are there.
* Still supports larger squad sizes using arrow buttons.
* Fixes an existing small UI bug on odd capacity sizes.

## Install 

1. Close the game.
2. Confirm you have [Long War 1.0](https://www.nexusmods.com/xcom/mods/88) installed.
2. If you play in an ultrawide resolution, confirm you have [Ultrawide resolution fix](https://www.nexusmods.com/xcom/mods/892) installed.
3. Download and extract [PatcherGUI](https://www.nexusmods.com/xcom/mods/448).
4. Download and extract mod file [Extend-squad-select-LW](https://www.nexusmods.com/games/xcom/mods/894).
5. Open PatcherGUI.
6. Browse to your "XCom-Enemy-Unknown/XEW" directory.
7. Browse to the mod file: `Extend-squad-select-LW`
8. Click **Apply** to install.

## Tested configurations

Tested at 3440x1440 in **Long War 1.0**: starting missions and screens.

* Tested with all 4 squad member types (soldier, SHIV, MEC, MEC trooper).
* Tested with up to 10 squad members.

## Implementation

The existing LWR logic already allows mapping of up to 12 squad members. It just needed to
be extended to map additional squad members to new animation slots.

### 3D Animation changes

For each existing slot (1-6), and each squad member type (soldier, SHIV, MEC, MEC trooper), 
a named animation slot existed in a Matinee animation in `Anim_Hangar.upk`.

For each squad member type two new slots were added to the animation, by copying the first two slot animations,
but using a new position.

### 2D UI changes

The Scaleform (Flash) SquadSelect file that LWR uses was extended to either show 6 or 8 boxes at once, 
depending on the aspect ratio.


## License

This project's original code and documentation are available under the [MIT license](LICENSE).
UPKUtils is licensed separately under GPLv2 and is not included in the release ZIP.
The source repository retains the tools, licenses, and corresponding source in `third-party` for local use.

## Tools used

Many thanks to the following utilities that made this mod possible:

* [Nexus Mods for XCOM](https://www.nexusmods.com/games/xcom): A great collection of mods and improvements, which
  showed that this fix was possible, and tools exist to do it.
* [UPK Utils](https://github.com/wghost/UPKUtils): An amazing collection of tools for inspecting and modifying UPK files.
* [PatcherGUI](https://github.com/wghost/PatcherGUI): The GUI interface to apply UPK patches for XCOM, which inspired
  this tool's interface.
* [UE Explorer](https://github.com/UE-Explorer/UE-Explorer): For providing a way to show and search UnrealScript code
  inside UPK files.
* [JPEXS Decompiler](https://github.com/jindrapetrik/jpexs-decompiler): Used to inspect ScaleForm UI elements and to determine how to resize them.
* [ChatGPT](https://chatgpt.com/): Mostly to assist with compiling and decompiling UnrealEngine file formats and UnrealScript bytecode.
