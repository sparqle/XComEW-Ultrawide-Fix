import hashlib
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

    def test_backup_managed_state_and_failure_rollback(self):
        for fail in (False, True):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve()
                exe = root / "XEW/Binaries/Win32/XComEW.exe"
                exe.parent.mkdir(parents=True)
                original = executable("yiraxis.com")
                exe.write_bytes(original)
                original_hash = hashlib.sha256(original).hexdigest()
                with patch.object(app, "app_folder", return_value=root):
                    state = {"version": 2, "components": {
                        "exe": {"path": str(exe), "patched_sha256": original_hash,
                                "backup": "backups/original.exe", "original_sha256": "original hash"},
                        "upk": {"untouched": True}}}
                    app.save_state(exe, state)
                    real_save = app.save_state
                    calls = []

                    def save(*args):
                        calls.append(True)
                        if fail and len(calls) == 1:
                            raise OSError("state write failed")
                        real_save(*args)

                    with patch.object(app, "save_state", side_effect=save):
                        if fail:
                            with self.assertRaisesRegex(OSError, "state write failed"):
                                app.disable_phone_home(root, None, lambda _: None)
                        else:
                            app.disable_phone_home(root, None, lambda _: None)
                            app.disable_phone_home(root, None, lambda _: None)
                    self.assertEqual(exe.read_bytes(), original if fail else executable("xcm.invalid"))
                    saved = app.load_state(exe)["components"]
                    self.assertEqual(saved["exe"]["patched_sha256"], app.digest(exe))
                    self.assertEqual(saved["exe"]["backup"], "backups/original.exe")
                    self.assertEqual(saved["upk"], {"untouched": True})
                    backups = list(app.backup_directory(exe).glob("XComEW.phone-home-*.exe"))
                    self.assertEqual(len(backups), 1)
                    self.assertEqual(backups[0].read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
