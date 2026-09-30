import sys
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
        self.root = Path(self.temp.name).resolve()
        self.exe = self.root / "XEW/Binaries/Win32/XComEW.exe"
        self.exe.parent.mkdir(parents=True)
        self.clean = b"MZ" + b"\0".join((
            app.exe_patch.CURSOR_ORIGINAL, app.exe_patch.FOV_ORIGINAL,
            app.exe_patch.EXCLUSIONS_ORIGINAL)) + b"other mod"
        self.exe.write_bytes(self.clean)
        self.upk = self.root / "XEW/XComGame/CookedPCConsole/XComGame.upk"
        self.upk.parent.mkdir(parents=True)
        self.upk.write_bytes(b"original")
        app.size_file(self.upk).write_bytes(b"size")
        (self.root / "mods").mkdir()
        (self.root / "mods" / app.SCRIPT).write_bytes(b"install")
        mock = patch.object(app, "app_folder", return_value=self.root)
        mock.start()
        self.addCleanup(mock.stop)
        self.bak = self.exe.with_name("XComEW.exe.bak")
        self.script = self.root / "mods/Fix-ultrawide-UI.txt.uninstall.txt"

    def install_both(self):
        with patch.object(app, "stage_upk", return_value=(b"patched upk", b"generated undo")):
            app.install(self.root, self.root, lambda _: None)

    def test_install_restore_deletes_mods_script_preserves_exe_edits(self):
        self.install_both()
        self.assertEqual(self.script.read_bytes(), b"generated undo")
        self.assertEqual(self.bak.read_bytes(), self.clean)
        self.assertFalse((self.root / "backups").exists())
        self.exe.write_bytes(self.exe.read_bytes() + b"later modification")
        with patch.object(app, "stage_upk", return_value=(b"restored upk", None)) as stage:
            app.restore(self.root, self.root, lambda _: None)
            stage.assert_called_once_with(self.upk, self.root, self.script, uninstall=True)
        self.assertEqual(self.exe.read_bytes(), self.clean + b"later modification")
        self.assertEqual(self.upk.read_bytes(), b"restored upk")
        self.assertFalse(self.script.exists())
        self.assertFalse(app.size_file(self.upk).exists())
        self.assertEqual(self.bak.read_bytes(), self.clean)
        self.assertEqual(list((self.root / "backups").rglob("*.exe")), [])

    def test_exe_only_install_restore_without_upk_state_or_old_backup(self):
        self.upk.unlink()
        self.bak.write_bytes(b"unrelated old backup")
        with patch.object(app, "stage_upk") as stage:
            app.install_executable(self.root, None, lambda _: None)
            self.exe.write_bytes(self.exe.read_bytes() + b"later mod")
            app.restore(self.root, None, lambda _: None)
            stage.assert_not_called()
        self.assertEqual(self.exe.read_bytes(), self.clean + b"later mod")
        self.assertEqual(self.bak.read_bytes(), b"unrelated old backup")
        self.assertFalse(self.upk.exists())

    def test_restore_without_existing_backup(self):
        app.install_executable(self.root, None, lambda _: None)
        self.bak.unlink()
        patched = self.exe.read_bytes()
        app.restore(self.root, None, lambda _: None)
        self.assertEqual(self.exe.read_bytes(), self.clean)
        self.assertEqual(self.bak.read_bytes(), patched)

    def test_existing_script_skips_upk_install_even_after_other_modifications(self):
        self.install_both()
        self.upk.write_bytes(b"another mod")
        with patch.object(app, "stage_upk") as stage:
            app.install(self.root, None, lambda _: None)
            stage.assert_not_called()
        self.assertEqual(self.upk.read_bytes(), b"another mod")
        self.assertEqual(self.script.read_bytes(), b"generated undo")

    def test_failed_install_rolls_back_files_and_sidecar(self):
        real_write = app.write_atomic
        def fail_upk(path, data):
            real_write(path, data)
            if path == self.upk and data == b"patched upk":
                raise OSError("UPK write failed")
        with patch.object(app, "write_atomic", side_effect=fail_upk):
            with self.assertRaisesRegex(OSError, "UPK write failed"):
                self.install_both()
        self.assertEqual(self.exe.read_bytes(), self.clean)
        self.assertEqual(self.upk.read_bytes(), b"original")
        self.assertEqual(app.size_file(self.upk).read_bytes(), b"size")
        self.assertFalse(self.script.exists())
        self.assertEqual(self.bak.read_bytes(), self.clean)


    def test_failed_restore_keeps_script_and_rolls_back_exe(self):
        self.install_both()
        patched = self.exe.read_bytes()
        real_write = app.write_atomic
        def fail_upk(path, data):
            if path == self.upk and data == b"restored upk":
                raise OSError("write failed")
            real_write(path, data)
        with patch.object(app, "stage_upk", return_value=(b"restored upk", None)), \
                patch.object(app, "write_atomic", side_effect=fail_upk):
            with self.assertRaisesRegex(OSError, "write failed"):
                app.restore(self.root, self.root, lambda _: None)
        self.assertEqual(self.exe.read_bytes(), patched)
        self.assertEqual(self.upk.read_bytes(), b"patched upk")
        self.assertEqual(self.script.read_bytes(), b"generated undo")

    def test_failed_staging_keeps_game_and_uninstall(self):
        self.install_both()
        patched = self.exe.read_bytes()
        with patch.object(app, "stage_upk", side_effect=RuntimeError("patch failed")):
            with self.assertRaisesRegex(RuntimeError, "patch failed"):
                app.restore(self.root, self.root, lambda _: None)
        self.assertEqual(self.exe.read_bytes(), patched)
        self.assertTrue(self.script.exists())

    def test_failed_script_cleanup_rolls_back_restore(self):
        self.install_both()
        patched = self.exe.read_bytes()
        real_unlink = Path.unlink
        def fail_script(path, *args, **kwargs):
            if path == self.script:
                raise OSError("cleanup failed")
            return real_unlink(path, *args, **kwargs)
        with patch.object(app, "stage_upk", return_value=(b"restored upk", None)), \
                patch.object(Path, "unlink", fail_script):
            with self.assertRaisesRegex(OSError, "cleanup failed"):
                app.restore(self.root, self.root, lambda _: None)
        self.assertEqual(self.exe.read_bytes(), patched)
        self.assertEqual(self.upk.read_bytes(), b"patched upk")
        self.assertTrue(self.script.exists())

    def test_restore_uses_script_without_hash_checks_or_exe_snapshot(self):
        self.install_both()
        self.bak.unlink()
        self.upk.write_bytes(b"changed upk")
        with patch.object(app, "stage_upk", return_value=(b"restored upk", None)) as stage:
            app.restore(self.root, self.root, lambda _: None)
            stage.assert_called_once_with(self.upk, self.root, self.script, uninstall=True)
        self.assertEqual(self.exe.read_bytes(), self.clean)
        self.assertFalse(self.script.exists())

    def test_status_uses_exe_patterns_and_script_presence_without_tools(self):
        messages = []
        app.status(self.root, None, messages.append)
        self.assertIn("not installed", messages[-1])
        self.install_both()
        app.status(self.root, None, messages.append)
        self.assertIn("installed (uninstall script present)", messages[-1])
        self.script.unlink()
        app.status(self.root, None, messages.append)
        self.assertIn("not installed", messages[-1])


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


if __name__ == "__main__":
    unittest.main()
