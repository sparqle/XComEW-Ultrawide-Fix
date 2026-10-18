# Third-party software

The root MIT license covers this project's original code, documentation, and artwork. It does not relicense
third-party software or XCOM game content.

## UPKUtils

`DecompressLZO.exe` and `PatchUPK.exe` in this directory are tools from
[UPKUtils](https://github.com/wghost/UPKUtils), by wghost81 (Wasteland Ghost).
They are distributed under the GNU General Public License, version 2; see [the license](UPKUtils-GPL-2.0.txt).
The application invokes these standalone executables through their command-line interfaces.

GPLv2 section 3 requires corresponding source when distributing these binaries. A link to the upstream project
and a copy of its license alone do not satisfy that requirement.

The included [UPKUtils source archive](UPKUtils-7.3-source.zip) is an unmodified snapshot of upstream tag `7.3`, commit
`f4a7149cb25389b3d3e0b4ee1bf4bfefd7b02c29`, including its build scripts and miniLZO sources.
The source archive's `build/CMakeLists.txt` builds both bundled tools using CMake and a C++11 compiler.

Both bundled executables match the files in `UPKUtils73.7z` from the
[official UPKUtils 7.3 release](https://github.com/wghost/UPKUtils/releases/tag/7.3).
Their SHA-256 hashes were checked against a fresh download of that release archive. The included source snapshot
is from the same release tag. If replacing these binaries, also update their corresponding source and notices.

Current binary SHA-256 values:

```text
DecompressLZO.exe 49BDDD80AAE5A6AAC5923E5ED0A012EFF9F04727F6C78D69B49AEC52EC1DBDD9
PatchUPK.exe      57B666E97CD5E695A561E09618A0BE1AC1FCA02B247BFF5FED42A2949E639DA7
```

## miniLZO

UPKUtils includes miniLZO 2.06 by Markus Franz Xaver Johannes Oberhumer.
Its original [license](miniLZO-COPYING.txt) and required [README](README.LZO) are preserved in this directory.
Its source files and copyright notices are retained in the UPKUtils source archive.
