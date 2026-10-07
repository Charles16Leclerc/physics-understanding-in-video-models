from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

import numpy as np

from physics_bench.config import PhysicsConfig
from physics_bench.render_dataset import (
    render_balanced_contact_dataset,
    select_balanced_contact_indices,
)
from physics_bench.renderer import AssetBank, iter_rendered_frames, sample_appearance_spec
from physics_bench.simulator import simulate_scene

from tests.helpers import make_scene


ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets" / "renderer" / "v1"


@unittest.skipUnless(importlib.util.find_spec("PIL") is not None, "Pillow is not installed")
class ProductionRendererTests(unittest.TestCase):
    def test_appearance_sampling_is_replayable_and_label_agnostic(self) -> None:
        bank = AssetBank(ASSET_ROOT)
        first = sample_appearance_spec(
            latent_scene_id="ls-test",
            render_seed=123,
            asset_bank=bank,
            render_family="air_hockey",
        )
        second = sample_appearance_spec(
            latent_scene_id="ls-test",
            render_seed=123,
            asset_bank=bank,
            render_family="air_hockey",
        )
        self.assertEqual(first, second)
        self.assertEqual(first.render_regime, "diverse")
        self.assertIsNotNone(first.marking_style_id)
        self.assertFalse(first.motion_blur)
        self.assertFalse(first.directional_light)
        self.assertFalse(first.cast_shadow)

        canonical = sample_appearance_spec(
            latent_scene_id="ls-test",
            render_seed=999,
            asset_bank=bank,
            render_family="canonical_neutral",
        )
        self.assertEqual(canonical.render_regime, "canonical")
        self.assertEqual(canonical.global_brightness_gain, 1.0)
        self.assertEqual(canonical.ball_hue_jitter_deg, 0.0)

    def test_frames_have_expected_shape_and_temporal_change(self) -> None:
        config = PhysicsConfig()
        result = simulate_scene(
            make_scene(p_context_xy=(0.0, 70.0), velocity_xy=(0.0, -140.0)),
            config,
        )
        bank = AssetBank(ASSET_ROOT)
        appearance = sample_appearance_spec(
            latent_scene_id=result.scene.latent_scene_id,
            render_seed=456,
            asset_bank=bank,
            render_family="billiards",
        )
        frames = list(
            iter_rendered_frames(
                result.trajectory,
                appearance,
                bank,
                config,
                supersample=1,
            )
        )
        self.assertEqual(len(frames), config.num_frames)
        self.assertEqual(frames[0].shape, (448, 448, 3))
        self.assertEqual(frames[0].dtype, np.uint8)
        self.assertGreater(float(np.mean(np.abs(frames[0].astype(float) - frames[-1]))), 0.01)

    def test_positive_world_barrier_angle_has_negative_image_slope(self) -> None:
        config = PhysicsConfig()
        result = simulate_scene(
            make_scene(
                p_context_xy=(150.0, 100.0),
                velocity_xy=(1.0, 0.0),
                barrier_axis_angle_rad=math.pi / 4.0,
            ),
            config,
        )
        bank = AssetBank(ASSET_ROOT)
        appearance = sample_appearance_spec(
            latent_scene_id=result.scene.latent_scene_id,
            render_seed=654,
            asset_bank=bank,
            render_family="canonical_neutral",
        )
        frame = next(
            iter_rendered_frames(
                result.trajectory,
                appearance,
                bank,
                config,
                supersample=1,
            )
        )
        crop = frame[145:303, 145:303]
        dark = np.mean(crop, axis=2) < 150.0
        y_indices, x_indices = np.nonzero(dark)
        covariance = float(np.cov(x_indices, y_indices)[0, 1])
        self.assertLess(covariance, 0.0)

    def test_balanced_selection_replays_exactly(self) -> None:
        config = PhysicsConfig()
        first = select_balanced_contact_indices(
            config=config,
            num_proposals=1_000,
            scene_seed=20_261_005,
            selection_seed=777,
            max_per_class=4,
        )
        second = select_balanced_contact_indices(
            config=config,
            num_proposals=1_000,
            scene_seed=20_261_005,
            selection_seed=777,
            max_per_class=4,
        )
        self.assertEqual(first, second)
        self.assertEqual(len(first.positive_proposal_indices), 4)
        self.assertEqual(len(first.negative_proposal_indices), 4)
        self.assertTrue(
            set(first.positive_proposal_indices).isdisjoint(first.negative_proposal_indices)
        )

    @unittest.skipUnless(
        importlib.util.find_spec("imageio_ffmpeg") is not None,
        "imageio-ffmpeg is not installed",
    )
    def test_small_balanced_dataset_writes_mp4_and_unsplit_manifest(self) -> None:
        import imageio_ffmpeg

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary = render_balanced_contact_dataset(
                config=PhysicsConfig(),
                num_proposals=500,
                scene_seed=20_261_005,
                selection_seed=888,
                render_seed_root=999,
                output_dir=root,
                asset_bank_root=ASSET_ROOT,
                families=("canonical_neutral",),
                max_per_class=1,
                supersample=1,
            )
            self.assertEqual(summary["rendered_status_counts"], {"positive": 1, "negative": 1})
            rows = [
                json.loads(line)
                for line in (root / "manifests" / "contact.jsonl").read_text().splitlines()
            ]
            self.assertEqual(len(rows), 2)
            self.assertEqual({row["contact_binary"] for row in rows}, {0, 1})
            self.assertTrue(all(row["split"] is None for row in rows))
            for row in rows:
                video_path = root / row["video_path"]
                self.assertGreater(video_path.stat().st_size, 1_000)
                self.assertIn(b"ftyp", video_path.read_bytes()[:64])
                frame_count, duration_s = imageio_ffmpeg.count_frames_and_secs(str(video_path))
                self.assertEqual(frame_count, 24)
                self.assertAlmostEqual(duration_s, 1.0, places=2)


if __name__ == "__main__":
    unittest.main()
