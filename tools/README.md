# Build mod releases

Run from the project root:

```powershell
powershell.exe -NoProfile -NonInteractive -File tools/build.ps1
```

The script reads each `mods/<name>/mod.json`, concatenates its `files` in order
into `mods/<name>.txt`, and creates `dist/<name>-<version>.zip` containing that
text file.

Leading and trailing line breaks are trimmed from each fragment, with one blank
line inserted between fragments. Internal formatting is preserved.
