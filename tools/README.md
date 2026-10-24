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
