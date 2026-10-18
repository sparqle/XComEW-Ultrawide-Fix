# XCOM: Enemy Within - Ultrawide mods

The code for two mods I made to improve ultrawide support in X-COM: Enemy Within.

## Ultrawide resolution fix


An ultrawide resolution fix for **XCOM: Enemy Within**, **Long War** and **Long War Rebalance** to make it properly expand horizontally, turning it into a [Hor+](https://www.wsgf.org/article/screen-change) game.

It addresses several visual and input problems at wide aspect ratios:

- Cursor doesn't match the highlighted square on the ground.
- Camera is too zoomed in when in headquarters.
- Camera is a bit too zoomed out when on missions or main screen.
- The health bars and other hovering UI elements don't follow units.

Read [documentation and installation](mods/Ultrawide-resolution-fix/README.md) or download from [Nexus Mods](https://www.nexusmods.com/xcom/mods/892).


## Extend squad select screen for Long War Rebalance

Show eight squad members at once in the hangar for **Long War Rebalance**.

* In ultrawide resolutions all 8 members can be geared at once.
* Shows 8 squad members on 16:9, just half offscreen as an indication that they are there.
* Still supports larger squad sizes using arrow buttons.
* Fixes an existing small UI bug on odd capacity sizes.

Read [documentation and installation](mods/Extend-squad-select-LWR/README.md) or download from [Nexus Mods](https://www.nexusmods.com/xcom/mods/448).


## License

This project's original code and documentation are available under the [MIT license](LICENSE).
UPKUtils is licensed separately under GPLv2 and is not included in the release ZIP.
The source repository retains the tools, licenses, and corresponding source in `third-party` for local use.

## Shout outs

Many thanks to the following free utilities that made modding possible:

* [Nexus mods for XCOM](https://www.nexusmods.com/games/xcom): A great collection of mods and improvements, which
  showed that this fix was possible, and tools exist to do it.
* [UPK Utils](https://github.com/wghost/UPKUtils): An amazing collection of tools for inspecting and modifying UPK files.
* [GUI Patcher](https://github.com/wghost/GUIPatcher): The GUI interface to apply UPK patches for XCOM, which inspired
  this tool's interface.
* [UE Explorer](https://github.com/UE-Explorer/UE-Explorer): For providing a way to show and search UnrealScript code
  inside UPK files.
* [JPEXS Decompiler](https://github.com/jindrapetrik/jpexs-decompiler): Used to inspect ScaleForm UI elements and to determine how to resize them.
* [Ghidra](https://github.com/nationalsecurityagency/ghidra): To decompile XCOM.exe assembly with, to find native
  functions mentioned in UPK files.
* [dbg](https://github.com/x64dbg/x64dbg): To debug XCOM.exe live with, used to track down the completely internal
  CalcSceneView() function.