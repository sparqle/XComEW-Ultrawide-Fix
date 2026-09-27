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
import uuid
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import exe_patcher as exe_patch
from version import VERSION

APP = "XCOM EW Ultrawide Fix"
STATE = ".ultrawide-fix.json"
EXE_BACKUP = ".ultrawide-fix.original"
SCRIPT = "Fix-ultrawide-HPBars.txt"


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


def locations(base: Path, hp: bool = True) -> tuple[Path, Path]:
    base = base.resolve()
    root = base / "XEW"
    exe = root / "Binaries" / "Win32" / "XComEW.exe"
    if not exe.is_file():
        raise FileNotFoundError(f"Expected XComEW.exe at {exe}. Select the XCom-Enemy-Unknown directory.")
    upk_dir = root / "XComGame" / "CookedPCConsole"
    if not hp:
        return exe, upk_dir / "XComGame.upk"
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


def app_folder() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent


def binaries_folder() -> Path:
    return app_folder() / "binaries"


def patch_script() -> Path:
    return app_folder() / "mods" / SCRIPT


def size_file(upk: Path) -> Path:
    return upk.with_name(upk.name + ".uncompressed_size")


def restore_size_file(upk: Path, data: bytes | None) -> None:
    if data is not None:
        write_atomic(size_file(upk), data)
    else:
        size_file(upk).unlink(missing_ok=True)


def run_tool(args: list[str], cwd: Path) -> None:
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, errors="replace", timeout=300,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if p.returncode:
        raise RuntimeError(f"{Path(args[0]).name} failed ({p.returncode}):\n{(p.stdout + p.stderr)[-3000:]}")


def stage_upk(upk: Path, folder: Path, script: Path, *, uninstall: bool = False) -> tuple[bytes, bytes | None]:
    decompress = tool("DecompressLZO", folder)
    patch = tool("PatchUPK", folder)
    with tempfile.TemporaryDirectory(prefix="xcomew-ultrawide-") as temp:
        work = Path(temp)
        # Keep generated uninstall files isolated from previous installations.
        staged_script = work / script.name
        shutil.copy2(script, staged_script)
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
        run_tool([str(patch), str(staged_script), str(work)], work)
        if digest(unpacked) == before:
            raise RuntimeError("PatchUPK made no change to the staged UPK.")
        undo = None
        if not uninstall:
            generated = staged_script.with_name(staged_script.name + ".uninstall.txt")
            if not generated.is_file() or not generated.stat().st_size:
                raise RuntimeError("PatchUPK did not generate an uninstall script; no game files changed.")
            undo = generated.read_bytes()
        return unpacked.read_bytes(), undo


def install(base: Path, folder: Path, hp: bool, log) -> None:
    exe, upk = locations(base, hp)
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
    uninstall_data = None
    for key, target in pending:
        log(f"Preparing {target.name}...")
        if key == "exe":
            check_result(exe_patch.install(target, dry_run=True, show_hash=False))
        else:
            payloads[key], uninstall_data = stage_upk(target, folder, patch_script())
    # The patcher also recognizes installations made outside this UI.
    if any(key == "exe" for key, _ in pending) and exe_patch.is_fully_patched(exe_patch.inspect(exe)):
        pending = [(key, path) for key, path in pending if key != "exe"]
    originals = {key: target.read_bytes() for key, target in pending}
    written = []
    exe_backup = exe.with_name(exe.name + EXE_BACKUP)
    backup_created = False
    sidecar_data = size_file(upk).read_bytes() if "upk" in originals and size_file(upk).exists() else None
    uninstall_path = None
    try:
        if uninstall_data is not None:
            uninstall_path = app_folder() / "mods" / f"{SCRIPT}.{uuid.uuid4().hex}.uninstall.txt"
            write_atomic(uninstall_path, uninstall_data)
        if "exe" in originals:
            if exe_backup.exists():
                raise FileExistsError(f"EXE backup already exists: {exe_backup}")
            backup_created = True
        for key, target in pending:
            original_hash = hashlib.sha256(originals[key]).hexdigest()
            written.append((key, target))
            if key == "exe":
                check_result(exe_patch.install(target, dry_run=False, show_hash=False, backup_path=exe_backup))
            else:
                write_atomic(target, payloads[key])
                size_file(target).unlink(missing_ok=True)
            patched_hash = digest(target)
            if key != "exe" and patched_hash != hashlib.sha256(payloads[key]).hexdigest():
                raise RuntimeError("Installed file verification failed.")
            state["components"][key] = {"path": str(target),
                                         "original_sha256": original_hash, "patched_sha256": patched_hash}
            if key == "exe":
                state["components"][key]["backup"] = str(exe_backup)
            else:
                state["components"][key]["uninstall"] = uninstall_path.relative_to(app_folder()).as_posix()
                state["components"][key]["uninstall_sha256"] = digest(uninstall_path)
            save_state(exe, state)
            log(f"Installed {target.name}")
    except Exception:
        for key, target in reversed(written):
            write_atomic(target, originals[key])
            if key == "upk":
                restore_size_file(target, sidecar_data)
            state["components"].pop(key, None)
        save_state(exe, state)
        if backup_created and exe_backup.exists():
            exe_backup.unlink()
        if uninstall_path is not None:
            uninstall_path.unlink(missing_ok=True)
        raise


def restore(base: Path, folder: Path, hp: bool, log) -> None:
    exe, upk = locations(base, hp)
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
    # Validate and prepare both restores before changing either game file.
    payloads = {}
    for key, path, rec in ready:
        if key == "exe":
            if not rec.get("backup"):
                raise ValueError("No original EXE backup recorded; cannot restore XComEW.exe.")
            backup = Path(rec["backup"])
            if not backup.is_file() or digest(backup) != rec["original_sha256"]:
                raise ValueError(f"Original backup missing or changed: {backup}")
            payloads[key] = backup.read_bytes()
        else:
            if not rec.get("uninstall") or not rec.get("uninstall_sha256"):
                raise ValueError("No generated uninstall script recorded for this UPK installation; restore it with the original patching tool or backup.")
            script = (app_folder() / rec["uninstall"]).resolve()
            if not script.is_relative_to((app_folder() / "mods").resolve()):
                raise ValueError("Recorded uninstall script must be in the application's mods directory.")
            if not script.is_file() or digest(script) != rec["uninstall_sha256"]:
                raise ValueError(f"Uninstall script missing or changed: {script}")
            payloads[key], _ = stage_upk(path, folder, script, uninstall=True)
    done = []
    patched_data = {key: path.read_bytes() for key, path, _ in ready}
    sidecar_data = size_file(upk).read_bytes() if "upk" in patched_data and size_file(upk).exists() else None
    try:
        for key, path, rec in ready:
            done.append((key, path))
            if key == "exe":
                check_result(exe_patch.restore(path, rec["backup"], dry_run=False))
            else:
                write_atomic(path, payloads[key])
                size_file(path).unlink(missing_ok=True)
            if digest(path) != hashlib.sha256(payloads[key]).hexdigest():
                raise RuntimeError(f"Restore verification failed: {path}")
    except Exception:
        for key, path in reversed(done):
            write_atomic(path, patched_data[key])
            if key == "upk":
                restore_size_file(path, sidecar_data)
        raise
    for key, path in done:
        del state["components"][key]
        save_state(exe, state)
        rec = next(r for k, p, r in ready if k == key)
        if "backup" in rec:
            Path(rec["backup"]).unlink()
        log(f"Restored {path.name}")


def check_result(result: int) -> None:
    if result:
        raise RuntimeError(f"EXE patcher returned error {result}; see the log for details.")


def status(base: Path, folder: Path, hp: bool, log) -> None:
    exe, upk = locations(base, hp)
    check_result(exe_patch.status(exe, show_hash=True))
    if hp:
        record = load_state(exe)["components"].get("upk")
        if not record:
            log(f"{upk.name}: no managed installation")
        else:
            log(f"{upk.name}: " + ("installed" if digest(upk) == record["patched_sha256"] else "changed since installation"))


class LogStream:
    """Collect print fragments into lines for the UI's thread-safe log callback."""

    def __init__(self, log):
        self.log = log
        self.pending = ""

    def write(self, text):
        self.pending += text
        while "\n" in self.pending:
            line, self.pending = self.pending.split("\n", 1)
            self.log(line.rstrip("\r"))
        return len(text)

    def flush(self):
        if self.pending:
            self.log(self.pending)
            self.pending = ""


class Window:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP} v{VERSION}")
        self.root.geometry("760x420")
        self.base = tk.StringVar()
        self.skip_hp = tk.BooleanVar(value=False)
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text=f"XCOM: Enemy Within - Ultrawide Fix - v{VERSION}", font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 14))
        self.row(main, "XCom-Enemy-Unknown Folder", self.base, self.choose_base)
        ttk.Checkbutton(main, text="Skip installing/restoring HP bar patch (XComGame.upk), I will patch it myself using PatcherGUI or PatchUPK.", variable=self.skip_hp).pack(anchor="w", pady=12)
        buttons = ttk.Frame(main)
        buttons.pack(anchor="w", pady=14)
        self.buttons = []
        for name, action in (("Install", install), ("Restore", restore), ("Status", status)):
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
            stream = LogStream(self.log)
            try:
                with redirect_stdout(stream), redirect_stderr(stream):
                    try:
                        action(base, folder, hp, self.log)
                    finally:
                        stream.flush()
                self.log("Done.")
            except Exception as exc:
                self.log(f"Error: {exc}")
                self.root.after(0, lambda msg=str(exc): messagebox.showerror(APP, msg))
            finally:
                self.root.after(0, lambda: [b.configure(state="normal") for b in self.buttons])
        threading.Thread(target=work, daemon=True).start()


if __name__ == "__main__":
    Window().root.mainloop()
