"""Windows UI for the XCOM: Enemy Within executable and HP bar UPK fixes."""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import webbrowser
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

import exe_patcher as exe_patch
from game_path import find_game_directory, load_game_directory, save_game_directory
from version import VERSION

APP = "XCOM EW Ultrawide Fix"
SCRIPT = "Fix-ultrawide-UI.txt"


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


def executable_location(base: Path) -> Path:
    base = base.resolve()
    root = base / "XEW"
    exe = root / "Binaries" / "Win32" / "XComEW.exe"
    if not exe.is_file():
        raise FileNotFoundError(f"Expected XComEW.exe at {exe}. Select the XCom-Enemy-Unknown directory.")
    return exe


def locations(base: Path) -> tuple[Path, Path]:
    exe = executable_location(base)
    root = base.resolve() / "XEW"
    upk_dir = root / "XComGame" / "CookedPCConsole"
    matches = [p for p in upk_dir.glob("*.upk") if p.name.lower() == "xcomgame.upk"] if upk_dir.is_dir() else []
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected XComGame.upk in {upk_dir}")
    return exe, matches[0]


def uninstall_script() -> Path:
    script = patch_script()
    return script.with_name(script.name + ".uninstall.txt")


def tool(name: str, folder: Path) -> Path:
    p = folder / (name + ".exe")
    if not p.is_file():
        raise FileNotFoundError(f"Missing {p}. Select a folder with DecompressLZO.exe and PatchUPK.exe.")
    return p.resolve()


def app_folder() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent


def binaries_folder(value: str = "") -> Path:
    folder = Path(value.strip()).expanduser() if value.strip() else app_folder() / "third_party"
    for candidate in (folder, folder / "Binaries"):
        if all((candidate / name).is_file() for name in ("DecompressLZO.exe", "PatchUPK.exe")):
            return candidate.resolve()
    raise FileNotFoundError(
        f"Could not find both DecompressLZO.exe and PatchUPK.exe in {folder} "
        f"or {folder / 'Binaries'}. Select a folder containing both tools."
    )


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


def install_executable(base: Path, folder: Path | None, log) -> None:
    install(base, folder, log, executable_only=True)


def install(base: Path, folder: Path | None, log, *, executable_only: bool = False) -> None:
    log("--- Installing executable only... ---" if executable_only else "--- Installing... ---")
    exe = executable_location(base)
    check_result(exe_patch.install(exe, dry_run=True, show_hash=False))
    if executable_only:
        check_result(exe_patch.install(exe, dry_run=False, show_hash=False))
        return
    script = uninstall_script()
    upk = None
    payload = undo = None
    if script.exists():
        if not script.is_file():
            raise ValueError(f"Expected an uninstall script file: {script}")
        log("XComGame.upk: already installed (uninstall script present)")
    else:
        _, upk = locations(base)
        payload, undo = stage_upk(upk, folder, patch_script())
    original_exe = exe.read_bytes()
    original_upk = upk.read_bytes() if payload is not None else None
    sidecar = size_file(upk).read_bytes() if payload is not None and size_file(upk).exists() else None
    written_upk = created_script = False
    try:
        if undo is not None:
            script.parent.mkdir(parents=True, exist_ok=True)
            created_script = True
            write_atomic(script, undo)
        check_result(exe_patch.install(exe, dry_run=False, show_hash=False))
        if payload is not None:
            written_upk = True
            write_atomic(upk, payload)
            size_file(upk).unlink(missing_ok=True)
            if upk.read_bytes() != payload:
                raise RuntimeError("Installed UPK verification failed.")
    except Exception:
        if exe.read_bytes() != original_exe:
            write_atomic(exe, original_exe)
        if written_upk:
            write_atomic(upk, original_upk)
            restore_size_file(upk, sidecar)
        if created_script:
            script.unlink(missing_ok=True)
        raise
    log("Ultrawide EXE patch installed.")
    if payload is not None:
        log("Installed XComGame.upk")


def disable_phone_home(base: Path, folder: Path | None, log) -> None:
    log("--- Disabling phone home... ---")
    exe = executable_location(base)
    original = exe.read_bytes()
    patched = exe_patch.disable_phone_home(original)
    if patched == original:
        log(f"Phone home already disabled: {exe_patch.PHONE_HOME_DISABLED}")
        return
    log(f"EXE backup: {exe_patch.make_backup(exe)}")
    try:
        write_atomic(exe, patched)
        if exe.read_bytes() != patched:
            raise RuntimeError("Phone home patch verification failed.")
    except Exception:
        write_atomic(exe, original)
        raise
    log(f"Phone home address replaced with {exe_patch.PHONE_HOME_DISABLED}")


def restore(base: Path, folder: Path | None, log) -> None:
    log("--- Restoring... ---")
    exe = executable_location(base)
    original_exe = exe.read_bytes()
    restored_exe = exe_patch.reverse_patch(original_exe)
    script = uninstall_script()
    upk = None
    payload = original_upk = sidecar = None
    if script.exists():
        _, upk = locations(base)
        if not script.is_file() or not script.stat().st_size:
            raise ValueError(f"UPK uninstall script missing or empty: {script}")
        payload, _ = stage_upk(upk, folder, script, uninstall=True)
        original_upk = upk.read_bytes()
        sidecar = size_file(upk).read_bytes() if size_file(upk).exists() else None
    if restored_exe != original_exe:
        exe_patch.make_backup(exe)
    written_exe = written_upk = False
    try:
        if restored_exe != original_exe:
            written_exe = True
            write_atomic(exe, restored_exe)
            if exe.read_bytes() != restored_exe:
                raise RuntimeError("EXE reverse patch verification failed.")
        if payload is not None:
            written_upk = True
            write_atomic(upk, payload)
            size_file(upk).unlink(missing_ok=True)
            if upk.read_bytes() != payload:
                raise RuntimeError("UPK restore verification failed.")
            script.unlink()
    except Exception:
        if written_exe:
            write_atomic(exe, original_exe)
        if written_upk:
            write_atomic(upk, original_upk)
            restore_size_file(upk, sidecar)
        raise
    log("Ultrawide EXE patch reversed; unrelated EXE modifications retained.")
    if payload is not None:
        log("Restored XComGame.upk and removed its uninstall script.")


def check_result(result: int) -> None:
    if result:
        raise RuntimeError(f"EXE patcher returned error {result}; see the log for details.")


def status(base: Path, folder: Path | None, log) -> None:
    log("--- Status ---")
    exe = executable_location(base)
    check_result(exe_patch.status(exe, show_hash=False))
    installed = uninstall_script().is_file()
    log("XComGame.upk: " + ("installed (uninstall script present)" if installed else "not installed (no uninstall script)"))


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
        # PyInstaller extracts bundled assets beside this module in one-file builds.
        resources = Path(__file__).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
        self.root.iconbitmap(default=str(resources / "assets" / "ultrawide.ico"))
        self.root.title(f"{APP} v{VERSION}")
        self.root.geometry("760x480")
        self.base = tk.StringVar()
        self.tools_path = tk.StringVar()
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text=f"XCOM: Enemy Within - Ultrawide Fix - v{VERSION}", font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 14))
        self.row(main, "XCom-Enemy-Unknown Folder", self.base, self.choose_base)
        self.row(main, "UPK tools folder", self.tools_path, self.choose_tools)
        download_line = ttk.Frame(main)
        download_line.pack(anchor="w")
        ttk.Label(download_line, text="Select the folder containing PatcherGUI or UPKUtils. Download one of these tools separately from").pack(side="left")
        self.link_font = tkfont.nametofont("TkDefaultFont").copy()
        self.link_font.configure(underline=True)
        nexus_link = ttk.Label(download_line, text="Nexusmods", foreground="#0563C1",
                               font=self.link_font, cursor="hand2", takefocus=True)
        nexus_link.pack(side="left")
        for event in ("<Button-1>", "<Return>", "<space>"):
            nexus_link.bind(event, lambda _: webbrowser.open("https://www.nexusmods.com/xcom/mods/448"))
        ttk.Label(download_line, text="or GitHub.").pack(side="left")
        buttons = ttk.Frame(main)
        buttons.pack(anchor="w", pady=14)
        self.buttons = []
        for name, action in (("Install", install), ("Restore", restore), ("Status", status)):
            b = ttk.Button(buttons, text=name, command=lambda a=action: self.start(a))
            b.pack(side="left", padx=(0, 10))
            self.buttons.append(b)
        advanced = ttk.Menubutton(buttons, text="Advanced")
        advanced_menu = tk.Menu(advanced, tearoff=False)
        for name, action in (("Install EXE only", install_executable),
                             ("Improved Disable Phone Home", disable_phone_home)):
            advanced_menu.add_command(label=name, command=lambda a=action: self.start(a))
        advanced.configure(menu=advanced_menu)
        advanced.pack(side="left", padx=(0, 10))
        self.buttons.append(advanced)
        self.output = tk.Text(main, height=9, state="disabled", wrap="word")
        self.output.pack(fill="both", expand=True)
        self.base.set(load_game_directory(app_folder()))
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def row(self, parent, label, var, browse):
        line = ttk.Frame(parent)
        line.pack(fill="x", pady=3)
        ttk.Label(line, text=label, width=32).pack(side="left")
        ttk.Entry(line, textvariable=var).pack(side="left", fill="x", expand=True)
        ttk.Button(line, text="Browse…", command=browse).pack(side="left", padx=(8, 0))

    def choose_base(self):
        initial = find_game_directory(self.base.get())
        value = filedialog.askdirectory(title="Select XCom-Enemy-Unknown folder", initialdir=initial or None)
        if value:
            self.base.set(value)
            self.save_base()

    def choose_tools(self):
        value = filedialog.askdirectory(title="Select folder containing DecompressLZO.exe and PatchUPK.exe")
        if value:
            self.tools_path.set(value)

    def save_base(self):
        try:
            save_game_directory(app_folder(), self.base.get())
        except OSError as exc:
            self.log(f"Could not save the selected folder: {exc}")

    def close(self):
        self.save_base()
        self.root.destroy()

    def log(self, message):
        self.root.after(0, self._log, message)

    def _log(self, message):
        self.output.configure(state="normal")
        self.output.insert("end", message + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def start(self, action):
        value = find_game_directory(self.base.get())
        self.base.set(value)
        if not value:
            messagebox.showerror(APP, "Could not locate XCOM. Select your XCom-Enemy-Unknown folder.")
            return
        self.save_base()
        base = Path(value)
        try:
            needs_tools = ((action is install and not uninstall_script().exists())
                           or (action is restore and uninstall_script().exists()))
            folder = binaries_folder(self.tools_path.get()) if needs_tools else None
        except (OSError, ValueError) as exc:
            messagebox.showerror(APP, f"{exc}\n\nDownload PatcherGUI or UPKUtils separately and select the folder containing DecompressLZO.exe and PatchUPK.exe.")
            return
        if action is disable_phone_home:
            try:
                original = executable_location(base).read_bytes()
                if exe_patch.disable_phone_home(original) == original:
                    self.log("--- Disabling phone home... ---")
                    self.log(f"Phone home already disabled: {exe_patch.PHONE_HOME_DISABLED}")
                    return
            except (OSError, ValueError) as exc:
                self.log(f"Error: {exc}")
                messagebox.showerror(APP, str(exc))
                return
            if not messagebox.askyesno(APP,
                    f"Improve disable phone home using the domain {exe_patch.PHONE_HOME_DISABLED}?\n\n"
                    f"PatcherGUI uses {exe_patch.PHONE_HOME_LEGACY}, which is now registered and is no longer a safe blocking address.\n\n"
                    "The new xcm.invalid address is reserved and cannot be registered. Close the game first.",
                    default="no"):
                return
        for b in self.buttons:
            b.configure(state="disabled")
        def work():
            stream = LogStream(self.log)
            try:
                with redirect_stdout(stream), redirect_stderr(stream):
                    try:
                        action(base, folder, self.log)
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
