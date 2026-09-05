from __future__ import annotations

import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from stable_identity import source_content_hash  # noqa: E402


class StableIdentityTests(unittest.TestCase):
    def test_source_hash_frames_embedded_separator_bytes(self) -> None:
        self.assertNotEqual(
            source_content_hash("alpha", "beta\x1fgamma"),
            source_content_hash("alpha\x1fbeta", "gamma"),
        )


if __name__ == "__main__":
    unittest.main()
