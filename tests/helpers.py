from __future__ import annotations

import math

import numpy as np

from physics_bench.config import PhysicsConfig
from physics_bench.geometry import wrap_angle_2pi, wrap_axis_angle_pi
from physics_bench.models import SceneSpec
from physics_bench.sampler import latent_scene_id


def make_scene(
    *,
    p_context_xy: tuple[float, float],
    velocity_xy: tuple[float, float],
    barrier_center_xy: tuple[float, float] = (0.0, 0.0),
    barrier_axis_angle_rad: float = 0.0,
    scene_seed: int = 1,
    proposal_index: int = 0,
    config: PhysicsConfig | None = None,
) -> SceneSpec:
    config = config or PhysicsConfig()
    velocity = np.asarray(velocity_xy, dtype=np.float64)
    speed_px = float(np.linalg.norm(velocity))
    return SceneSpec(
        latent_scene_id=latent_scene_id(scene_seed, proposal_index, config.proposal_mode),
        scene_seed=scene_seed,
        proposal_index=proposal_index,
        proposal_mode=config.proposal_mode,
        p_context_xy=np.asarray(p_context_xy, dtype=np.float64),
        speed_px_per_s=speed_px,
        speed_cells_per_s=speed_px / config.cell_px,
        velocity_angle_rad=wrap_angle_2pi(math.atan2(velocity[1], velocity[0])),
        velocity_xy=velocity,
        barrier_center_xy=np.asarray(barrier_center_xy, dtype=np.float64),
        barrier_axis_angle_rad=wrap_axis_angle_pi(barrier_axis_angle_rad),
        barrier_length_px=config.barrier_length_px,
        barrier_width_px=config.barrier_width_px,
        ball_radius_px=config.ball_radius_px,
    )
