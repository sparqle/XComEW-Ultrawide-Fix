import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import app


class ToolsFolderTests(unittest.TestCase):
    def test_binaries_subdirectory_and_direct_folder_priority(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            nested = folder / "Binaries"
            nested.mkdir()
            (folder / "DecompressLZO.exe").touch()
            (nested / "PatchUPK.exe").touch()
            with self.assertRaises(FileNotFoundError):
                app.binaries_folder(str(folder))
            (nested / "DecompressLZO.exe").touch()
            self.assertEqual(app.binaries_folder(str(folder)), nested.resolve())
            (folder / "PatchUPK.exe").touch()
            self.assertEqual(app.binaries_folder(str(folder)), folder.resolve())

    def test_selected_folder_overrides_local_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            selected = root / "Tools with spaces"
            selected.mkdir()
            for name in ("DecompressLZO.exe", "PatchUPK.exe"):
                (selected / name).touch()
            with patch.object(app, "app_folder", return_value=root):
                self.assertEqual(app.binaries_folder(str(selected)), selected.resolve())
                with self.assertRaises(FileNotFoundError):
                    app.binaries_folder()

    def test_blank_uses_local_directory_and_requires_both_tools(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fallback = root / "third_party"
            fallback.mkdir()
            with patch.object(app, "app_folder", return_value=root):
                (fallback / "DecompressLZO.exe").touch()
                with self.assertRaisesRegex(FileNotFoundError, "PatchUPK"):
                    app.binaries_folder("   ")
                (fallback / "PatchUPK.exe").touch()
                self.assertEqual(app.binaries_folder("   "), fallback.resolve())
                with self.assertRaises(FileNotFoundError):
                    app.binaries_folder(str(root / "missing"))
