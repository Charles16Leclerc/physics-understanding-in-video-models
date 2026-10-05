"""Versioned simulator configuration and derived benchmark constants."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math


PROPOSAL_MODE_CODE = {
    "independent_uniform": 0,
    "positive_guided": 1,
    "negative_guided": 2,
}


@dataclass(frozen=True, slots=True)
class PhysicsConfig:
    frame_width_px: int = 448
    frame_height_px: int = 448
    cell_px: float = 28.0

    table_width_px: float = 420.0
    table_height_px: float = 308.0
    physics_roi_width_px: float = 392.0
    physics_roi_height_px: float = 280.0

    ball_diameter_px: float = 35.0
    ball_radius_px: float = 17.5
    barrier_length_px: float = 140.0
    barrier_width_px: float = 28.0

    fps: int = 24
    num_frames: int = 24
    num_context_frames: int = 8
    collision_frame_min: int = 12
    collision_frame_max: int = 19

    endpoint_margin_px: float = 17.5
    negative_safety_margin_px: float = 35.0
    min_impact_angle_deg: float = 10.0
    min_bad_outgoing_angle_deg: float = 10.0

    speed_min_cells_per_s: float = 5.0
    speed_max_cells_per_s: float = 8.5

    proposal_mode: str = "independent_uniform"
    speed_distribution: str = "uniform_range"
    velocity_angle_distribution: str = "uniform_0_2pi"
    barrier_axis_angle_distribution: str = "uniform_0_pi"
    p_context_distribution: str = "uniform_ball_center_legal_region"
    barrier_center_distribution: str = "uniform_orientation_conditioned_feasible_region"
    rng_algorithm: str = "numpy_pcg64_seedsequence"

    violation_delta_min_deg: float = 5.0
    violation_delta_max_deg: float = 90.0
    max_violation_sampling_attempts: int = 128

    spatial_epsilon_px: float = 1.0e-9
    time_epsilon_s: float = 1.0e-12
    angle_epsilon_rad: float = 1.0e-12

    restitution: float = 1.0
    friction: float = 0.0

    def __post_init__(self) -> None:
        if self.frame_width_px != 448 or self.frame_height_px != 448:
            raise ValueError("v1 master frame must be 448x448")
        if not math.isclose(self.ball_diameter_px, 2.0 * self.ball_radius_px):
            raise ValueError("ball_diameter_px must equal 2 * ball_radius_px")
        if self.fps <= 0 or self.num_frames <= 0:
            raise ValueError("fps and num_frames must be positive")
        if not 0 < self.num_context_frames < self.num_frames:
            raise ValueError("num_context_frames must lie inside the clip")
        if not 0 <= self.collision_frame_min <= self.collision_frame_max < self.num_frames:
            raise ValueError("collision frame window is invalid")
        if not 0.0 < self.speed_min_cells_per_s < self.speed_max_cells_per_s:
            raise ValueError("speed range must be positive and non-empty")
        if self.proposal_mode not in PROPOSAL_MODE_CODE:
            raise ValueError(f"unknown proposal_mode: {self.proposal_mode}")
        if self.proposal_mode != "independent_uniform":
            raise NotImplementedError(
                "v1 implements only proposal_mode='independent_uniform'; guided mode codes are reserved"
            )
        expected_distributions = {
            "speed_distribution": "uniform_range",
            "velocity_angle_distribution": "uniform_0_2pi",
            "barrier_axis_angle_distribution": "uniform_0_pi",
            "p_context_distribution": "uniform_ball_center_legal_region",
            "barrier_center_distribution": "uniform_orientation_conditioned_feasible_region",
            "rng_algorithm": "numpy_pcg64_seedsequence",
        }
        for field_name, expected in expected_distributions.items():
            if getattr(self, field_name) != expected:
                raise ValueError(f"v1 requires {field_name}={expected!r}")
        if self.restitution != 1.0 or self.friction != 0.0:
            raise ValueError("v1 requires restitution=1 and friction=0")
        if min(self.spatial_epsilon_px, self.time_epsilon_s, self.angle_epsilon_rad) <= 0.0:
            raise ValueError("all numerical epsilons must be positive")
        if not 0.0 < self.violation_delta_min_deg < self.violation_delta_max_deg <= 90.0:
            raise ValueError("violation delta range must lie in (0, 90]")

    @property
    def frame_half_width_px(self) -> float:
        return self.frame_width_px / 2.0

    @property
    def frame_half_height_px(self) -> float:
        return self.frame_height_px / 2.0

    @property
    def table_half_width_px(self) -> float:
        return self.table_width_px / 2.0

    @property
    def table_half_height_px(self) -> float:
        return self.table_height_px / 2.0

    @property
    def roi_half_width_px(self) -> float:
        return self.physics_roi_width_px / 2.0

    @property
    def roi_half_height_px(self) -> float:
        return self.physics_roi_height_px / 2.0

    @property
    def center_half_width_px(self) -> float:
        return self.roi_half_width_px - self.ball_radius_px

    @property
    def center_half_height_px(self) -> float:
        return self.roi_half_height_px - self.ball_radius_px

    @property
    def barrier_half_length_px(self) -> float:
        return self.barrier_length_px / 2.0

    @property
    def barrier_half_width_px(self) -> float:
        return self.barrier_width_px / 2.0

    @property
    def context_time_s(self) -> float:
        return self.num_context_frames / self.fps

    @property
    def duration_s(self) -> float:
        return self.num_frames / self.fps

    @property
    def speed_min_px_per_s(self) -> float:
        return self.speed_min_cells_per_s * self.cell_px

    @property
    def speed_max_px_per_s(self) -> float:
        return self.speed_max_cells_per_s * self.cell_px

    @property
    def min_impact_angle_rad(self) -> float:
        return math.radians(self.min_impact_angle_deg)

    @property
    def min_bad_outgoing_angle_rad(self) -> float:
        return math.radians(self.min_bad_outgoing_angle_deg)

    @property
    def violation_delta_min_rad(self) -> float:
        return math.radians(self.violation_delta_min_deg)

    @property
    def violation_delta_max_rad(self) -> float:
        return math.radians(self.violation_delta_max_deg)

    @property
    def frame_times_s(self) -> tuple[float, ...]:
        return tuple(i / self.fps for i in range(self.num_frames))

    @property
    def mode_code(self) -> int:
        return PROPOSAL_MODE_CODE[self.proposal_mode]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def config_hash(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
