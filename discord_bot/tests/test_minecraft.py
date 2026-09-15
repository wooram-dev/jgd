import json
import tempfile
import unittest
from pathlib import Path

from utils.minecraft import load_known_minecraft_players, parse_numismatics_balance


class MinecraftPlayerCacheTests(unittest.TestCase):
    def test_loads_valid_unique_names(self):
        entries = [
            {"name": "PlayerTwo", "uuid": "ignored"},
            {"name": "playerone", "uuid": "ignored"},
            {"name": "PLAYERONE", "uuid": "ignored"},
            {"name": "invalid player", "uuid": "ignored"},
            {"uuid": "missing-name"},
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "usercache.json"
            path.write_text(json.dumps(entries), encoding="utf-8")
            self.assertEqual(
                load_known_minecraft_players(str(path)),
                ["playerone", "PlayerTwo"],
            )


class NumismaticsBalanceParserTests(unittest.TestCase):
    def test_parses_spur_balance(self):
        self.assertEqual(
            parse_numismatics_balance("PlayerOne", "PlayerOne has 1234 spurs."),
            1234,
        )

    def test_parses_singular_and_formatting(self):
        self.assertEqual(
            parse_numismatics_balance("PlayerOne", "\x1b[32mPlayerOne has 1 spur.\x1b[0m"),
            1,
        )

    def test_rejects_unrelated_response(self):
        self.assertIsNone(
            parse_numismatics_balance("PlayerOne", "Could not find account for PlayerOne."),
        )


if __name__ == "__main__":
    unittest.main()
