from __future__ import annotations

import math
import unittest

import numpy as np

from physics_bench.config import PhysicsConfig
from physics_bench.geometry import (
    first_contact_moving_point_rounded_rectangle,
    ray_min_distance_to_rectangle,
    reflect_velocity,
)


class GeometryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = PhysicsConfig()
        self.center = np.zeros(2, dtype=np.float64)

    def contact(self, origin: tuple[float, float], direction: tuple[float, float]):
        return first_contact_moving_point_rounded_rectangle(
            np.asarray(origin, dtype=np.float64),
            np.asarray(direction, dtype=np.float64),
            self.center,
            0.0,
            self.config.barrier_length_px,
            self.config.barrier_width_px,
            self.config.ball_radius_px,
            self.config.spatial_epsilon_px,
            self.config.angle_epsilon_rad,
        )

    def test_exact_long_face_contact(self) -> None:
        hit = self.contact((0.0, 100.0), (0.0, -1.0))
        self.assertEqual(hit.feature, "long_face")
        self.assertEqual(hit.face_id, "long_pos_n")
        self.assertAlmostEqual(hit.distance_px, 68.5)
        np.testing.assert_allclose(hit.center_xy, [0.0, 31.5], atol=1e-12)
        np.testing.assert_allclose(hit.surface_xy, [0.0, 14.0], atol=1e-12)
        np.testing.assert_allclose(hit.normal_xy, [0.0, 1.0], atol=1e-12)
        self.assertAlmostEqual(hit.impact_angle_deg, 90.0)

    def test_exact_short_face_contact(self) -> None:
        hit = self.contact((100.0, 0.0), (-1.0, 0.0))
        self.assertEqual(hit.feature, "short_face")
        self.assertEqual(hit.face_id, "short_pos_t")
        self.assertAlmostEqual(hit.distance_px, 12.5)
        np.testing.assert_allclose(hit.surface_xy, [70.0, 0.0], atol=1e-12)

    def test_exact_corner_contact(self) -> None:
        radial = np.asarray([1.0, 1.0], dtype=np.float64) / math.sqrt(2.0)
        corner = np.asarray([70.0, 14.0], dtype=np.float64)
        origin = corner + (self.config.ball_radius_px + 10.0) * radial
        hit = self.contact(tuple(origin), tuple(-radial))
        self.assertEqual(hit.feature, "corner")
        self.assertEqual(hit.face_id, "corner_pos_t_pos_n")
        self.assertAlmostEqual(hit.distance_px, 10.0, places=9)
        np.testing.assert_allclose(hit.surface_xy, corner, atol=1e-9)
        self.assertIsNone(hit.normal_xy)

    def test_tangent_corner_is_ambiguous(self) -> None:
        hit = self.contact((100.0, 14.0 + self.config.ball_radius_px), (-1.0, 0.0))
        self.assertEqual(hit.feature, "ambiguous")
        self.assertTrue(hit.numerical_ambiguous)

    def test_no_contact(self) -> None:
        hit = self.contact((-100.0, 100.0), (1.0, 0.0))
        self.assertEqual(hit.feature, "none")

    def test_ray_minimum_distance(self) -> None:
        distance = ray_min_distance_to_rectangle(
            np.asarray([-100.0, 100.0]),
            np.asarray([1.0, 0.0]),
            self.center,
            0.0,
            self.config.barrier_length_px,
            self.config.barrier_width_px,
            self.config.angle_epsilon_rad,
        )
        self.assertAlmostEqual(distance, 86.0)

    def test_elastic_reflection_preserves_speed(self) -> None:
        incoming = np.asarray([30.0, -40.0])
        outgoing = reflect_velocity(incoming, np.asarray([0.0, 1.0]))
        np.testing.assert_allclose(outgoing, [30.0, 40.0])
        self.assertAlmostEqual(np.linalg.norm(incoming), np.linalg.norm(outgoing))


if __name__ == "__main__":
    unittest.main()
