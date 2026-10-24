# Build mod releases

To search UPK names in a directory or a single package, run:

```powershell
.\tools\upk-search-names.ps1 'C:\Packages' 'soldier|hangar' -IgnoreCase
.\tools\upk-search-names.ps1 'C:\Packages\XComGame.upk' 'soldier|hangar' -IgnoreCase
```

Directory searches include only `.upk` files directly inside that directory.
The first argument also accepts `-Path`; the existing `-Directory` name remains
an alias. Matches are printed as `filename:line:matching-text`.
Exit codes are 0 for matches, 1 for no
matches, and 2 for errors.

To decompile a UPK method to pseudo-code, run:

```powershell
.\tools\upk-hex-to-pseudocode.ps1 'C:\Packages\XComGame.upk' 'ClassName.MethodName'
```

The script decompresses the package in a temporary directory when needed and
prints the pseudo-code to standard output. The original package is preserved.
It looks for `DecompressLZO.exe` and `HexToPseudoCode.exe` beside the script,
in `../third-party` relative to the script, then on `PATH`.

To find an object entry in a UPK package, run:

```powershell
.\tools\upk-find-object.ps1 'C:\Packages\Command1.upk' 'gfxStrategyHUD.StrategyHUD'
```

The script uses `FindObjectEntry.exe` and the shared UPK decompression helper,
prints the tool output, and removes temporary files after the lookup. The original
package is preserved. It looks for `DecompressLZO.exe` and `FindObjectEntry.exe`
beside the script, in `../third-party`, then on `PATH`.
Exit codes are 0 for a successful tool invocation and 2 for errors.

To export a SwfMovie as an editable Flash file, run:

```powershell
.\tools\upk-export-swf.ps1 'C:\Packages\Command1.upk' 'gfxStrategyHUD.StrategyHUD' '.\StrategyHUD.swf'
```

The output path is optional and defaults to `<entryName>.swf` in the current
directory. Use `-Force` to overwrite an existing output. The script uses the same
tool lookup and decompression helpers as `upk-find-object.ps1`, preserves the
package, and extracts only the movie byte array within the selected export.
Scaleform `GFX`/`CFX` signatures are converted to `FWS`/`CWS`; the remaining
payload is unchanged. Scaleform extensions may require a compatible editor
(such as JPEXS FFDec). This exports a compiled movie, not an authoring `.fla`
project, and does not import edits back into the UPK.
Exit codes are 0 for success and 2 for errors.

Run from the project root:

```powershell
powershell.exe -NoProfile -NonInteractive -File tools/build.ps1
```

The script reads each `mods/<name>/mod.json`, concatenates its `files` in order
into `mods/<name>.txt`, and creates `dist/<name>-<version>.zip` containing that
text file.

File paths are relative to the directory containing `mod.json`. Use `../` to
reference shared files in sibling mod directories (for example,
`../shared/squad-select/extend-ui.txt`). Paths must stay inside `mods/`.

Leading and trailing line breaks are trimmed from each fragment, with one blank
line inserted between fragments. Internal formatting is preserved.
