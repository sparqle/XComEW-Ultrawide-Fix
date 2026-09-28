import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import exe_patcher as exe


class ExeRestoreTests(unittest.TestCase):
    def setUp(self):
        self.clean = b"MZ" + b"\0".join((exe.CURSOR_ORIGINAL, exe.FOV_ORIGINAL, exe.EXCLUSIONS_ORIGINAL))
        self.patched = b"MZ" + b"\0".join((exe.CURSOR_PATCHED, exe.FOV_PATCHED, exe.EXCLUSIONS_PATCHED))

    def test_reverse_preserves_phone_home_and_other_mods(self):
        other = "xcm.invalid\0".encode("utf-16le") + b"unrelated mod"
        self.assertEqual(exe.reverse_patch(self.patched + other), self.clean + other)
        self.assertEqual(exe.reverse_patch(self.clean + other), self.clean + other)

    def test_reverse_handles_partial_known_patch(self):
        partial = self.clean.replace(exe.FOV_ORIGINAL, exe.FOV_PATCHED)
        self.assertEqual(exe.reverse_patch(partial), self.clean)

    def test_reverse_refuses_unknown_or_duplicate_blocks(self):
        for data in (self.patched + exe.CURSOR_PATCHED,
                     self.patched.replace(exe.FOV_PATCHED, b"unknown patch")):
            with self.assertRaises(ValueError):
                exe.reverse_patch(data)

    def test_install_failure_rolls_back_current_bytes_not_old_bak(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "XComEW.exe"
            path.write_bytes(self.clean)
            backup = path.with_name("XComEW.exe.bak")
            backup.write_bytes(b"old snapshot")
            real_inspect = exe.inspect
            calls = []
            def inspect(target):
                calls.append(True)
                if len(calls) == 2:
                    raise RuntimeError("verification failed")
                return real_inspect(target)
            with patch.object(exe, "inspect", side_effect=inspect):
                with self.assertRaisesRegex(RuntimeError, "verification failed"):
                    exe.install(path, dry_run=False, show_hash=False)
            self.assertEqual(path.read_bytes(), self.clean)
            self.assertEqual(backup.read_bytes(), b"old snapshot")

    def test_restore_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "XComEW.exe"
            path.write_bytes(self.patched)
            self.assertEqual(exe.restore(path, dry_run=True), 0)
            self.assertEqual(path.read_bytes(), self.patched)
            self.assertFalse(path.with_name("XComEW.exe.bak").exists())


if __name__ == "__main__":
    unittest.main()
