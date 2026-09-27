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
        app.save_state(self.exe, {"version": 2, "components": {
            "exe": {"path": str(self.exe), "patched_sha256": app.digest(self.exe)}}})
        mock = patch.object(app, "app_folder", return_value=self.root)
        mock.start()
        self.addCleanup(mock.stop)

    def test_install_and_restore_use_saved_script(self):
        with patch.object(app, "stage_upk", return_value=(b"patched", b"generated undo")):
            app.install(self.root, self.root, True, lambda _: None)
        self.assertFalse(app.size_file(self.upk).exists())
        record = app.load_state(self.exe)["components"]["upk"]
        script = self.root / record["uninstall"]
        self.assertEqual(script.read_bytes(), b"generated undo")
        # Restore only UPK; the EXE is an externally managed fixture.
        state = app.load_state(self.exe)
        del state["components"]["exe"]
        app.save_state(self.exe, state)
        with patch.object(app, "stage_upk", return_value=(b"restored unpacked", None)) as stage:
            app.restore(self.root, self.root, True, lambda _: None)
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
                app.install(self.root, self.root, True, lambda _: None)
        self.assertEqual(self.upk.read_bytes(), b"original")
        self.assertEqual(app.size_file(self.upk).read_bytes(), b"size")
        self.assertEqual(list((self.root / "mods").glob("*.uninstall.txt")), [])

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
