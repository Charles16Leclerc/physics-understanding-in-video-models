"""Deterministic v1 scene proposal sampler."""

from __future__ import annotations

import math

import numpy as np

from .config import PROPOSAL_MODE_CODE, PhysicsConfig
from .geometry import vec2, wrap_angle_2pi, wrap_axis_angle_pi
from .models import SceneSpec


UINT64_LIMIT = 1 << 64


def validate_uint64(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value < UINT64_LIMIT:
        raise ValueError(f"{field_name} must be an unsigned 64-bit integer")


def proposal_rng(
    scene_seed: int,
    proposal_index: int,
    proposal_mode: str,
) -> np.random.Generator:
    validate_uint64(scene_seed, "scene_seed")
    validate_uint64(proposal_index, "proposal_index")
    if proposal_mode not in PROPOSAL_MODE_CODE:
        raise ValueError(f"unknown proposal mode: {proposal_mode}")
    mode_code = PROPOSAL_MODE_CODE[proposal_mode]
    seed_sequence = np.random.SeedSequence([scene_seed, proposal_index, mode_code])
    return np.random.Generator(np.random.PCG64(seed_sequence))


def latent_scene_id(scene_seed: int, proposal_index: int, proposal_mode: str) -> str:
    mode_code = PROPOSAL_MODE_CODE[proposal_mode]
    return f"ls-{scene_seed:016x}-{mode_code:02x}-{proposal_index:016x}"


def sample_scene(
    config: PhysicsConfig,
    scene_seed: int,
    proposal_index: int,
) -> SceneSpec:
    """Sample one independent-uniform latent proposal.

    The frozen draw order is speed, velocity angle, barrier angle, context x/y,
    then barrier-center x/y. Recording this order makes exact replay robust.
    """
    if config.proposal_mode != "independent_uniform":
        raise NotImplementedError("v1 implements only independent_uniform sampling")
    rng = proposal_rng(scene_seed, proposal_index, config.proposal_mode)

    speed_cells = float(
        rng.uniform(config.speed_min_cells_per_s, config.speed_max_cells_per_s)
    )
    velocity_angle = wrap_angle_2pi(float(rng.uniform(0.0, 2.0 * math.pi)))
    barrier_angle = wrap_axis_angle_pi(float(rng.uniform(0.0, math.pi)))
    p_context = vec2(
        float(rng.uniform(-config.center_half_width_px, config.center_half_width_px)),
        float(rng.uniform(-config.center_half_height_px, config.center_half_height_px)),
    )

    a = config.barrier_half_length_px
    h = config.barrier_half_width_px
    extent_x = a * abs(math.cos(barrier_angle)) + h * abs(math.sin(barrier_angle))
    extent_y = a * abs(math.sin(barrier_angle)) + h * abs(math.cos(barrier_angle))
    barrier_center = vec2(
        float(rng.uniform(-config.roi_half_width_px + extent_x, config.roi_half_width_px - extent_x)),
        float(rng.uniform(-config.roi_half_height_px + extent_y, config.roi_half_height_px - extent_y)),
    )

    speed_px = speed_cells * config.cell_px
    velocity = speed_px * vec2(math.cos(velocity_angle), math.sin(velocity_angle))
    return SceneSpec(
        latent_scene_id=latent_scene_id(scene_seed, proposal_index, config.proposal_mode),
        scene_seed=scene_seed,
        proposal_index=proposal_index,
        proposal_mode=config.proposal_mode,
        p_context_xy=p_context,
        speed_px_per_s=speed_px,
        speed_cells_per_s=speed_cells,
        velocity_angle_rad=velocity_angle,
        velocity_xy=velocity,
        barrier_center_xy=barrier_center,
        barrier_axis_angle_rad=barrier_angle,
        barrier_length_px=config.barrier_length_px,
        barrier_width_px=config.barrier_width_px,
        ball_radius_px=config.ball_radius_px,
    )
