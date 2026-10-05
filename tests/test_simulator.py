from __future__ import annotations

import math
import unittest

import numpy as np

from physics_bench.config import PhysicsConfig
from physics_bench.judgment import generate_judgment_pair
from physics_bench.sampler import sample_scene
from physics_bench.serialization import dumps_json
from physics_bench.simulator import simulate_scene

from tests.helpers import make_scene


class SimulatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = PhysicsConfig()

    def test_clean_positive(self) -> None:
        scene = make_scene(p_context_xy=(0.0, 70.0), velocity_xy=(0.0, -140.0))
        result = simulate_scene(scene, self.config)
        self.assertEqual(result.contact.status, "positive")
        self.assertEqual(result.contact.contact_binary, 1)
        self.assertEqual(result.collision_event.first_contact_feature, "long_face")
        self.assertEqual(result.collision_event.contact_face_id, "long_pos_n")
        self.assertTrue(12 <= result.collision_event.first_contact_frame_index <= 19)
        np.testing.assert_allclose(result.collision_event.post_collision_velocity_xy, [0.0, 140.0])
        self.assertAlmostEqual(
            np.linalg.norm(result.collision_event.post_collision_velocity_xy),
            scene.speed_px_per_s,
        )
        self.assertIsNotNone(result.labels.dynamics)

    def test_clean_negative(self) -> None:
        scene = make_scene(p_context_xy=(-100.0, 100.0), velocity_xy=(140.0, 0.0))
        result = simulate_scene(scene, self.config)
        self.assertEqual(result.contact.status, "negative")
        self.assertEqual(result.contact.contact_binary, 0)
        self.assertTrue(result.contact.negative_safe_ray_no_intersection)
        self.assertFalse(result.collision_event.future_first_contact_exists)
        self.assertIsNone(result.labels.dynamics)

    def test_too_early_collision_is_reject(self) -> None:
        scene = make_scene(p_context_xy=(0.0, 40.0), velocity_xy=(0.0, -140.0))
        result = simulate_scene(scene, self.config)
        self.assertEqual(result.contact.status, "reject")
        self.assertIn("collision_too_early", result.acceptance.rejection_reasons)
        self.assertIsNone(result.contact.contact_binary)

    def test_near_tangent_rejected_face_has_no_false_second_collision(self) -> None:
        result = simulate_scene(sample_scene(self.config, 20261005, 49696), self.config)
        self.assertEqual(result.collision_event.first_contact_feature, "short_face")
        self.assertIn("short_face_contact", result.acceptance.rejection_reasons)
        self.assertNotIn("second_collision", result.acceptance.rejection_reasons)

    def test_endpoint_margin_equality_is_numerically_ambiguous(self) -> None:
        result = simulate_scene(
            make_scene(p_context_xy=(52.5, 70.0), velocity_xy=(0.0, -140.0)),
            self.config,
        )
        self.assertEqual(result.contact.status, "reject")
        self.assertIn("endpoint_margin_violation", result.acceptance.rejection_reasons)
        self.assertIn("numerical_boundary_ambiguous", result.acceptance.rejection_reasons)

    def test_impact_angle_equality_is_numerically_ambiguous(self) -> None:
        speed = 140.0
        angle = math.radians(-10.0)
        velocity = (speed * math.cos(angle), speed * math.sin(angle))
        ttc = 0.25
        p_context = (-velocity[0] * ttc, 31.5 - velocity[1] * ttc)
        result = simulate_scene(
            make_scene(p_context_xy=p_context, velocity_xy=velocity),
            self.config,
        )
        self.assertEqual(result.contact.status, "reject")
        self.assertIn("impact_angle_too_small", result.acceptance.rejection_reasons)
        self.assertIn("numerical_boundary_ambiguous", result.acceptance.rejection_reasons)

    def test_negative_safety_tangent_is_not_negative(self) -> None:
        result = simulate_scene(
            make_scene(p_context_xy=(-100.0, 49.0), velocity_xy=(140.0, 0.0)),
            self.config,
        )
        self.assertEqual(result.contact.status, "reject")
        self.assertIn("negative_not_strictly_safe", result.acceptance.rejection_reasons)
        self.assertIn("numerical_boundary_ambiguous", result.acceptance.rejection_reasons)

    def test_frame_boundary_uses_post_velocity(self) -> None:
        collision_time = 0.5
        p_context_y = 31.5 + 140.0 * (collision_time - self.config.context_time_s)
        scene = make_scene(
            p_context_xy=(0.0, p_context_y),
            velocity_xy=(0.0, -140.0),
        )
        result = simulate_scene(scene, self.config)
        self.assertEqual(result.contact.status, "positive")
        self.assertEqual(result.collision_event.first_contact_frame_index, 12)
        np.testing.assert_allclose(result.trajectory.velocity_xy[12], [0.0, 140.0])
        np.testing.assert_allclose(result.trajectory.ball_center_xy[12], [0.0, 31.5], atol=1e-10)

    def test_json_has_no_nonfinite_values(self) -> None:
        result = simulate_scene(
            make_scene(p_context_xy=(-100.0, 100.0), velocity_xy=(140.0, 0.0)),
            self.config,
        )
        payload = dumps_json(result)
        self.assertNotIn("NaN", payload)
        self.assertNotIn("Infinity", payload)

    def test_judgment_pair_is_matched(self) -> None:
        base = simulate_scene(
            make_scene(p_context_xy=(0.0, 70.0), velocity_xy=(0.0, -140.0)),
            self.config,
        )
        pair = generate_judgment_pair(base, judgment_seed=42, config=self.config)
        self.assertTrue(pair.generated)
        self.assertIsNotNone(pair.valid)
        self.assertIsNotNone(pair.invalid)
        collision_time = base.collision_event.first_contact_time_s
        pre_mask = base.trajectory.frame_times_s <= collision_time
        np.testing.assert_array_equal(
            pair.valid.trajectory.ball_center_xy[pre_mask],
            pair.invalid.trajectory.ball_center_xy[pre_mask],
        )
        self.assertIsNotNone(pair.metadata.bad_post_velocity_xy)
        self.assertAlmostEqual(
            np.linalg.norm(pair.metadata.bad_post_velocity_xy), base.scene.speed_px_per_s
        )
        self.assertTrue(pair.metadata.alternate_barrier_feasible)
        self.assertGreater(pair.metadata.delta_deg, 5.0)
        self.assertLess(pair.metadata.delta_deg, 90.0)

    def test_randomized_accepted_scene_invariants(self) -> None:
        accepted = 0
        judgment_checked = 0
        for index in range(5000):
            result = simulate_scene(sample_scene(self.config, 20261005, index), self.config)
            if result.contact.status == "positive":
                accepted += 1
                event = result.collision_event
                self.assertEqual(event.first_contact_feature, "long_face")
                self.assertGreater(event.impact_angle_deg, self.config.min_impact_angle_deg)
                self.assertLess(
                    abs(event.contact_axis_coordinate_px),
                    self.config.barrier_half_length_px - self.config.endpoint_margin_px,
                )
                self.assertLess(float(np.dot(event.pre_collision_velocity_xy, event.contact_normal_xy)), 0.0)
                self.assertGreater(float(np.dot(event.post_collision_velocity_xy, event.contact_normal_xy)), 0.0)
                self.assertAlmostEqual(
                    np.linalg.norm(event.pre_collision_velocity_xy),
                    np.linalg.norm(event.post_collision_velocity_xy),
                    places=10,
                )
                if judgment_checked < 20:
                    pair = generate_judgment_pair(result, 10_000 + index, self.config)
                    self.assertTrue(pair.generated)
                    self.assertIsNotNone(pair.invalid)
                    self.assertTrue(pair.metadata.alternate_barrier_feasible)
                    self.assertTrue(pair.metadata.invalid_trajectory_inside_roi)
                    self.assertFalse(pair.metadata.invalid_second_collision)
                    np.testing.assert_allclose(
                        np.linalg.norm(pair.metadata.bad_post_velocity_xy),
                        result.scene.speed_px_per_s,
                        rtol=0.0,
                        atol=1e-10,
                    )
                    judgment_checked += 1
            elif result.contact.status == "negative":
                accepted += 1
                self.assertTrue(result.contact.negative_safe_ray_no_intersection)
                self.assertFalse(result.contact.true_barrier_collision_exists)
            else:
                self.assertIsNone(result.contact.contact_binary)
        self.assertGreater(accepted, 100)
        self.assertEqual(judgment_checked, 20)


if __name__ == "__main__":
    unittest.main()
