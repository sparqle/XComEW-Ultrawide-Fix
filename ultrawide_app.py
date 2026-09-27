"""Windows UI for the XCOM: Enemy Within executable and HP bar UPK fixes."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import xcomew_complete_ultrawide_patcher as exe_patch

APP = "XCOM EW Ultrawide Fix"
STATE = ".ultrawide-fix.json"
EXE_BACKUP = ".ultrawide-fix.original"
SCRIPT = "Fix-ultrawide-HPBars.txt"
UNINSTALL = SCRIPT + ".uninstall.txt"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_atomic(path: Path, data: bytes) -> None:
    if path.exists():
        exe_patch.atomic_write(path, data)
    else:
        fd, name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as out:
                out.write(data)
                out.flush()
                os.fsync(out.fileno())
            os.replace(name, path)
        finally:
            if os.path.exists(name):
                os.unlink(name)


def locations(base: Path) -> tuple[Path, Path]:
    base = base.resolve()
    root = base / "XEW"
    exe = root / "Binaries" / "Win32" / "XComEW.exe"
    if not exe.is_file():
        raise FileNotFoundError(f"Expected XComEW.exe at {exe}. Select the XCom-Enemy-Unknown directory.")
    upk_dir = root / "XComGame" / "CookedPCConsole"
    matches = [p for p in upk_dir.glob("*.upk") if p.name.lower() == "xcomgame.upk"] if upk_dir.is_dir() else []
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected XComGame.upk in {upk_dir}")
    return exe, matches[0]


def load_state(exe: Path) -> dict:
    path = exe.parent / STATE
    if not path.exists():
        return {"version": 2, "components": {}}
    obj = json.loads(path.read_text(encoding="utf-8"))
    if obj.get("version") not in (1, 2) or not isinstance(obj.get("components"), dict):
        raise ValueError("Unrecognized ultrawide fix state file; no changes made.")
    return obj


def save_state(exe: Path, state: dict) -> None:
    path = exe.parent / STATE
    if state["components"]:
        write_atomic(path, (json.dumps(state, indent=2) + "\n").encode())
    elif path.exists():
        path.unlink()


def tool(name: str, folder: Path) -> Path:
    p = folder / (name + ".exe")
    if not p.is_file():
        raise FileNotFoundError(f"Missing {p}. Select a folder with DecompressLZO.exe and PatchUPK.exe.")
    return p.resolve()


def binaries_folder() -> Path:
    app_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    return app_dir / "binaries"


def run_tool(args: list[str], cwd: Path) -> None:
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, errors="replace", timeout=300,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if p.returncode:
        raise RuntimeError(f"{Path(args[0]).name} failed ({p.returncode}):\n{(p.stdout + p.stderr)[-3000:]}")


def stage_upk(upk: Path, folder: Path, uninstall: bool = False) -> bytes:
    decompress = tool("DecompressLZO", folder)
    patch = tool("PatchUPK", folder)
    script = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / (UNINSTALL if uninstall else SCRIPT)
    with tempfile.TemporaryDirectory(prefix="xcomew-ultrawide-") as temp:
        work = Path(temp)
        # DecompressLZO writes the output path; PatchUPK finds XComGame.upk in the directory.
        unpacked = work / "XComGame.upk"
        try:
            run_tool([str(decompress), str(upk), str(unpacked)], work)
        except RuntimeError as error:
            if "Package is already decompressed!" not in str(error):
                raise
            # DecompressLZO reports an already unpacked UPK as exit code 1.
            # Work only on the staging copy, leaving the installed file untouched.
            shutil.copy2(upk, unpacked)
        if not unpacked.is_file() or not unpacked.stat().st_size:
            raise RuntimeError("DecompressLZO did not produce XComGame.upk.")
        before = digest(unpacked)
        run_tool([str(patch), str(script), str(work)], work)
        if digest(unpacked) == before:
            raise RuntimeError("PatchUPK made no change to the staged UPK.")
        return unpacked.read_bytes()


def exe_bytes(exe: Path, uninstall: bool = False) -> bytes:
    info = exe_patch.inspect(exe)
    if not (exe_patch.is_fully_patched(info) if uninstall else exe_patch.is_clean(info)):
        raise ValueError("XComEW.exe does not match the expected complete patch state.")
    data = bytearray(info["data"])
    for label, original, patched in (
        ("cursor", exe_patch.CURSOR_ORIGINAL, exe_patch.CURSOR_PATCHED),
        ("fov", exe_patch.FOV_ORIGINAL, exe_patch.FOV_PATCHED),
        ("exclusions", exe_patch.EXCLUSIONS_ORIGINAL, exe_patch.EXCLUSIONS_PATCHED),
    ):
        old, new = (patched, original) if uninstall else (original, patched)
        offset = info[label + ("_patched" if uninstall else "_original")][0]
        data[offset:offset + len(old)] = new
    result = bytes(data)
    for original, patched in ((exe_patch.CURSOR_ORIGINAL, exe_patch.CURSOR_PATCHED),
                              (exe_patch.FOV_ORIGINAL, exe_patch.FOV_PATCHED),
                              (exe_patch.EXCLUSIONS_ORIGINAL, exe_patch.EXCLUSIONS_PATCHED)):
        old, new = (patched, original) if uninstall else (original, patched)
        if old in result or result.count(new) != 1:
            raise RuntimeError("EXE patch verification failed.")
    return result


def install(base: Path, folder: Path, hp: bool, log) -> None:
    exe, upk = locations(base)
    state = load_state(exe)
    targets = [("exe", exe)] + ([("upk", upk)] if hp else [])
    for key, target in targets:
        record = state["components"].get(key)
        if record:
            if digest(target) != record["patched_sha256"]:
                raise ValueError(f"{target.name} changed since installation; refusing to overwrite it.")
            log(f"{target.name}: already installed")
    pending = [(key, path) for key, path in targets if key not in state["components"]]
    if not pending:
        return
    # Prepare and validate both changes before writing either game file.
    payloads = {}
    for key, target in pending:
        log(f"Preparing {target.name}...")
        payloads[key] = exe_bytes(target) if key == "exe" else stage_upk(target, folder)
    originals = {key: target.read_bytes() for key, target in pending}
    written = []
    exe_backup = exe.with_name(exe.name + EXE_BACKUP)
    backup_created = False
    try:
        if "exe" in originals:
            if exe_backup.exists():
                raise FileExistsError(f"EXE backup already exists: {exe_backup}")
            shutil.copy2(exe, exe_backup)
            backup_created = True
            if digest(exe_backup) != hashlib.sha256(originals["exe"]).hexdigest():
                raise RuntimeError("EXE backup verification failed.")
        for key, target in pending:
            original_hash = hashlib.sha256(originals[key]).hexdigest()
            write_atomic(target, payloads[key])
            written.append((key, target))
            patched_hash = digest(target)
            if patched_hash != hashlib.sha256(payloads[key]).hexdigest():
                raise RuntimeError("Installed file verification failed.")
            state["components"][key] = {"path": str(target),
                                         "original_sha256": original_hash, "patched_sha256": patched_hash}
            if key == "exe":
                state["components"][key]["backup"] = str(exe_backup)
            save_state(exe, state)
            log(f"Installed {target.name}")
    except Exception:
        for key, target in reversed(written):
            write_atomic(target, originals[key])
            state["components"].pop(key, None)
        save_state(exe, state)
        if backup_created and exe_backup.exists():
            exe_backup.unlink()
        raise


def restore(base: Path, folder: Path, hp: bool, log) -> None:
    exe, upk = locations(base)
    state = load_state(exe)
    selected = [("exe", exe)] + ([("upk", upk)] if hp else [])
    ready = []
    for key, path in selected:
        rec = state["components"].get(key)
        if not rec:
            log(f"{path.name}: no managed installation")
            continue
        if Path(rec["path"]) != path:
            raise ValueError(f"Recorded path does not match {path}; refusing restore.")
        if digest(path) != rec["patched_sha256"]:
            raise ValueError(f"{path.name} changed since installation; refusing restore.")
        ready.append((key, path, rec))
    # An older app release did not create EXE backups; retain inverse restore for it.
    payloads = {}
    for key, path, rec in ready:
        if key == "exe" and "backup" in rec:
            backup = Path(rec["backup"])
            if not backup.is_file() or digest(backup) != rec["original_sha256"]:
                raise ValueError(f"Original backup missing or changed: {backup}")
            payloads[key] = backup.read_bytes()
        else:
            payloads[key] = exe_bytes(path, True) if key == "exe" else stage_upk(path, folder, True)
            if key == "exe" and hashlib.sha256(payloads[key]).hexdigest() != rec["original_sha256"]:
                raise ValueError("Inverse EXE patch does not match the original hash.")
    done = []
    patched_data = {key: path.read_bytes() for key, path, _ in ready}
    try:
        for key, path, _ in ready:
            write_atomic(path, payloads[key])
            if digest(path) != hashlib.sha256(payloads[key]).hexdigest():
                raise RuntimeError(f"Restore verification failed: {path}")
            done.append((key, path))
    except Exception:
        for key, path in reversed(done):
            write_atomic(path, patched_data[key])
        raise
    for key, path in done:
        del state["components"][key]
        save_state(exe, state)
        rec = next(r for k, p, r in ready if k == key)
        if "backup" in rec:
            Path(rec["backup"]).unlink()
        log(f"Restored {path.name}")


class Window:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP)
        self.root.geometry("760x420")
        self.base = tk.StringVar()
        self.skip_hp = tk.BooleanVar(value=False)
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="XCOM: Enemy Within — Ultrawide Fix", font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 14))
        self.row(main, "XCom-Enemy-Unknown Folder", self.base, self.choose_base)
        ttk.Checkbutton(main, text="Skip installing/restoring HP bar patch (XComGame.upk), I will patch it myself using PatcherGUI or PatchUPK.", variable=self.skip_hp).pack(anchor="w", pady=12)
        buttons = ttk.Frame(main)
        buttons.pack(anchor="w", pady=14)
        self.buttons = []
        for name, action in (("Install", install), ("Restore", restore)):
            b = ttk.Button(buttons, text=name, command=lambda a=action: self.start(a))
            b.pack(side="left", padx=(0, 10))
            self.buttons.append(b)
        self.output = tk.Text(main, height=9, state="disabled", wrap="word")
        self.output.pack(fill="both", expand=True)
        for candidate in exe_patch.default_candidates():
            if candidate.is_file():
                self.base.set(str(candidate.parent.parent.parent.parent))
                break

    def row(self, parent, label, var, browse):
        line = ttk.Frame(parent)
        line.pack(fill="x", pady=3)
        ttk.Label(line, text=label, width=32).pack(side="left")
        ttk.Entry(line, textvariable=var).pack(side="left", fill="x", expand=True)
        ttk.Button(line, text="Browse…", command=browse).pack(side="left", padx=(8, 0))

    def choose_base(self):
        value = filedialog.askdirectory(title="Select XCom-Enemy-Unknown folder")
        if value:
            self.base.set(value)

    def log(self, message):
        self.root.after(0, self._log, message)

    def _log(self, message):
        self.output.configure(state="normal")
        self.output.insert("end", message + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def start(self, action):
        base, folder, hp = Path(self.base.get()), binaries_folder(), not self.skip_hp.get()
        for b in self.buttons:
            b.configure(state="disabled")
        def work():
            try:
                action(base, folder, hp, self.log)
                self.log("Done.")
            except Exception as exc:
                self.log(f"Error: {exc}")
                self.root.after(0, lambda msg=str(exc): messagebox.showerror(APP, msg))
            finally:
                self.root.after(0, lambda: [b.configure(state="normal") for b in self.buttons])
        threading.Thread(target=work, daemon=True).start()


if __name__ == "__main__":
    Window().root.mainloop()
