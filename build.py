"""Build the standalone Windows GUI using the current Python interpreter."""
from pathlib import Path
import sys


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

    PyInstaller.__main__.run([
        "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", NAME,
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build" / "pyinstaller"),
        "--specpath", str(ROOT / "build"),
        "--paths", str(ROOT / "src"),
        "--add-data", f"{ROOT / 'patches' / 'Fix-ultrawide-HPBars.txt'};patches",
        "--add-data", f"{ROOT / 'patches' / 'Fix-ultrawide-HPBars.txt.uninstall.txt'};patches",
        str(ROOT / "src" / "app.py"),
    ])
    print(f"Built {ROOT / 'dist' / (NAME + '.exe')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
