import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import game_path


class GamePathTests(unittest.TestCase):
    def test_saved_directory_takes_priority(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            selected = folder / "Game with spaces"
            selected.mkdir()
            game_path.save_game_directory(folder, str(selected))
            with patch.object(game_path, "GAME_DIRECTORIES", (folder,)):
                self.assertEqual(game_path.load_game_directory(folder), str(selected.resolve()))

    def test_empty_and_missing_paths_fall_back_in_order(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            first, second = folder / "first", folder / "second"
            first.mkdir()
            second.mkdir()
            with patch.object(game_path, "GAME_DIRECTORIES", (folder / "missing", first, second)):
                for value in ("", "   ", str(folder / "missing")):
                    self.assertEqual(game_path.find_game_directory(value), str(first))
                self.assertEqual(game_path.load_game_directory(folder), str(first))
                (folder / game_path.CONFIG).write_bytes(b'\xff')
                self.assertEqual(game_path.load_game_directory(folder), str(first))

    def test_no_match_does_not_resolve_empty_path_to_working_directory(self):
        with patch.object(game_path, "GAME_DIRECTORIES", ()):
            self.assertEqual(game_path.find_game_directory(""), "")

    def test_invalid_selection_does_not_overwrite_saved_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            game_path.save_game_directory(folder, temp)
            game_path.save_game_directory(folder, "")
            game_path.save_game_directory(folder, str(folder / "missing"))
            self.assertEqual(game_path.load_game_directory(folder), str(folder.resolve()))
