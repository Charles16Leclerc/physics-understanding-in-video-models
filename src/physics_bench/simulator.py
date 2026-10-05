"""Continuous trajectory simulation, acceptance, and task-label generation."""

from __future__ import annotations

import math

import numpy as np

from .config import PhysicsConfig
from .geometry import (
    GeometricContact,
    barrier_basis,
    barrier_vertices,
    first_contact_moving_point_rounded_rectangle,
    ray_min_distance_to_rectangle,
    reflect_velocity,
    strict_box_status,
    vertices_strictly_inside_box,
    wrap_angle_2pi,
    world_to_barrier_local,
)
from .models import (
    AcceptanceReport,
    CollisionEvent,
    ContactClassification,
    DynamicsLabels,
    RelativeGeometry,
    SceneSpec,
    SimulationResult,
    StateLabels,
    TaskLabels,
    Trajectory,
)


def _append_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def _validate_scene(scene: SceneSpec, config: PhysicsConfig) -> None:
    speed = float(np.linalg.norm(scene.velocity_xy))
    tolerance = max(config.spatial_epsilon_px, speed * config.angle_epsilon_rad)
    if abs(speed - scene.speed_px_per_s) > tolerance:
        raise ValueError("SceneSpec velocity_xy and speed_px_per_s are inconsistent")
    if abs(scene.speed_cells_per_s * config.cell_px - speed) > tolerance:
        raise ValueError("SceneSpec speed_cells_per_s is inconsistent")
    expected_angle = wrap_angle_2pi(math.atan2(scene.velocity_xy[1], scene.velocity_xy[0]))
    angle_error = abs(
        math.atan2(
            math.sin(expected_angle - scene.velocity_angle_rad),
            math.cos(expected_angle - scene.velocity_angle_rad),
        )
    )
    if angle_error > config.angle_epsilon_rad:
        raise ValueError("SceneSpec velocity angle is inconsistent")
    if not 0.0 <= scene.velocity_angle_rad < 2.0 * math.pi:
        raise ValueError("velocity_angle_rad is not canonical")
    if not 0.0 <= scene.barrier_axis_angle_rad < math.pi:
        raise ValueError("barrier_axis_angle_rad is not canonical")
    if scene.ball_radius_px != config.ball_radius_px:
        raise ValueError("SceneSpec ball radius differs from PhysicsConfig")
    if scene.barrier_length_px != config.barrier_length_px:
        raise ValueError("SceneSpec barrier length differs from PhysicsConfig")
    if scene.barrier_width_px != config.barrier_width_px:
        raise ValueError("SceneSpec barrier width differs from PhysicsConfig")


def _raw_contact(scene: SceneSpec, config: PhysicsConfig, expansion_radius_px: float) -> GeometricContact:
    return first_contact_moving_point_rounded_rectangle(
        scene.p_context_xy,
        scene.velocity_xy,
        scene.barrier_center_xy,
        scene.barrier_axis_angle_rad,
        scene.barrier_length_px,
        scene.barrier_width_px,
        expansion_radius_px,
        config.spatial_epsilon_px,
        config.angle_epsilon_rad,
    )


def _snap_event_time(time_s: float, config: PhysicsConfig) -> float:
    nearest_frame_time = round(time_s * config.fps) / config.fps
    if abs(time_s - nearest_frame_time) <= config.time_epsilon_s:
        return nearest_frame_time
    return time_s


def _frame_index(time_s: float, config: PhysicsConfig) -> int:
    snapped = _snap_event_time(time_s, config)
    return math.floor(config.fps * snapped)


def _empty_event() -> CollisionEvent:
    return CollisionEvent(
        future_first_contact_exists=False,
        first_contact_time_s=None,
        first_contact_frame_index=None,
        first_contact_feature="none",
        contact_face_id=None,
        contact_normal_xy=None,
        ball_center_at_contact_xy=None,
        surface_contact_point_xy=None,
        contact_axis_coordinate_px=None,
        impact_angle_deg=None,
        pre_collision_velocity_xy=None,
        post_collision_velocity_xy=None,
        post_collision_angle_rad=None,
    )


def _collision_event(
    scene: SceneSpec,
    raw_contact: GeometricContact,
    absolute_time_s: float | None,
    config: PhysicsConfig,
) -> CollisionEvent:
    if (
        raw_contact.feature == "none"
        or absolute_time_s is None
        or absolute_time_s >= config.duration_s
    ):
        return _empty_event()
    event_time = _snap_event_time(absolute_time_s, config)
    frame_index = _frame_index(event_time, config)
    pre_velocity = np.asarray(scene.velocity_xy, dtype=np.float64)

    if raw_contact.feature == "ambiguous":
        return CollisionEvent(
            True,
            event_time,
            frame_index,
            "ambiguous",
            None,
            None,
            raw_contact.center_xy,
            None,
            None,
            None,
            pre_velocity,
            None,
            None,
        )
    if raw_contact.feature == "corner":
        return CollisionEvent(
            True,
            event_time,
            frame_index,
            "corner",
            raw_contact.face_id,
            None,
            raw_contact.center_xy,
            raw_contact.surface_xy,
            raw_contact.contact_axis_coordinate_px,
            None,
            pre_velocity,
            None,
            None,
        )

    if raw_contact.normal_xy is None:
        raise RuntimeError("face contact is missing a normal")
    post_velocity = reflect_velocity(pre_velocity, raw_contact.normal_xy)
    return CollisionEvent(
        True,
        event_time,
        frame_index,
        raw_contact.feature,
        raw_contact.face_id,
        raw_contact.normal_xy,
        raw_contact.center_xy,
        raw_contact.surface_xy,
        raw_contact.contact_axis_coordinate_px,
        raw_contact.impact_angle_deg,
        pre_velocity,
        post_velocity,
        wrap_angle_2pi(math.atan2(post_velocity[1], post_velocity[0])),
    )


def _trajectory_from_event(
    scene: SceneSpec,
    event: CollisionEvent,
    vertices_xy: np.ndarray,
    tangent_xy: np.ndarray,
    config: PhysicsConfig,
    *,
    trajectory_variant_id: str | None = None,
    override_post_velocity_xy: np.ndarray | None = None,
) -> Trajectory:
    frame_times = np.asarray(config.frame_times_s, dtype=np.float64)
    positions = np.empty((config.num_frames, 2), dtype=np.float64)
    velocities = np.empty((config.num_frames, 2), dtype=np.float64)
    event_time = event.first_contact_time_s
    event_center = event.ball_center_at_contact_xy
    post_velocity = (
        np.asarray(override_post_velocity_xy, dtype=np.float64)
        if override_post_velocity_xy is not None
        else event.post_collision_velocity_xy
    )
    has_piecewise_path = event_time is not None and event_center is not None and post_velocity is not None

    for index, time_s in enumerate(frame_times):
        if has_piecewise_path and time_s >= event_time:
            positions[index] = event_center + post_velocity * (time_s - event_time)
            velocities[index] = post_velocity
        else:
            positions[index] = scene.p_context_xy + scene.velocity_xy * (
                time_s - config.context_time_s
            )
            velocities[index] = scene.velocity_xy

    if has_piecewise_path:
        p_end = event_center + post_velocity * (config.duration_s - event_time)
    else:
        p_end = scene.p_context_xy + scene.velocity_xy * (
            config.duration_s - config.context_time_s
        )
    return Trajectory(
        trajectory_variant_id=trajectory_variant_id or f"{scene.latent_scene_id}:physical",
        frame_times_s=frame_times,
        ball_center_xy=positions,
        velocity_xy=velocities,
        p_end_at_t1_xy=np.asarray(p_end, dtype=np.float64),
        barrier_vertices_xy=np.asarray(vertices_xy, dtype=np.float64),
        barrier_tangent_xy=np.asarray(tangent_xy, dtype=np.float64),
    )


def trajectory_with_post_velocity(
    base: SimulationResult,
    post_velocity_xy: np.ndarray,
    trajectory_variant_id: str,
    config: PhysicsConfig,
) -> Trajectory:
    """Create a full latent trajectory that branches only at collision time."""
    return _trajectory_from_event(
        base.scene,
        base.collision_event,
        base.trajectory.barrier_vertices_xy,
        base.trajectory.barrier_tangent_xy,
        config,
        trajectory_variant_id=trajectory_variant_id,
        override_post_velocity_xy=post_velocity_xy,
    )


def has_second_collision(
    contact_center_xy: np.ndarray,
    outgoing_velocity_xy: np.ndarray,
    collision_time_s: float,
    scene: SceneSpec,
    config: PhysicsConfig,
    initial_contact_normal_xy: np.ndarray | None = None,
) -> bool:
    if initial_contact_normal_xy is not None:
        outward_component = float(
            np.dot(
                outgoing_velocity_xy / np.linalg.norm(outgoing_velocity_xy),
                initial_contact_normal_xy,
            )
        )
        # A rectangle is convex. A ray starting on a supporting face and moving
        # into its exterior half-plane can never intersect the rectangle again.
        if outward_component > math.sin(config.angle_epsilon_rad):
            return False
    remaining_time = config.duration_s - collision_time_s
    if remaining_time <= config.time_epsilon_s:
        return False
    speed = float(np.linalg.norm(outgoing_velocity_xy))
    separation_distance = max(
        100.0 * config.spatial_epsilon_px,
        100.0 * config.time_epsilon_s * speed,
    )
    separation_time = separation_distance / speed
    if separation_time >= remaining_time:
        return False
    start = contact_center_xy + outgoing_velocity_xy * separation_time
    second = first_contact_moving_point_rounded_rectangle(
        start,
        outgoing_velocity_xy,
        scene.barrier_center_xy,
        scene.barrier_axis_angle_rad,
        scene.barrier_length_px,
        scene.barrier_width_px,
        scene.ball_radius_px,
        config.spatial_epsilon_px,
        config.angle_epsilon_rad,
    )
    if second.feature == "none" or second.distance_px is None:
        return False
    available_distance = speed * (remaining_time - separation_time)
    return second.distance_px <= available_distance + config.spatial_epsilon_px


def simulate_scene(scene: SceneSpec, config: PhysicsConfig) -> SimulationResult:
    _validate_scene(scene, config)
    reasons: list[str] = []
    tangent, _ = barrier_basis(scene.barrier_axis_angle_rad)
    vertices = barrier_vertices(
        scene.barrier_center_xy,
        scene.barrier_axis_angle_rad,
        scene.barrier_length_px,
        scene.barrier_width_px,
    )

    barrier_inside, barrier_boundary = vertices_strictly_inside_box(
        vertices,
        config.roi_half_width_px,
        config.roi_half_height_px,
        config.spatial_epsilon_px,
    )
    if not barrier_inside:
        _append_reason(reasons, "barrier_outside_physics_roi")
    if barrier_boundary:
        _append_reason(reasons, "numerical_boundary_ambiguous")

    p_start = scene.p_context_xy - scene.velocity_xy * config.context_time_s
    for point, outside_reason in (
        (p_start, "ball_start_outside_physics_roi"),
        (scene.p_context_xy, "ball_start_outside_physics_roi"),
    ):
        status = strict_box_status(
            point,
            config.center_half_width_px,
            config.center_half_height_px,
            config.spatial_epsilon_px,
        )
        if status == "outside":
            _append_reason(reasons, outside_reason)
        elif status == "boundary":
            _append_reason(reasons, "numerical_boundary_ambiguous")

    context_contact = first_contact_moving_point_rounded_rectangle(
        p_start,
        scene.velocity_xy,
        scene.barrier_center_xy,
        scene.barrier_axis_angle_rad,
        scene.barrier_length_px,
        scene.barrier_width_px,
        scene.ball_radius_px,
        config.spatial_epsilon_px,
        config.angle_epsilon_rad,
    )
    context_path_length = scene.speed_px_per_s * config.context_time_s
    if (
        context_contact.feature != "none"
        and context_contact.distance_px is not None
        and context_contact.distance_px <= context_path_length + config.spatial_epsilon_px
    ):
        _append_reason(reasons, "context_collision")
        if (
            context_contact.numerical_ambiguous
            or abs(context_contact.distance_px - context_path_length)
            <= config.spatial_epsilon_px
        ):
            _append_reason(reasons, "numerical_boundary_ambiguous")

    raw_contact = _raw_contact(scene, config, scene.ball_radius_px)
    candidate_time = (
        None
        if raw_contact.distance_px is None
        else config.context_time_s + raw_contact.distance_px / scene.speed_px_per_s
    )
    if candidate_time is not None:
        candidate_time = _snap_event_time(candidate_time, config)

    event = _collision_event(scene, raw_contact, candidate_time, config)
    trajectory = _trajectory_from_event(scene, event, vertices, tangent, config)

    safe_contact = _raw_contact(scene, config, config.negative_safety_margin_px)
    negative_safe = safe_contact.feature == "none"
    if safe_contact.numerical_ambiguous:
        _append_reason(reasons, "numerical_boundary_ambiguous")

    true_collision_exists = raw_contact.feature != "none"
    legal_long_face = raw_contact.feature == "long_face"
    collision_frame = None if candidate_time is None else _frame_index(candidate_time, config)
    in_positive_window = bool(
        legal_long_face
        and candidate_time is not None
        and candidate_time < config.duration_s
        and config.collision_frame_min <= collision_frame <= config.collision_frame_max
    )
    after_positive_window = bool(
        legal_long_face
        and collision_frame is not None
        and collision_frame > config.collision_frame_max
    )
    after_clip = bool(
        legal_long_face
        and candidate_time is not None
        and candidate_time >= config.duration_s
    )

    if raw_contact.numerical_ambiguous:
        _append_reason(reasons, "ambiguous_contact_feature")
        _append_reason(reasons, "numerical_boundary_ambiguous")
    elif raw_contact.feature == "short_face":
        _append_reason(reasons, "short_face_contact")
    elif raw_contact.feature == "corner":
        _append_reason(reasons, "corner_contact")

    if raw_contact.feature == "none":
        end_status = strict_box_status(
            trajectory.p_end_at_t1_xy,
            config.center_half_width_px,
            config.center_half_height_px,
            config.spatial_epsilon_px,
        )
        if end_status == "outside":
            _append_reason(reasons, "ball_end_outside_physics_roi")
        elif end_status == "boundary":
            _append_reason(reasons, "numerical_boundary_ambiguous")
        if not negative_safe:
            _append_reason(reasons, "negative_ray_enters_safety_region")
            _append_reason(reasons, "negative_not_strictly_safe")
    else:
        if candidate_time is not None and candidate_time >= config.duration_s:
            _append_reason(reasons, "collision_too_late")
            _append_reason(reasons, "ray_hit_beyond_video")
        elif collision_frame is not None:
            if collision_frame < config.collision_frame_min:
                _append_reason(reasons, "collision_too_early")
            elif collision_frame > config.collision_frame_max:
                _append_reason(reasons, "collision_too_late")

        if legal_long_face:
            axis = raw_contact.contact_axis_coordinate_px
            if axis is None:
                raise RuntimeError("long-face contact is missing axis coordinate")
            endpoint_threshold = config.barrier_half_length_px - config.endpoint_margin_px
            endpoint_difference = endpoint_threshold - abs(axis)
            if endpoint_difference <= 0.0:
                _append_reason(reasons, "endpoint_margin_violation")
            if abs(endpoint_difference) <= config.spatial_epsilon_px:
                _append_reason(reasons, "numerical_boundary_ambiguous")

            impact_deg = raw_contact.impact_angle_deg
            if impact_deg is None:
                raise RuntimeError("long-face contact is missing impact angle")
            impact_rad = math.radians(impact_deg)
            if impact_rad <= config.min_impact_angle_rad:
                _append_reason(reasons, "impact_angle_too_small")
            if abs(impact_rad - config.min_impact_angle_rad) <= config.angle_epsilon_rad:
                _append_reason(reasons, "numerical_boundary_ambiguous")

        if raw_contact.center_xy is not None:
            collision_center_status = strict_box_status(
                raw_contact.center_xy,
                config.center_half_width_px,
                config.center_half_height_px,
                config.spatial_epsilon_px,
            )
            if collision_center_status == "outside":
                _append_reason(reasons, "ball_collision_center_outside_physics_roi")
            elif collision_center_status == "boundary":
                _append_reason(reasons, "numerical_boundary_ambiguous")

        end_status = strict_box_status(
            trajectory.p_end_at_t1_xy,
            config.center_half_width_px,
            config.center_half_height_px,
            config.spatial_epsilon_px,
        )
        if end_status == "outside":
            _append_reason(reasons, "ball_end_outside_physics_roi")
        elif end_status == "boundary":
            _append_reason(reasons, "numerical_boundary_ambiguous")

        if (
            event.post_collision_velocity_xy is not None
            and event.ball_center_at_contact_xy is not None
            and event.first_contact_time_s is not None
            and has_second_collision(
                event.ball_center_at_contact_xy,
                event.post_collision_velocity_xy,
                event.first_contact_time_s,
                scene,
                config,
                event.contact_normal_xy,
            )
        ):
            _append_reason(reasons, "second_collision")
            _append_reason(reasons, "multiple_contact")

    if raw_contact.feature == "none" and negative_safe and not reasons:
        status = "negative"
        contact_binary = 0
    elif legal_long_face and in_positive_window and not reasons:
        status = "positive"
        contact_binary = 1
    else:
        status = "reject"
        contact_binary = None

    contact = ContactClassification(
        status=status,
        contact_binary=contact_binary,
        negative_safe_ray_no_intersection=negative_safe,
        true_barrier_collision_exists=true_collision_exists,
        legal_long_face_collision_exists=legal_long_face,
        collision_in_positive_window=in_positive_window,
        collision_after_positive_window=after_positive_window,
        collision_after_clip=after_clip,
    )
    acceptance = AcceptanceReport(
        accepted_for_contact=status in {"positive", "negative"},
        accepted_for_dynamics=status == "positive",
        judgment_base_geometry_eligible=status == "positive",
        status=status,
        rejection_reasons=tuple(reasons),
    )

    canonical_normal = barrier_basis(scene.barrier_axis_angle_rad)[1]
    local_context = world_to_barrier_local(
        scene.p_context_xy,
        scene.barrier_center_xy,
        tangent,
        canonical_normal,
    )
    ray_distance = ray_min_distance_to_rectangle(
        scene.p_context_xy,
        scene.velocity_xy,
        scene.barrier_center_xy,
        scene.barrier_axis_angle_rad,
        scene.barrier_length_px,
        scene.barrier_width_px,
        config.angle_epsilon_rad,
    )
    relative = RelativeGeometry(
        barrier_center_minus_ball_xy=scene.barrier_center_xy - scene.p_context_xy,
        ball_u_in_barrier_frame=float(local_context[0]),
        ball_d_in_barrier_frame=float(local_context[1]),
        signed_center_clearance_to_nearest_long_face_contact_line_px=(
            abs(float(local_context[1]))
            - (config.barrier_half_width_px + config.ball_radius_px)
        ),
        endpoint_axial_margin_px=config.barrier_half_length_px - abs(float(local_context[0])),
        center_ray_min_distance_to_rectangle_px=ray_distance,
        ball_surface_ray_min_clearance_to_rectangle_px=ray_distance - config.ball_radius_px,
        candidate_collision_time_s=candidate_time,
        actual_first_contact_feature=raw_contact.feature,
    )

    dynamics = None
    if status == "positive":
        if any(
            value is None
            for value in (
                event.first_contact_time_s,
                event.surface_contact_point_xy,
                event.ball_center_at_contact_xy,
                event.post_collision_velocity_xy,
                event.post_collision_angle_rad,
            )
        ):
            raise RuntimeError("accepted positive scene has incomplete dynamics event")
        post_speed = float(np.linalg.norm(event.post_collision_velocity_xy))
        dynamics = DynamicsLabels(
            ttc_from_context_s=event.first_contact_time_s - config.context_time_s,
            surface_contact_point_xy=event.surface_contact_point_xy,
            ball_center_at_contact_xy=event.ball_center_at_contact_xy,
            post_velocity_xy=event.post_collision_velocity_xy,
            post_speed_px_per_s=post_speed,
            post_speed_cells_per_s=post_speed / config.cell_px,
            post_velocity_angle_rad=event.post_collision_angle_rad,
        )

    labels = TaskLabels(
        state=StateLabels(
            p_context_xy=scene.p_context_xy,
            velocity_xy=scene.velocity_xy,
            speed_px_per_s=scene.speed_px_per_s,
            speed_cells_per_s=scene.speed_cells_per_s,
            velocity_angle_rad=scene.velocity_angle_rad,
            barrier_axis_angle_rad=scene.barrier_axis_angle_rad,
            barrier_center_xy=scene.barrier_center_xy,
            relative_geometry=relative,
        ),
        contact_binary=contact_binary,
        dynamics=dynamics,
    )
    return SimulationResult(scene, trajectory, event, relative, contact, acceptance, labels)
