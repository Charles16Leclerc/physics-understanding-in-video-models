"""Typed records shared by sampling, simulation, labels, and rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray


FloatArray = NDArray[np.float64]
ContactStatus = Literal["positive", "negative", "reject"]
ContactFeature = Literal["none", "long_face", "short_face", "corner", "ambiguous"]


@dataclass(frozen=True, slots=True)
class SceneSpec:
    latent_scene_id: str
    scene_seed: int
    proposal_index: int
    proposal_mode: str
    p_context_xy: FloatArray
    speed_px_per_s: float
    speed_cells_per_s: float
    velocity_angle_rad: float
    velocity_xy: FloatArray
    barrier_center_xy: FloatArray
    barrier_axis_angle_rad: float
    barrier_length_px: float
    barrier_width_px: float
    ball_radius_px: float


@dataclass(frozen=True, slots=True)
class CollisionEvent:
    future_first_contact_exists: bool
    first_contact_time_s: float | None
    first_contact_frame_index: int | None
    first_contact_feature: ContactFeature
    contact_face_id: str | None
    contact_normal_xy: FloatArray | None
    ball_center_at_contact_xy: FloatArray | None
    surface_contact_point_xy: FloatArray | None
    contact_axis_coordinate_px: float | None
    impact_angle_deg: float | None
    pre_collision_velocity_xy: FloatArray | None
    post_collision_velocity_xy: FloatArray | None
    post_collision_angle_rad: float | None


@dataclass(frozen=True, slots=True)
class Trajectory:
    trajectory_variant_id: str
    frame_times_s: FloatArray
    ball_center_xy: FloatArray
    velocity_xy: FloatArray
    p_end_at_t1_xy: FloatArray
    barrier_vertices_xy: FloatArray
    barrier_tangent_xy: FloatArray


@dataclass(frozen=True, slots=True)
class RelativeGeometry:
    barrier_center_minus_ball_xy: FloatArray
    ball_u_in_barrier_frame: float
    ball_d_in_barrier_frame: float
    signed_center_clearance_to_nearest_long_face_contact_line_px: float
    endpoint_axial_margin_px: float
    center_ray_min_distance_to_rectangle_px: float
    ball_surface_ray_min_clearance_to_rectangle_px: float
    candidate_collision_time_s: float | None
    actual_first_contact_feature: ContactFeature


@dataclass(frozen=True, slots=True)
class ContactClassification:
    status: ContactStatus
    contact_binary: int | None
    negative_safe_ray_no_intersection: bool
    true_barrier_collision_exists: bool
    legal_long_face_collision_exists: bool
    collision_in_positive_window: bool
    collision_after_positive_window: bool
    collision_after_clip: bool


@dataclass(frozen=True, slots=True)
class AcceptanceReport:
    accepted_for_contact: bool
    accepted_for_dynamics: bool
    judgment_base_geometry_eligible: bool
    status: ContactStatus
    rejection_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StateLabels:
    p_context_xy: FloatArray
    velocity_xy: FloatArray
    speed_px_per_s: float
    speed_cells_per_s: float
    velocity_angle_rad: float
    barrier_axis_angle_rad: float
    barrier_center_xy: FloatArray
    relative_geometry: RelativeGeometry


@dataclass(frozen=True, slots=True)
class DynamicsLabels:
    ttc_from_context_s: float
    surface_contact_point_xy: FloatArray
    ball_center_at_contact_xy: FloatArray
    post_velocity_xy: FloatArray
    post_speed_px_per_s: float
    post_speed_cells_per_s: float
    post_velocity_angle_rad: float


@dataclass(frozen=True, slots=True)
class TaskLabels:
    state: StateLabels
    contact_binary: int | None
    dynamics: DynamicsLabels | None


@dataclass(frozen=True, slots=True)
class SimulationResult:
    scene: SceneSpec
    trajectory: Trajectory
    collision_event: CollisionEvent
    relative_geometry: RelativeGeometry
    contact: ContactClassification
    acceptance: AcceptanceReport
    labels: TaskLabels


@dataclass(frozen=True, slots=True)
class JudgmentLabels:
    validity_binary: int
    angular_violation_deg: float
    angular_violation_rad: float
    normalized_violation_severity: float
    violation_family: str
    violation_sign: int
    latent_scene_id: str
    judgment_pair_id: str
    trajectory_variant_id: str
    paired_trajectory_variant_id: str


@dataclass(frozen=True, slots=True)
class JudgmentVariant:
    trajectory: Trajectory
    labels: JudgmentLabels


@dataclass(frozen=True, slots=True)
class JudgmentVariantMetadata:
    judgment_pair_id: str
    latent_scene_id: str
    judgment_pair_generated: bool
    valid_trajectory_variant_id: str
    invalid_trajectory_variant_id: str | None
    judgment_seed: int
    violation_sampling_attempt_count: int
    delta_deg: float | None
    delta_rad: float | None
    sign: int | None
    bad_post_velocity_angle_rad: float | None
    bad_post_velocity_xy: FloatArray | None
    bad_outgoing_angle_to_barrier_deg: float | None
    alternate_barrier_rotation_deg: float | None
    alternate_barrier_axis_angle_rad: float | None
    alternate_barrier_vertices_xy: FloatArray | None
    alternate_barrier_feasible: bool
    invalid_final_center_xy: FloatArray | None
    invalid_trajectory_inside_roi: bool
    invalid_second_collision: bool


@dataclass(frozen=True, slots=True)
class JudgmentPair:
    generated: bool
    valid: JudgmentVariant | None
    invalid: JudgmentVariant | None
    metadata: JudgmentVariantMetadata
