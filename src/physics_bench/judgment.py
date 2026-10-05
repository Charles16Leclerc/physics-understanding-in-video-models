"""Matched Reflection Judgment pair generation."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from .config import PhysicsConfig
from .geometry import (
    barrier_basis,
    rotate_points,
    strict_box_status,
    unit,
    vertices_strictly_inside_box,
    world_to_barrier_local,
    wrap_angle_2pi,
    wrap_axis_angle_pi,
)
from .models import (
    JudgmentLabels,
    JudgmentPair,
    JudgmentVariant,
    JudgmentVariantMetadata,
    SimulationResult,
)
from .sampler import validate_uint64
from .simulator import has_second_collision, trajectory_with_post_velocity


JUDGMENT_STREAM_CODE = 100


@dataclass(frozen=True, slots=True)
class _ValidBadCandidate:
    sign: int
    delta_rad: float
    bad_angle_rad: float
    bad_velocity_xy: np.ndarray
    bad_outgoing_angle_deg: float
    alternate_rotation_rad: float
    alternate_axis_angle_rad: float
    alternate_vertices_xy: np.ndarray
    final_center_xy: np.ndarray


def _judgment_rng(base: SimulationResult, judgment_seed: int) -> np.random.Generator:
    validate_uint64(judgment_seed, "judgment_seed")
    sequence = np.random.SeedSequence(
        [judgment_seed, base.scene.scene_seed, base.scene.proposal_index, JUDGMENT_STREAM_CODE]
    )
    return np.random.Generator(np.random.PCG64(sequence))


def _evaluate_bad_candidate(
    base: SimulationResult,
    delta_rad: float,
    sign: int,
    config: PhysicsConfig,
) -> _ValidBadCandidate | None:
    event = base.collision_event
    if (
        event.first_contact_feature != "long_face"
        or event.first_contact_time_s is None
        or event.ball_center_at_contact_xy is None
        or event.contact_normal_xy is None
        or event.post_collision_angle_rad is None
    ):
        return None

    speed = base.scene.speed_px_per_s
    bad_angle = wrap_angle_2pi(event.post_collision_angle_rad + sign * delta_rad)
    bad_velocity = speed * np.asarray(
        [math.cos(bad_angle), math.sin(bad_angle)], dtype=np.float64
    )
    bad_direction = unit(bad_velocity)

    # The invalid branch must visibly leave the real active face.
    outward_component = float(np.dot(bad_direction, event.contact_normal_xy))
    if outward_component <= math.sin(config.angle_epsilon_rad):
        return None

    _, canonical_normal = barrier_basis(base.scene.barrier_axis_angle_rad)
    bad_outgoing_angle = math.asin(
        min(1.0, abs(float(np.dot(bad_direction, canonical_normal))))
    )
    if bad_outgoing_angle <= config.min_bad_outgoing_angle_rad:
        return None
    if (
        abs(bad_outgoing_angle - config.min_bad_outgoing_angle_rad)
        <= config.angle_epsilon_rad
    ):
        return None

    final_center = event.ball_center_at_contact_xy + bad_velocity * (
        config.duration_s - event.first_contact_time_s
    )
    if (
        strict_box_status(
            final_center,
            config.center_half_width_px,
            config.center_half_height_px,
            config.spatial_epsilon_px,
        )
        != "inside"
    ):
        return None
    if has_second_collision(
        event.ball_center_at_contact_xy,
        bad_velocity,
        event.first_contact_time_s,
        base.scene,
        config,
        event.contact_normal_xy,
    ):
        return None

    rotation = sign * delta_rad / 2.0
    alternate_vertices = rotate_points(
        base.trajectory.barrier_vertices_xy,
        event.ball_center_at_contact_xy,
        rotation,
    )
    alternate_inside, alternate_boundary = vertices_strictly_inside_box(
        alternate_vertices,
        config.roi_half_width_px,
        config.roi_half_height_px,
        config.spatial_epsilon_px,
    )
    if not alternate_inside or alternate_boundary:
        return None

    alternate_center = rotate_points(
        base.scene.barrier_center_xy[np.newaxis, :],
        event.ball_center_at_contact_xy,
        rotation,
    )[0]
    alternate_axis = wrap_axis_angle_pi(base.scene.barrier_axis_angle_rad + rotation)
    alternate_tangent, alternate_normal_canonical = barrier_basis(alternate_axis)
    local_contact_center = world_to_barrier_local(
        event.ball_center_at_contact_xy,
        alternate_center,
        alternate_tangent,
        alternate_normal_canonical,
    )
    expected_normal_distance = config.barrier_half_width_px + config.ball_radius_px
    if (
        abs(abs(float(local_contact_center[1])) - expected_normal_distance)
        > config.spatial_epsilon_px
    ):
        return None
    endpoint_difference = (
        config.barrier_half_length_px
        - config.endpoint_margin_px
        - abs(float(local_contact_center[0]))
    )
    if endpoint_difference <= config.spatial_epsilon_px:
        return None

    active_sign = 1.0 if local_contact_center[1] > 0.0 else -1.0
    alternate_active_normal = active_sign * alternate_normal_canonical
    incoming_direction = unit(base.scene.velocity_xy)
    incoming_component = float(np.dot(incoming_direction, alternate_active_normal))
    if incoming_component >= -math.sin(config.angle_epsilon_rad):
        return None
    alternate_impact = math.asin(min(1.0, abs(incoming_component)))
    if alternate_impact <= config.min_impact_angle_rad:
        return None

    # Confirm that the alternate legal reflection produces the proposed bad direction.
    reflected = base.scene.velocity_xy - 2.0 * float(
        np.dot(base.scene.velocity_xy, alternate_active_normal)
    ) * alternate_active_normal
    reflected_angle = wrap_angle_2pi(math.atan2(reflected[1], reflected[0]))
    angular_error = abs(
        math.atan2(math.sin(reflected_angle - bad_angle), math.cos(reflected_angle - bad_angle))
    )
    if angular_error > 10.0 * config.angle_epsilon_rad:
        return None

    return _ValidBadCandidate(
        sign=sign,
        delta_rad=delta_rad,
        bad_angle_rad=bad_angle,
        bad_velocity_xy=bad_velocity,
        bad_outgoing_angle_deg=math.degrees(bad_outgoing_angle),
        alternate_rotation_rad=rotation,
        alternate_axis_angle_rad=alternate_axis,
        alternate_vertices_xy=alternate_vertices,
        final_center_xy=final_center,
    )


def _failed_pair(
    base: SimulationResult,
    judgment_seed: int,
    attempts: int,
) -> JudgmentPair:
    pair_id = f"{base.scene.latent_scene_id}:pair:{judgment_seed:016x}"
    metadata = JudgmentVariantMetadata(
        judgment_pair_id=pair_id,
        latent_scene_id=base.scene.latent_scene_id,
        judgment_pair_generated=False,
        valid_trajectory_variant_id=base.trajectory.trajectory_variant_id,
        invalid_trajectory_variant_id=None,
        judgment_seed=judgment_seed,
        violation_sampling_attempt_count=attempts,
        delta_deg=None,
        delta_rad=None,
        sign=None,
        bad_post_velocity_angle_rad=None,
        bad_post_velocity_xy=None,
        bad_outgoing_angle_to_barrier_deg=None,
        alternate_barrier_rotation_deg=None,
        alternate_barrier_axis_angle_rad=None,
        alternate_barrier_vertices_xy=None,
        alternate_barrier_feasible=False,
        invalid_final_center_xy=None,
        invalid_trajectory_inside_roi=False,
        invalid_second_collision=False,
    )
    return JudgmentPair(False, None, None, metadata)


def generate_judgment_pair(
    base: SimulationResult,
    judgment_seed: int,
    config: PhysicsConfig,
) -> JudgmentPair:
    """Generate one matched valid/invalid pair from a dynamics-eligible scene."""
    validate_uint64(judgment_seed, "judgment_seed")
    if not base.acceptance.judgment_base_geometry_eligible:
        return _failed_pair(base, judgment_seed, 0)
    rng = _judgment_rng(base, judgment_seed)
    chosen: _ValidBadCandidate | None = None
    attempts = 0
    for attempts in range(1, config.max_violation_sampling_attempts + 1):
        delta = float(
            rng.uniform(config.violation_delta_min_rad, config.violation_delta_max_rad)
        )
        candidates = [
            candidate
            for sign in (-1, 1)
            if (candidate := _evaluate_bad_candidate(base, delta, sign, config)) is not None
        ]
        if len(candidates) == 2:
            chosen = candidates[int(rng.integers(0, 2))]
        elif len(candidates) == 1:
            chosen = candidates[0]
        if chosen is not None:
            break

    if chosen is None:
        return _failed_pair(base, judgment_seed, attempts)

    pair_id = f"{base.scene.latent_scene_id}:pair:{judgment_seed:016x}"
    invalid_trajectory_id = f"{base.scene.latent_scene_id}:invalid:{judgment_seed:016x}"
    invalid_trajectory = trajectory_with_post_velocity(
        base,
        chosen.bad_velocity_xy,
        invalid_trajectory_id,
        config,
    )
    valid_id = base.trajectory.trajectory_variant_id
    valid_labels = JudgmentLabels(
        validity_binary=1,
        angular_violation_deg=0.0,
        angular_violation_rad=0.0,
        normalized_violation_severity=0.0,
        violation_family="reflection_direction",
        violation_sign=0,
        latent_scene_id=base.scene.latent_scene_id,
        judgment_pair_id=pair_id,
        trajectory_variant_id=valid_id,
        paired_trajectory_variant_id=invalid_trajectory_id,
    )
    invalid_labels = JudgmentLabels(
        validity_binary=0,
        angular_violation_deg=math.degrees(chosen.delta_rad),
        angular_violation_rad=chosen.delta_rad,
        normalized_violation_severity=math.degrees(chosen.delta_rad) / 90.0,
        violation_family="reflection_direction",
        violation_sign=chosen.sign,
        latent_scene_id=base.scene.latent_scene_id,
        judgment_pair_id=pair_id,
        trajectory_variant_id=invalid_trajectory_id,
        paired_trajectory_variant_id=valid_id,
    )
    metadata = JudgmentVariantMetadata(
        judgment_pair_id=pair_id,
        latent_scene_id=base.scene.latent_scene_id,
        judgment_pair_generated=True,
        valid_trajectory_variant_id=valid_id,
        invalid_trajectory_variant_id=invalid_trajectory_id,
        judgment_seed=judgment_seed,
        violation_sampling_attempt_count=attempts,
        delta_deg=math.degrees(chosen.delta_rad),
        delta_rad=chosen.delta_rad,
        sign=chosen.sign,
        bad_post_velocity_angle_rad=chosen.bad_angle_rad,
        bad_post_velocity_xy=chosen.bad_velocity_xy,
        bad_outgoing_angle_to_barrier_deg=chosen.bad_outgoing_angle_deg,
        alternate_barrier_rotation_deg=math.degrees(chosen.alternate_rotation_rad),
        alternate_barrier_axis_angle_rad=chosen.alternate_axis_angle_rad,
        alternate_barrier_vertices_xy=chosen.alternate_vertices_xy,
        alternate_barrier_feasible=True,
        invalid_final_center_xy=chosen.final_center_xy,
        invalid_trajectory_inside_roi=True,
        invalid_second_collision=False,
    )
    return JudgmentPair(
        generated=True,
        valid=JudgmentVariant(base.trajectory, valid_labels),
        invalid=JudgmentVariant(invalid_trajectory, invalid_labels),
        metadata=metadata,
    )
