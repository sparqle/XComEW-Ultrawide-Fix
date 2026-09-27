import sys
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import app


class UpkWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.exe = self.root / "XEW/Binaries/Win32/XComEW.exe"
        self.exe.parent.mkdir(parents=True)
        self.exe.write_bytes(b"exe")
        self.upk = self.root / "XEW/XComGame/CookedPCConsole/XComGame.upk"
        self.upk.parent.mkdir(parents=True)
        self.upk.write_bytes(b"original")
        app.size_file(self.upk).write_bytes(b"size")
        (self.root / "mods").mkdir()
        (self.root / "mods" / app.SCRIPT).write_bytes(b"install")
        mock = patch.object(app, "app_folder", return_value=self.root)
        mock.start()
        self.addCleanup(mock.stop)
        app.save_state(self.exe, {"version": 2, "components": {
            "exe": {"path": str(self.exe), "patched_sha256": app.digest(self.exe)}}})

    def test_install_and_restore_use_saved_script(self):
        with patch.object(app, "stage_upk", return_value=(b"patched", b"generated undo")):
            app.install(self.root, self.root, lambda _: None)
        self.assertFalse(app.size_file(self.upk).exists())
        record = app.load_state(self.exe)["components"]["upk"]
        script = self.root / record["uninstall"]
        self.assertTrue(script.is_relative_to(self.root / "backups"))
        self.assertEqual(script.read_bytes(), b"generated undo")
        # Restore only UPK; the EXE is an externally managed fixture.
        state = app.load_state(self.exe)
        del state["components"]["exe"]
        app.save_state(self.exe, state)
        with patch.object(app, "stage_upk", return_value=(b"restored unpacked", None)) as stage:
            app.restore(self.root, self.root, lambda _: None)
            stage.assert_called_once_with(self.upk, self.root, script, uninstall=True)
        self.assertFalse(app.size_file(self.upk).exists())
        self.assertEqual(self.upk.read_bytes(), b"restored unpacked")

    def test_failed_commit_restores_upk_and_sidecar(self):
        real_save = app.save_state
        calls = 0

        def fail_once(*args):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError("state write failed")
            return real_save(*args)

        with patch.object(app, "stage_upk", return_value=(b"patched", b"undo")), \
                patch.object(app, "save_state", side_effect=fail_once):
            with self.assertRaises(OSError):
                app.install(self.root, self.root, lambda _: None)
        self.assertEqual(self.upk.read_bytes(), b"original")
        self.assertEqual(app.size_file(self.upk).read_bytes(), b"size")
        self.assertEqual(list((self.root / "mods").glob("*.uninstall.txt")), [])
        self.assertEqual(list((self.root / "backups").rglob("*.uninstall.txt")), [])

    def test_exe_and_uninstall_share_local_backup_directory(self):
        app.save_state(self.exe, {"version": 2, "components": {}})

        def install_exe(path, *, dry_run, show_hash, backup_path=None):
            if not dry_run:
                backup_path.write_bytes(path.read_bytes())
                path.write_bytes(b"patched exe")
            return 0

        def restore_exe(path, backup, *, dry_run):
            path.write_bytes(Path(backup).read_bytes())
            return 0

        with patch.object(app.exe_patch, "install", side_effect=install_exe), \
                patch.object(app.exe_patch, "inspect"), \
                patch.object(app.exe_patch, "is_fully_patched", return_value=False), \
                patch.object(app, "stage_upk", return_value=(b"patched", b"undo")):
            app.install(self.root, self.root, lambda _: None)
        state = app.load_state(self.exe)
        backup = self.root / state["components"]["exe"]["backup"]
        script = self.root / state["components"]["upk"]["uninstall"]
        self.assertEqual(backup.parent, script.parent)
        self.assertEqual(script.name, "Fix-ultrawide-Tactical.uninstall.txt")
        self.assertTrue((backup.parent / app.STATE).is_file())
        self.assertFalse((self.exe.parent / app.STATE).exists())
        self.assertTrue(backup.is_relative_to(self.root / "backups"))
        self.assertEqual(backup.read_bytes(), b"exe")
        with patch.object(app.exe_patch, "restore", side_effect=restore_exe), \
                patch.object(app, "stage_upk", return_value=(b"original", None)):
            app.restore(self.root, self.root, lambda _: None)
        self.assertEqual(self.exe.read_bytes(), b"exe")
        self.assertEqual(self.upk.read_bytes(), b"original")

    def test_legacy_mods_uninstall_is_rejected(self):
        script = self.root / "mods" / "legacy.uninstall.txt"
        script.write_bytes(b"undo")
        app.save_state(self.exe, {"version": 2, "components": {"upk": {
            "path": str(self.upk), "patched_sha256": app.digest(self.upk),
            "uninstall": "mods/legacy.uninstall.txt", "uninstall_sha256": app.digest(script)}}})
        with patch.object(app, "stage_upk", return_value=(b"restored", None)) as stage:
            with self.assertRaisesRegex(ValueError, "backups directory"):
                app.restore(self.root, self.root, lambda _: None)
            stage.assert_not_called()

    def test_backup_paths_outside_local_directory_are_rejected(self):
        for recorded in (str(self.exe), "mods/undo.txt", "backups/../undo.txt"):
            with self.subTest(recorded=recorded):
                with self.assertRaisesRegex(ValueError, "backups directory"):
                    app.backup_file(recorded)

    def test_stage_captures_generated_uninstall(self):
        def fake_tool(args, cwd):
            if args[0] == "DecompressLZO":
                Path(args[2]).write_bytes(b"unpacked")
            else:
                (cwd / "XComGame.upk").write_bytes(b"patched")
                Path(args[1] + ".uninstall.txt").write_bytes(b"generated")

        with patch.object(app, "tool", side_effect=lambda name, folder: name), \
                patch.object(app, "run_tool", side_effect=fake_tool):
            result = app.stage_upk(self.upk, self.root, app.patch_script())
        self.assertEqual(result, (b"patched", b"generated"))
        self.assertEqual(self.upk.read_bytes(), b"original")

    def make_force_backup(self, name, timestamp):
        directory = self.root / "backups" / name
        directory.mkdir(parents=True, exist_ok=True)
        for filename, data in (("XComEW.exe", b"original exe"), ("Fix-ultrawide-Tactical.uninstall.txt", b"undo")):
            path = directory / filename
            path.write_bytes(data)
            os.utime(path, (timestamp, timestamp))
        return directory

    def test_force_selects_latest_complete_backup_without_state(self):
        self.make_force_backup("older", 100)
        newest = self.make_force_backup("newer", 200)
        incomplete = self.make_force_backup("incomplete", 300)
        (incomplete / "XComEW.exe").unlink()
        self.assertEqual(app.latest_backup(), newest)
        with patch.object(app, "stage_upk", return_value=(b"restored upk", None)) as stage:
            app.force_restore(self.root, self.root, lambda _: None)
            self.assertEqual(stage.call_args.args[2].parent, newest)
        self.assertEqual(self.exe.read_bytes(), b"original exe")
        self.assertEqual(self.upk.read_bytes(), b"restored upk")
        self.assertTrue((newest / "XComEW.exe").exists())
        self.assertFalse((app.backup_directory(self.exe) / app.STATE).exists())

    def test_force_staging_failure_does_not_change_game(self):
        self.make_force_backup("newest", 200)
        with patch.object(app, "stage_upk", side_effect=RuntimeError("patch failed")):
            with self.assertRaisesRegex(RuntimeError, "patch failed"):
                app.force_restore(self.root, self.root, lambda _: None)
        self.assertEqual(self.exe.read_bytes(), b"exe")
        self.assertEqual(self.upk.read_bytes(), b"original")

    def test_force_write_failure_rolls_back_both_files(self):
        self.make_force_backup("newest", 200)
        real_write = app.write_atomic
        def fail_upk(path, data):
            if path == self.upk and data == b"restored upk":
                raise OSError("write failed")
            real_write(path, data)
        with patch.object(app, "stage_upk", return_value=(b"restored upk", None)), \
                patch.object(app, "write_atomic", side_effect=fail_upk):
            with self.assertRaisesRegex(OSError, "write failed"):
                app.force_restore(self.root, self.root, lambda _: None)
        self.assertEqual(self.exe.read_bytes(), b"exe")
        self.assertEqual(self.upk.read_bytes(), b"original")
        self.assertEqual(app.size_file(self.upk).read_bytes(), b"size")

    def test_force_rejects_changed_backup(self):
        directory = self.make_force_backup("newest", 200)
        (directory / app.STATE).write_text('{"components":{"exe":{"original_sha256":"wrong"}}}')
        with patch.object(app, "stage_upk") as stage:
            with self.assertRaisesRegex(ValueError, "Backup file changed"):
                app.force_restore(self.root, self.root, lambda _: None)
            stage.assert_not_called()

    def test_force_requires_complete_backup(self):
        with self.assertRaisesRegex(FileNotFoundError, "No complete backup"):
            app.latest_backup()


if __name__ == "__main__":
    unittest.main()
