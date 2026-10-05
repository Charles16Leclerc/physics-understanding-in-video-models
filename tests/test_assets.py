from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np

from physics_bench.assets import AssetBankConfig, generate_asset_bank


@unittest.skipUnless(importlib.util.find_spec("PIL") is not None, "Pillow is not installed")
class AssetBankTests(unittest.TestCase):
    def test_asset_bank_counts_geometry_and_replay(self) -> None:
        from PIL import Image

        config = AssetBankConfig(seed=12345, supersample=2)
        with tempfile.TemporaryDirectory() as first_directory, tempfile.TemporaryDirectory() as second_directory:
            first_root = Path(first_directory)
            second_root = Path(second_directory)
            first = generate_asset_bank(first_root, config)
            second = generate_asset_bank(second_root, config)

            self.assertTrue(first["procedural_only"])
            self.assertEqual(len(first["assets"]), 74)
            self.assertEqual(
                [asset["sha256"] for asset in first["assets"]],
                [asset["sha256"] for asset in second["assets"]],
            )

            by_kind: dict[str, list[dict[str, object]]] = {}
            for asset in first["assets"]:
                by_kind.setdefault(str(asset["kind"]), []).append(asset)
            self.assertEqual(len(by_kind["surface"]), 13)
            self.assertEqual(len(by_kind["outside_background"]), 7)
            self.assertEqual(len(by_kind["table_rail"]), 10)
            self.assertEqual(len(by_kind["ball"]), 16)
            self.assertEqual(len(by_kind["barrier"]), 10)
            self.assertEqual(len(by_kind["marking"]), 3)
            self.assertEqual(len(by_kind["background_preview"]), 13)
            self.assertEqual(len(by_kind["contact_sheet"]), 1)
            self.assertEqual(len(by_kind["object_contact_sheet"]), 1)

            ball_path = first_root / "balls" / "canonical_neutral" / "muted_red.png"
            with Image.open(ball_path) as ball:
                self.assertEqual(ball.mode, "RGBA")
                self.assertEqual(ball.size, (35, 35))
                alpha = np.asarray(ball)[:, :, 3]
                self.assertEqual(alpha[17, 17], 255)
                self.assertLess(alpha[0, 0], 10)

            barrier_path = first_root / "barriers" / "canonical_neutral" / "canonical_dark_metal.png"
            with Image.open(barrier_path) as barrier:
                self.assertEqual(barrier.mode, "RGBA")
                self.assertEqual(barrier.size, (140, 28))
                array = np.asarray(barrier)
                np.testing.assert_array_equal(array, array[::-1, ::-1])

            preview_path = first_root / "background_previews" / "billiards" / "background_0.png"
            with Image.open(preview_path) as preview:
                self.assertEqual(preview.mode, "RGB")
                self.assertEqual(preview.size, (448, 448))


if __name__ == "__main__":
    unittest.main()
