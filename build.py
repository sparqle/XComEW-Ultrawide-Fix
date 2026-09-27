"""Build the standalone Windows GUI using the current Python interpreter."""
from pathlib import Path
import shutil
import sys
from zipfile import ZIP_DEFLATED, ZipFile

from src.version import VERSION
from src.game_path import CONFIG

ROOT = Path(__file__).resolve().parent
NAME = "XComEW-Ultrawide-Fix"


def main() -> int:
    if sys.platform != "win32":
        print("Build on Windows to produce a Windows executable.", file=sys.stderr)
        return 1
    try:
        import PyInstaller.__main__
    except ModuleNotFoundError:
        print(
            "Missing build dependency. Install requirements-build.txt into "
            "this interpreter first (see README.md).",
            file=sys.stderr,
        )
        return 1

    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo, StringFileInfo, StringStruct, StringTable,
        VarFileInfo, VarStruct, VSVersionInfo,
    )

    version_numbers = tuple(int(part) for part in VERSION.split("."))
    version_numbers += (0,) * (4 - len(version_numbers))
    version_file = ROOT / "build" / "version-info.txt"
    version_file.parent.mkdir(parents=True, exist_ok=True)
    version_info = VSVersionInfo(
        ffi=FixedFileInfo(filevers=version_numbers, prodvers=version_numbers,
                          mask=0x3F, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
        kids=[
            StringFileInfo([StringTable("040904B0", [
                StringStruct("FileDescription", "XCOM: Enemy Within Ultrawide Fix"),
                StringStruct("FileVersion", VERSION),
                StringStruct("ProductName", NAME),
                StringStruct("ProductVersion", VERSION),
                StringStruct("OriginalFilename", NAME + ".exe"),
            ])]),
            VarFileInfo([VarStruct("Translation", [1033, 1200])]),
        ],
    )
    version_file.write_text(str(version_info), encoding="utf-8")

    PyInstaller.__main__.run([
        "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", NAME,
        "--version-file", str(version_file),
        "--icon", str(ROOT / "assets" / "ultrawide.ico"),
        "--add-data", str(ROOT / "assets" / "ultrawide.ico") + ";assets",
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build" / "pyinstaller"),
        "--specpath", str(ROOT / "build"),
        "--paths", str(ROOT / "src"),
        str(ROOT / "src" / "app.py"),
    ])
    mods = ROOT / "dist" / "mods"
    mods.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "mods" / "Fix-ultrawide-Tactical.txt", mods)
    shutil.copy2(ROOT / "README.md", ROOT / "dist" / "README.md")
    shutil.copy2(ROOT / "LICENSE", ROOT / "dist" / "LICENSE")
    shutil.copytree(ROOT / "third_party", ROOT / "dist" / "third_party", dirs_exist_ok=True)
    dist = ROOT / "dist"
    (dist / "backups").mkdir(exist_ok=True)
    archive = dist / f"{NAME}-{VERSION}.zip"
    # Exclude ZIPs and installation-specific uninstall scripts left in mods.
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
        bundle.writestr("backups/", b"")
        for path in sorted(dist.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(dist)
            if path.suffix.lower() == ".zip" and relative.parts[0] != "third_party":
                continue
            if relative.parts[0].lower() == "backups":
                continue
            if relative.as_posix().lower() == CONFIG.lower():
                continue
            if relative.parts[0].lower() == "mods" and path.name.lower().endswith(".uninstall.txt"):
                continue
            bundle.write(path, relative)
    print(f"Built {ROOT / 'dist' / (NAME + '.exe')} (version {VERSION})")
    print(f"Created {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
