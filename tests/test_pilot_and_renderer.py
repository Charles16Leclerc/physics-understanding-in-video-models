from __future__ import annotations

import importlib.util
import gzip
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from physics_bench.config import PhysicsConfig
from physics_bench.debug_renderer import render_debug_video
from physics_bench.pilot import run_pilot
from physics_bench.simulator import simulate_scene

from tests.helpers import make_scene


class PilotAndRendererTests(unittest.TestCase):
    def test_small_pilot_writes_replayable_artifacts(self) -> None:
        config = PhysicsConfig()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            artifacts = run_pilot(
                config=config,
                num_proposals=500,
                scene_seed=123,
                judgment_seed_root=456,
                output_dir=output,
                positive_sample_count=2,
                negative_sample_count=2,
                judgment_sample_count=1,
                progress_every=0,
            )
            self.assertEqual(artifacts.summary["num_proposals"], 500)
            self.assertEqual(sum(artifacts.summary["status_counts"].values()), 500)
            self.assertTrue((output / "summary.json").is_file())
            self.assertTrue((output / "accepted_scenes.jsonl.gz").is_file())
            run_manifest = json.loads((output / "config.json").read_text())
            self.assertEqual(run_manifest["config_hash"], config.config_hash())
            with gzip.open(output / "accepted_scenes.jsonl.gz", "rt", encoding="utf-8") as stream:
                first_record = json.loads(next(stream))
            self.assertEqual(first_record["dataset_version"], "v1-pilot")
            self.assertEqual(first_record["config_hash"], config.config_hash())
            with np.load(output / "pilot_arrays.npz") as arrays:
                self.assertEqual(arrays["status_code"].shape, (500,))
                self.assertEqual(arrays["p_context_xy"].shape, (500, 2))

    @unittest.skipUnless(
        importlib.util.find_spec("PIL") is not None
        and importlib.util.find_spec("imageio_ffmpeg") is not None,
        "render dependencies are not installed",
    )
    def test_mp4_renderer(self) -> None:
        config = PhysicsConfig()
        result = simulate_scene(
            make_scene(p_context_xy=(0.0, 70.0), velocity_xy=(0.0, -140.0)),
            config,
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "debug.mp4"
            render_debug_video(result, output, config, supersample=1)
            self.assertGreater(output.stat().st_size, 1000)
            self.assertIn(b"ftyp", output.read_bytes()[:64])


if __name__ == "__main__":
    unittest.main()
