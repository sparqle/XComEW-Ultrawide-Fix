"""Game directory discovery and portable last-used directory settings."""
from pathlib import Path

CONFIG = "XComEW-Ultrawide-Fix.cfg"
GAME_DIRECTORIES = tuple(
    Path(drive) / root / "SteamApps/common/XCom-Enemy-Unknown"
    for root in (
        "Program Files/Steam",
        "Program Files (x86)/Steam",
        "Steam",
        "SteamLibrary",
        "Games/Steam",
    )
    for drive in ("C:/", "D:/")
)


def find_game_directory(value: str) -> str:
    value = value.strip()
    if value and Path(value).expanduser().is_dir():
        return str(Path(value).expanduser().resolve())
    for candidate in GAME_DIRECTORIES:
        if candidate.is_dir():
            return str(candidate)
    return ""


def load_game_directory(folder: Path) -> str:
    try:
        value = (folder / CONFIG).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        value = ""
    return find_game_directory(value)


def save_game_directory(folder: Path, value: str) -> None:
    value = value.strip()
    if value and Path(value).expanduser().is_dir():
        (folder / CONFIG).write_text(str(Path(value).expanduser().resolve()) + "\n", encoding="utf-8")
