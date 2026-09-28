import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import app
import exe_patcher


def executable(host):
    return b"MZ" + ("https://telemetry." + host + "/path\0").encode("utf-16le") + b"unchanged"


class PhoneHomeTests(unittest.TestCase):
    def test_original_and_legacy_addresses_keep_binary_layout(self):
        for host in ("firaxis.com", "yiraxis.com"):
            with self.subTest(host=host):
                original = executable(host)
                patched = exe_patcher.disable_phone_home(original)
                self.assertEqual(patched, executable("xcm.invalid"))
                self.assertEqual(len(patched), len(original))
                self.assertEqual(exe_patcher.disable_phone_home(patched), patched)

    def test_all_known_addresses_are_replaced(self):
        data = ("firaxis.com\0yiraxis.com\0xcm.invalid\0").encode("utf-16le")
        self.assertEqual(exe_patcher.disable_phone_home(data), ("xcm.invalid\0" * 3).encode("utf-16le"))

    def test_unknown_or_longer_domain_is_rejected(self):
        for host in ("example.com", "firaxis.company", "yiraxis.com.example.org"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                exe_patcher.disable_phone_home(executable(host))

    def test_one_time_game_backup_and_failure_rollback(self):
        for fail in (False, True):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve()
                exe = root / "XEW/Binaries/Win32/XComEW.exe"
                exe.parent.mkdir(parents=True)
                original = executable("yiraxis.com")
                exe.write_bytes(original)
                backup = exe.with_name("XComEW.exe.bak")
                backup.write_bytes(b"first backup")
                with patch.object(app, "app_folder", return_value=root):
                    state = {"version": 2, "components": {
                        "exe": {"patched_sha256": "stale hash"},
                        "upk": {"untouched": True}}}
                    app.save_state(exe, state)
                    real_write = app.write_atomic
                    def write(path, data):
                        real_write(path, data)
                        if fail and data == executable("xcm.invalid"):
                            raise OSError("write failed")
                    with patch.object(app, "write_atomic", side_effect=write):
                        if fail:
                            with self.assertRaisesRegex(OSError, "write failed"):
                                app.disable_phone_home(root, None, lambda _: None)
                        else:
                            app.disable_phone_home(root, None, lambda _: None)
                            app.disable_phone_home(root, None, lambda _: None)
                    self.assertEqual(exe.read_bytes(), original if fail else executable("xcm.invalid"))
                    self.assertEqual(app.load_state(exe), state)
                    self.assertEqual(backup.read_bytes(), b"first backup")
                    self.assertEqual(list((root / "backups").rglob("*.exe")), [])


if __name__ == "__main__":
    unittest.main()
