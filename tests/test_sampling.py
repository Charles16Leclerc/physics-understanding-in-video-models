from __future__ import annotations

import math
import unittest

import numpy as np

from physics_bench.config import PhysicsConfig
from physics_bench.geometry import barrier_vertices, vertices_strictly_inside_box
from physics_bench.sampler import sample_scene


class SamplingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = PhysicsConfig()

    def test_replay_is_exact(self) -> None:
        first = sample_scene(self.config, 1234, 5678)
        second = sample_scene(self.config, 1234, 5678)
        self.assertEqual(first.latent_scene_id, second.latent_scene_id)
        np.testing.assert_array_equal(first.p_context_xy, second.p_context_xy)
        np.testing.assert_array_equal(first.velocity_xy, second.velocity_xy)
        np.testing.assert_array_equal(first.barrier_center_xy, second.barrier_center_xy)

    def test_ranges_and_barrier_feasibility(self) -> None:
        for index in range(2000):
            scene = sample_scene(self.config, 99, index)
            self.assertTrue(
                self.config.speed_min_cells_per_s
                <= scene.speed_cells_per_s
                < self.config.speed_max_cells_per_s
            )
            self.assertTrue(0.0 <= scene.velocity_angle_rad < 2.0 * math.pi)
            self.assertTrue(0.0 <= scene.barrier_axis_angle_rad < math.pi)
            self.assertLessEqual(abs(scene.p_context_xy[0]), self.config.center_half_width_px)
            self.assertLessEqual(abs(scene.p_context_xy[1]), self.config.center_half_height_px)
            vertices = barrier_vertices(
                scene.barrier_center_xy,
                scene.barrier_axis_angle_rad,
                scene.barrier_length_px,
                scene.barrier_width_px,
            )
            inside, _ = vertices_strictly_inside_box(
                vertices,
                self.config.roi_half_width_px,
                self.config.roi_half_height_px,
                self.config.spatial_epsilon_px,
            )
            self.assertTrue(inside)

    def test_proposal_means_are_uniform(self) -> None:
        scenes = [sample_scene(self.config, 777, index) for index in range(20_000)]
        speeds = np.asarray([scene.speed_cells_per_s for scene in scenes])
        angles = np.asarray([scene.velocity_angle_rad for scene in scenes])
        axes = np.asarray([scene.barrier_axis_angle_rad for scene in scenes])
        self.assertLess(abs(speeds.mean() - 6.75), 0.04)
        self.assertLess(abs(np.mean(np.cos(angles))), 0.02)
        self.assertLess(abs(np.mean(np.sin(angles))), 0.02)
        self.assertLess(abs(np.mean(np.cos(2.0 * axes))), 0.02)
        self.assertLess(abs(np.mean(np.sin(2.0 * axes))), 0.02)


if __name__ == "__main__":
    unittest.main()
