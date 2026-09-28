#!/usr/bin/env python3
"""
XCOM: Enemy Within - Complete Ultrawide EXE Patcher
====================================================

Applies the complete native ultrawide patch set to a CLEAN XComEW.exe:

  1) Tactical cursor/UI coordinate fix.
  2) Dynamic tangent-space projection FOV fix.
  3) Removes the Command1 FOV exclusion.
  4) Removes the CIN_LoadScreen FOV exclusion.
  5) Removes the CIN_HQLoadScreen FOV exclusion.

This patcher is intentionally all-or-nothing:

  * CLEAN executable -> apply ALL patches
  * FULLY PATCHED executable -> report already patched
  * anything else -> refuse to modify

Installation requires a clean or fully patched set of ultrawide blocks.
Restore reverses recognized blocks in place and preserves unrelated edits.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import tempfile
from pathlib import Path


# Tactical cursor/UI coordinate patch.
CURSOR_ORIGINAL = bytes.fromhex("""
        F3 0F 2A 4C 24 20 0F 28 C1 F3 0F 59 05 04 FE 86
        01 0F 28 E0 F3 0F 59 25 38 ED 86 01 F3 0F 5C CC
        F3 0F 59 0D 98 65 87 01 F3 0F 59 D0 F3 0F 58 CA
        F3 0F 11 4C 24 4C 8B 4C 24 4C 0F 57 C9 F3 0F 2A
        4C 24 24 F3 0F 59 D8 F3 0F 59 05 64 ED 87 01 F3
        0F 5C C8 F3 0F 59 0D 98 65 87 01 5F F3 0F 58 CB
        F3 0F 11 4C 24 4C 8B 54 24 4C 5E 89 08 89 50 04
        5B 83 C4 38 C2 0C 00
""")

CURSOR_PATCHED = bytes.fromhex("""
        F3 0F 2A 44 24 24 90 90 90 F3 0F 5E 05 64 ED 87
        01 0F 28 E0 F3 0F 59 25 38 ED 86 01 8B 4C 24 20
        F3 0F 10 25 98 65 87 01 F3 0F 2A C9 F3 0F 59 CC
        B9 80 02 00 00 F3 0F 2A E1 F3 0F 5C D4 F3 0F 59
        D0 F3 0F 58 CA 90 90 F3 0F 59 25 64 ED 87 01 F3
        0F 59 D8 F3 0F 59 25 98 65 87 01 F3 0F 11 08 F3
        0F 11 58 04 5F 5E 5B 83 C4 38 C2 0C 00 90 90 90
        90 90 90 90 90 90 90
""")

if len(CURSOR_ORIGINAL) != len(CURSOR_PATCHED):
    raise RuntimeError("Internal error: cursor patch sizes do not match")


# Dynamic CalcSceneView FOV patch.
FOV_ORIGINAL = bytes.fromhex("""
        8B 44 24 40 8B C8 89 4C 24 20 DB 44 24 20 85 C9
        79 06 D8 05 50 F0 87 01 8B 4C 24 3C 8B D1 89 54
        24 20 DB 44 24 20 85 D2 79 06 D8 05 50 F0 87 01
        DE F9 D8 0D 44 A7 87 01 D8 4C 24 18 EB 0C
""")

FOV_PATCHED = bytes.fromhex("""
        8B 44 24 40 8B 4C 24 3C D9 44 24 18 D9 F2 DD D8
        EB 06 D8 05 50 F0 87 01 DB 44 24 40 DB 44 24 3C
        DE F9 DE C9 EB 0C 90 90 90 90 D8 05 50 F0 87 01
        90 90 D8 0D 44 A7 87 01 D9 E8 D9 F3 EB 0C
""")

if len(FOV_ORIGINAL) != len(FOV_PATCHED):
    raise RuntimeError("Internal error: FOV patch sizes do not match")


# Command1 / CIN_LoadScreen / CIN_HQLoadScreen exclusion patch.
EXCLUSIONS_ORIGINAL = bytes.fromhex("""
        68 2C 59 96 01 8D 8C 24 0C 01 00 00 E8 CF F1 0B
        00 85 C0 74 68 68 40 59 96 01 8D 8C 24 0C 01 00
        00 E8 BA F1 0B 00 85 C0 74 53 68 60 59 96 01 8D
        8C 24 0C 01 00 00 E8 A5 F1 0B 00 85 C0 74 3E
""")

EXCLUSIONS_PATCHED = bytes.fromhex("""
        68 2C 59 96 01 8D 8C 24 0C 01 00 00 E8 CF F1 0B
        00 85 C0 90 90 68 40 59 96 01 8D 8C 24 0C 01 00
        00 E8 BA F1 0B 00 85 C0 90 90 68 60 59 96 01 8D
        8C 24 0C 01 00 00 E8 A5 F1 0B 00 85 C0 90 90
""")

if len(EXCLUSIONS_ORIGINAL) != len(EXCLUSIONS_PATCHED):
    raise RuntimeError("Internal error: exclusion patch sizes do not match")


PHONE_HOME_ORIGINAL = "firaxis.com"
PHONE_HOME_LEGACY = "yiraxis.com"
# Same UTF-16LE byte length as the original; .invalid is reserved by RFC 2606.
PHONE_HOME_DISABLED = "xcm.invalid"


def disable_phone_home(data: bytes) -> bytes:
    """Replace the original or PatcherGUI host without moving any EXE bytes."""
    replacement = PHONE_HOME_DISABLED.encode("utf-16le")
    result = data
    found = False
    for host in (PHONE_HOME_ORIGINAL, PHONE_HOME_LEGACY, PHONE_HOME_DISABLED):
        needle = host.encode("utf-16le")
        if len(needle) != len(replacement):
            raise RuntimeError("Phone home patch sizes do not match")
        for offset in find_all(data, needle):
            # Require a UTF-16 host ending, not a substring of another domain.
            end = offset + len(needle)
            if offset % 2 or data[end:end + 2] not in (b"\0\0", b"/\0", b":\0", b"?\0", b"#\0"):
                continue
            found = True
            result = result[:offset] + replacement + result[end:]
    if not found:
        raise ValueError("No recognized phone home address found; no changes made.")
    return result


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_all(data: bytes, needle: bytes) -> list[int]:
    hits: list[int] = []
    pos = 0
    while True:
        pos = data.find(needle, pos)
        if pos < 0:
            return hits
        hits.append(pos)
        pos += 1


def inspect(path: Path) -> dict:
    data = path.read_bytes()
    return {
        "data": data,
        "cursor_original": find_all(data, CURSOR_ORIGINAL),
        "cursor_patched": find_all(data, CURSOR_PATCHED),
        "fov_original": find_all(data, FOV_ORIGINAL),
        "fov_patched": find_all(data, FOV_PATCHED),
        "exclusions_original": find_all(data, EXCLUSIONS_ORIGINAL),
        "exclusions_patched": find_all(data, EXCLUSIONS_PATCHED),
    }


def is_clean(info: dict) -> bool:
    return (
        len(info["cursor_original"]) == 1
        and not info["cursor_patched"]
        and len(info["fov_original"]) == 1
        and not info["fov_patched"]
        and len(info["exclusions_original"]) == 1
        and not info["exclusions_patched"]
    )


def is_fully_patched(info: dict) -> bool:
    return (
        not info["cursor_original"]
        and len(info["cursor_patched"]) == 1
        and not info["fov_original"]
        and len(info["fov_patched"]) == 1
        and not info["exclusions_original"]
        and len(info["exclusions_patched"]) == 1
    )


def default_candidates() -> list[Path]:
    roots: list[Path] = []
    for env in ("PROGRAMFILES(X86)", "PROGRAMFILES"):
        value = os.environ.get(env)
        if value:
            roots.append(Path(value))

    candidates: list[Path] = []
    for root in roots:
        candidates.extend([
            root / "Steam/steamapps/common/XCom-Enemy-Unknown/XEW/Binaries/Win32/XComEW.exe",
            root / "Steam/steamapps/common/XCOM Enemy Unknown/XEW/Binaries/Win32/XComEW.exe",
        ])
    return candidates


def resolve_exe(arg: str | None) -> Path:
    if arg:
        p = Path(arg).expanduser().resolve()
        if p.is_dir():
            p = p / "XComEW.exe"
        return p

    for p in default_candidates():
        if p.is_file():
            return p.resolve()

    beside = Path.cwd() / "XComEW.exe"
    if beside.is_file():
        return beside.resolve()

    raise FileNotFoundError(
        "Could not locate XComEW.exe automatically. Pass its path explicitly."
    )


def make_backup(path: Path) -> Path:
    """Keep the first snapshot beside the game, never overwrite an existing .bak."""
    backup = path.with_name(path.name + ".bak")
    try:
        out = backup.open("xb")
    except FileExistsError:
        return backup
    try:
        with out, path.open("rb") as source:
            shutil.copyfileobj(source, out)
            out.flush()
            os.fsync(out.fileno())
    except Exception:
        backup.unlink(missing_ok=True)
        raise
    return backup


def atomic_write(path: Path, data: bytes) -> None:
    fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        shutil.copystat(path, tmp)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def print_match_counts(info: dict) -> None:
    print(f"Cursor original/patched:     {len(info['cursor_original'])} / {len(info['cursor_patched'])}")
    print(f"FOV original/patched:        {len(info['fov_original'])} / {len(info['fov_patched'])}")
    print(f"Exclusions original/patched: {len(info['exclusions_original'])} / {len(info['exclusions_patched'])}")


def status(path: Path, show_hash: bool = False) -> int:
    info = inspect(path)

    print(f"Executable: {path}")
    if show_hash:
        print(f"SHA-256:    {sha256(path)}")

    if is_clean(info):
        print("Status:     CLEAN / UNPATCHED")
        print(f"Cursor:     original at file offset 0x{info['cursor_original'][0]:X}")
        print(f"FOV:        original at file offset 0x{info['fov_original'][0]:X}")
        print(f"Exclusions: original at file offset 0x{info['exclusions_original'][0]:X}")
        return 0

    if is_fully_patched(info):
        print("Status:     FULLY PATCHED")
        print(f"Cursor:     patched at file offset 0x{info['cursor_patched'][0]:X}")
        print(f"FOV:        patched at file offset 0x{info['fov_patched'][0]:X}")
        print(f"Exclusions: patched at file offset 0x{info['exclusions_patched'][0]:X}")
        return 0

    print("Status:     UNSUPPORTED / PARTIALLY PATCHED")
    print("This patcher only accepts a completely clean or completely patched executable.")
    print_match_counts(info)
    return 2


def install(path: Path, dry_run: bool, show_hash: bool) -> int:
    info = inspect(path)

    print(f"Executable: {path}")
    if show_hash:
        print(f"SHA-256:    {sha256(path)}")

    if is_fully_patched(info):
        print("Complete ultrawide patch is already installed. No changes made.")
        return 0

    if not is_clean(info):
        print("Refusing to modify the executable.", file=sys.stderr)
        print("Expected a completely clean XComEW.exe.", file=sys.stderr)
        print("Partial patches are intentionally not supported.", file=sys.stderr)
        print_match_counts(info)
        return 2

    cursor_off = info["cursor_original"][0]
    fov_off = info["fov_original"][0]
    exclusions_off = info["exclusions_original"][0]

    print(f"Cursor block:    0x{cursor_off:X}")
    print(f"FOV block:       0x{fov_off:X}")
    print(f"Exclusion block: 0x{exclusions_off:X}")

    new_data = bytearray(info["data"])
    new_data[cursor_off:cursor_off + len(CURSOR_ORIGINAL)] = CURSOR_PATCHED
    new_data[fov_off:fov_off + len(FOV_ORIGINAL)] = FOV_PATCHED
    new_data[exclusions_off:exclusions_off + len(EXCLUSIONS_ORIGINAL)] = EXCLUSIONS_PATCHED

    test_data = bytes(new_data)

    # Verify the complete patch set before touching disk.
    if find_all(test_data, CURSOR_ORIGINAL):
        raise RuntimeError("Internal verification failed: original cursor block remains")
    if len(find_all(test_data, CURSOR_PATCHED)) != 1:
        raise RuntimeError("Internal verification failed: patched cursor block mismatch")

    if find_all(test_data, FOV_ORIGINAL):
        raise RuntimeError("Internal verification failed: original FOV block remains")
    if len(find_all(test_data, FOV_PATCHED)) != 1:
        raise RuntimeError("Internal verification failed: patched FOV block mismatch")

    if find_all(test_data, EXCLUSIONS_ORIGINAL):
        raise RuntimeError("Internal verification failed: original exclusion block remains")
    if len(find_all(test_data, EXCLUSIONS_PATCHED)) != 1:
        raise RuntimeError("Internal verification failed: patched exclusion block mismatch")

    if dry_run:
        print("Dry run: all patch groups verified; no files changed.")
        return 0

    backup = make_backup(path)
    print(f"Backup:     {backup}")

    try:
        atomic_write(path, test_data)
        final = inspect(path)
        if not is_fully_patched(final):
            raise RuntimeError("Post-write verification failed")
    except Exception:
        atomic_write(path, info["data"])
        print("Patch failed; reverted this operation.", file=sys.stderr)
        raise

    print("Complete ultrawide patch installed successfully.")
    print("Applied:")
    print("  - tactical cursor/UI coordinate fix")
    print("  - dynamic tangent-space projection FOV fix")
    print("  - Command1 FOV exclusion removed")
    print("  - CIN_LoadScreen FOV exclusion removed")
    print("  - CIN_HQLoadScreen FOV exclusion removed")
    return 0


def reverse_patch(data: bytes) -> bytes:
    """Reverse recognized ultrawide blocks, preserving all unrelated EXE edits."""
    result = bytearray(data)
    for name, original, patched in (
        ("cursor", CURSOR_ORIGINAL, CURSOR_PATCHED),
        ("FOV", FOV_ORIGINAL, FOV_PATCHED),
        ("exclusions", EXCLUSIONS_ORIGINAL, EXCLUSIONS_PATCHED),
    ):
        clean = find_all(data, original)
        changed = find_all(data, patched)
        if len(clean) + len(changed) != 1:
            raise ValueError(f"Unrecognized or ambiguous {name} patch block; no changes made.")
        if changed:
            offset = changed[0]
            result[offset:offset + len(patched)] = original
    return bytes(result)


def restore(path: Path, dry_run: bool = False) -> int:
    original = path.read_bytes()
    restored = reverse_patch(original)
    if restored == original:
        print("Ultrawide EXE patch is already removed.")
        return 0
    if dry_run:
        print("Dry run: reverse patch verified; no files changed.")
        return 0
    make_backup(path)
    try:
        atomic_write(path, restored)
        if path.read_bytes() != restored:
            raise RuntimeError("Reverse patch verification failed")
    except Exception:
        atomic_write(path, original)
        raise
    print("Ultrawide EXE patch reversed; unrelated modifications retained.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="All-in-one XCOM: Enemy Within ultrawide EXE patcher."
    )
    parser.add_argument(
        "exe",
        nargs="?",
        help="Path to XComEW.exe (or its containing directory). Auto-detected when possible.",
    )
    parser.add_argument("--status", action="store_true", help="Report patch status only.")
    parser.add_argument("--restore", action="store_true", help="Reverse the ultrawide patch without needing a backup.")
    parser.add_argument("--dry-run", action="store_true", help="Verify patchability without writing.")
    parser.add_argument("--sha256", action="store_true", help="Display executable SHA-256.")
    args = parser.parse_args()

    try:
        path = resolve_exe(args.exe)
        if not path.is_file():
            print(f"XComEW.exe not found: {path}", file=sys.stderr)
            return 2

        if args.restore:
            return restore(path, args.dry_run)
        if args.status:
            return status(path, args.sha256)
        return install(path, args.dry_run, args.sha256)

    except PermissionError:
        print(
            "Permission denied. Close the game/debugger and run the terminal with permission "
            "to modify the game directory.",
            file=sys.stderr,
        )
        return 3
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
