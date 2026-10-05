"""Exact continuous 2D geometry for a moving disk and finite rectangle."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from numpy.typing import NDArray

from .models import ContactFeature, FloatArray


def vec2(x: float, y: float) -> FloatArray:
    return np.asarray([x, y], dtype=np.float64)


def unit(vector: FloatArray) -> FloatArray:
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        raise ValueError("zero vector has no direction")
    return np.asarray(vector, dtype=np.float64) / norm


def wrap_angle_2pi(angle_rad: float) -> float:
    value = angle_rad % (2.0 * math.pi)
    return 0.0 if value == 2.0 * math.pi else value


def wrap_axis_angle_pi(angle_rad: float) -> float:
    value = angle_rad % math.pi
    return 0.0 if value == math.pi else value


def barrier_basis(axis_angle_rad: float) -> tuple[FloatArray, FloatArray]:
    tangent = vec2(math.cos(axis_angle_rad), math.sin(axis_angle_rad))
    normal = vec2(-math.sin(axis_angle_rad), math.cos(axis_angle_rad))
    return tangent, normal


def world_to_barrier_local(
    point_xy: FloatArray,
    barrier_center_xy: FloatArray,
    tangent_xy: FloatArray,
    normal_xy: FloatArray,
) -> FloatArray:
    delta = np.asarray(point_xy, dtype=np.float64) - barrier_center_xy
    return vec2(float(np.dot(delta, tangent_xy)), float(np.dot(delta, normal_xy)))


def barrier_local_to_world(
    local_ud: FloatArray,
    barrier_center_xy: FloatArray,
    tangent_xy: FloatArray,
    normal_xy: FloatArray,
) -> FloatArray:
    return (
        np.asarray(barrier_center_xy, dtype=np.float64)
        + float(local_ud[0]) * tangent_xy
        + float(local_ud[1]) * normal_xy
    )


def barrier_vertices(
    center_xy: FloatArray,
    axis_angle_rad: float,
    length_px: float,
    width_px: float,
) -> FloatArray:
    tangent, normal = barrier_basis(axis_angle_rad)
    a = length_px / 2.0
    h = width_px / 2.0
    return np.stack(
        [
            center_xy - a * tangent - h * normal,
            center_xy + a * tangent - h * normal,
            center_xy + a * tangent + h * normal,
            center_xy - a * tangent + h * normal,
        ]
    ).astype(np.float64)


def rotate_points(points_xy: FloatArray, center_xy: FloatArray, angle_rad: float) -> FloatArray:
    cosine = math.cos(angle_rad)
    sine = math.sin(angle_rad)
    rotation = np.asarray([[cosine, -sine], [sine, cosine]], dtype=np.float64)
    return (np.asarray(points_xy) - center_xy) @ rotation.T + center_xy


def strict_box_status(
    point_xy: FloatArray,
    half_width: float,
    half_height: float,
    epsilon: float,
) -> str:
    """Return inside, boundary, or outside for a strict axis-aligned box."""
    margin_x = half_width - abs(float(point_xy[0]))
    margin_y = half_height - abs(float(point_xy[1]))
    minimum = min(margin_x, margin_y)
    if minimum < -epsilon:
        return "outside"
    if minimum <= epsilon:
        return "boundary"
    return "inside"


def vertices_strictly_inside_box(
    vertices_xy: FloatArray,
    half_width: float,
    half_height: float,
    epsilon: float,
) -> tuple[bool, bool]:
    statuses = [strict_box_status(vertex, half_width, half_height, epsilon) for vertex in vertices_xy]
    return all(status == "inside" for status in statuses), any(
        status == "boundary" for status in statuses
    )


def point_to_rectangle_distance_local(local_ud: FloatArray, a: float, h: float) -> float:
    du = max(abs(float(local_ud[0])) - a, 0.0)
    dd = max(abs(float(local_ud[1])) - h, 0.0)
    return math.hypot(du, dd)


def ray_min_distance_to_rectangle_local(
    origin_ud: FloatArray,
    direction_ud: FloatArray,
    a: float,
    h: float,
    angle_epsilon: float,
) -> float:
    """Exact Euclidean distance from an infinite forward ray to a closed AABB."""
    direction = unit(direction_ud)
    candidates = [0.0]
    for coordinate, extent, component in (
        (float(origin_ud[0]), a, float(direction[0])),
        (float(origin_ud[1]), h, float(direction[1])),
    ):
        if abs(component) > math.sin(angle_epsilon):
            for boundary in (-extent, extent):
                distance = (boundary - coordinate) / component
                if distance >= 0.0:
                    candidates.append(distance)
    for corner_u in (-a, a):
        for corner_d in (-h, h):
            projection = float(np.dot(vec2(corner_u, corner_d) - origin_ud, direction))
            if projection >= 0.0:
                candidates.append(projection)
    return min(
        point_to_rectangle_distance_local(origin_ud + distance * direction, a, h)
        for distance in candidates
    )


def ray_min_distance_to_rectangle(
    origin_xy: FloatArray,
    direction_xy: FloatArray,
    barrier_center_xy: FloatArray,
    barrier_axis_angle_rad: float,
    barrier_length_px: float,
    barrier_width_px: float,
    angle_epsilon: float,
) -> float:
    tangent, normal = barrier_basis(barrier_axis_angle_rad)
    origin_ud = world_to_barrier_local(origin_xy, barrier_center_xy, tangent, normal)
    direction_ud = vec2(float(np.dot(unit(direction_xy), tangent)), float(np.dot(unit(direction_xy), normal)))
    return ray_min_distance_to_rectangle_local(
        origin_ud,
        direction_ud,
        barrier_length_px / 2.0,
        barrier_width_px / 2.0,
        angle_epsilon,
    )


@dataclass(frozen=True, slots=True)
class GeometricContact:
    feature: ContactFeature
    distance_px: float | None
    face_id: str | None
    center_xy: FloatArray | None
    surface_xy: FloatArray | None
    normal_xy: FloatArray | None
    contact_axis_coordinate_px: float | None
    impact_angle_deg: float | None
    numerical_ambiguous: bool = False
    initial_overlap: bool = False

    @classmethod
    def none(cls) -> "GeometricContact":
        return cls("none", None, None, None, None, None, None, None)


@dataclass(frozen=True, slots=True)
class _Candidate:
    distance_px: float
    feature: ContactFeature
    face_id: str | None
    local_center_ud: FloatArray
    local_surface_ud: FloatArray | None
    local_normal_ud: FloatArray | None
    ambiguous: bool = False


def first_contact_moving_point_rounded_rectangle(
    origin_xy: FloatArray,
    direction_xy: FloatArray,
    barrier_center_xy: FloatArray,
    barrier_axis_angle_rad: float,
    barrier_length_px: float,
    barrier_width_px: float,
    expansion_radius_px: float,
    spatial_epsilon_px: float,
    angle_epsilon_rad: float,
) -> GeometricContact:
    """First forward-ray contact with rectangle Minkowski-expanded by a disk.

    The returned distance is path length in pixels, not time. Setting
    ``expansion_radius_px`` to the ball radius gives disk-vs-rectangle contact;
    setting it to d2 gives the rounded negative safety region.
    """
    direction_world = unit(direction_xy)
    tangent, canonical_normal = barrier_basis(barrier_axis_angle_rad)
    origin_ud = world_to_barrier_local(origin_xy, barrier_center_xy, tangent, canonical_normal)
    direction_ud = vec2(
        float(np.dot(direction_world, tangent)),
        float(np.dot(direction_world, canonical_normal)),
    )
    a = barrier_length_px / 2.0
    h = barrier_width_px / 2.0
    radius = expansion_radius_px
    epsilon = spatial_epsilon_px
    direction_threshold = math.sin(angle_epsilon_rad)

    start_distance = point_to_rectangle_distance_local(origin_ud, a, h)
    if start_distance < radius - epsilon:
        return GeometricContact(
            feature="ambiguous",
            distance_px=0.0,
            face_id=None,
            center_xy=np.asarray(origin_xy, dtype=np.float64),
            surface_xy=None,
            normal_xy=None,
            contact_axis_coordinate_px=None,
            impact_angle_deg=None,
            numerical_ambiguous=False,
            initial_overlap=True,
        )
    if abs(start_distance - radius) <= epsilon:
        return GeometricContact(
            feature="ambiguous",
            distance_px=0.0,
            face_id=None,
            center_xy=np.asarray(origin_xy, dtype=np.float64),
            surface_xy=None,
            normal_xy=None,
            contact_axis_coordinate_px=None,
            impact_angle_deg=None,
            numerical_ambiguous=True,
            initial_overlap=False,
        )

    candidates: list[_Candidate] = []

    # Long faces d = +/- (h + radius), with physical-face coordinate |u| < a.
    for sign_d in (-1.0, 1.0):
        component = float(direction_ud[1])
        if sign_d * component >= -direction_threshold:
            continue
        target_d = sign_d * (h + radius)
        distance = (target_d - float(origin_ud[1])) / component
        if distance <= epsilon:
            continue
        center = origin_ud + distance * direction_ud
        axial = abs(float(center[0]))
        if axial < a - epsilon:
            candidates.append(
                _Candidate(
                    distance,
                    "long_face",
                    "long_pos_n" if sign_d > 0 else "long_neg_n",
                    center,
                    vec2(float(center[0]), sign_d * h),
                    vec2(0.0, sign_d),
                )
            )
        elif abs(axial - a) <= epsilon:
            candidates.append(_Candidate(distance, "ambiguous", None, center, None, None, True))

    # Short faces u = +/- (a + radius), with physical-face coordinate |d| < h.
    for sign_u in (-1.0, 1.0):
        component = float(direction_ud[0])
        if sign_u * component >= -direction_threshold:
            continue
        target_u = sign_u * (a + radius)
        distance = (target_u - float(origin_ud[0])) / component
        if distance <= epsilon:
            continue
        center = origin_ud + distance * direction_ud
        transverse = abs(float(center[1]))
        if transverse < h - epsilon:
            candidates.append(
                _Candidate(
                    distance,
                    "short_face",
                    "short_pos_t" if sign_u > 0 else "short_neg_t",
                    center,
                    vec2(sign_u * a, float(center[1])),
                    vec2(sign_u, 0.0),
                )
            )
        elif abs(transverse - h) <= epsilon:
            candidates.append(_Candidate(distance, "ambiguous", None, center, None, None, True))

    # Quarter-circle corner arcs.
    for sign_u in (-1.0, 1.0):
        for sign_d in (-1.0, 1.0):
            corner = vec2(sign_u * a, sign_d * h)
            corner_from_origin = corner - origin_ud
            projection = float(np.dot(corner_from_origin, direction_ud))
            if projection <= epsilon:
                continue
            perpendicular_sq = max(
                0.0,
                float(np.dot(corner_from_origin, corner_from_origin)) - projection * projection,
            )
            perpendicular = math.sqrt(perpendicular_sq)
            if perpendicular > radius + epsilon:
                continue
            tangent_hit = abs(perpendicular - radius) <= epsilon
            if tangent_hit:
                distance = projection
            else:
                distance = projection - math.sqrt(max(radius * radius - perpendicular_sq, 0.0))
            if distance <= epsilon:
                continue
            center = origin_ud + distance * direction_ud
            radial = center - corner
            quadrant_u = sign_u * float(radial[0])
            quadrant_d = sign_d * float(radial[1])
            if quadrant_u < -epsilon or quadrant_d < -epsilon:
                continue
            boundary_join = quadrant_u <= epsilon or quadrant_d <= epsilon
            ambiguous = tangent_hit or boundary_join
            face_id = f"corner_{'pos' if sign_u > 0 else 'neg'}_t_{'pos' if sign_d > 0 else 'neg'}_n"
            candidates.append(
                _Candidate(
                    distance,
                    "ambiguous" if ambiguous else "corner",
                    None if ambiguous else face_id,
                    center,
                    None if ambiguous else corner,
                    None,
                    ambiguous,
                )
            )

    if not candidates:
        return GeometricContact.none()

    candidates.sort(key=lambda candidate: candidate.distance_px)
    first = candidates[0]
    simultaneous = any(
        abs(candidate.distance_px - first.distance_px) <= epsilon for candidate in candidates[1:]
    )
    if first.ambiguous or simultaneous:
        center_world = barrier_local_to_world(
            first.local_center_ud, barrier_center_xy, tangent, canonical_normal
        )
        return GeometricContact(
            feature="ambiguous",
            distance_px=first.distance_px,
            face_id=None,
            center_xy=center_world,
            surface_xy=None,
            normal_xy=None,
            contact_axis_coordinate_px=None,
            impact_angle_deg=None,
            numerical_ambiguous=True,
        )

    center_world = barrier_local_to_world(
        first.local_center_ud, barrier_center_xy, tangent, canonical_normal
    )
    surface_world = (
        None
        if first.local_surface_ud is None
        else barrier_local_to_world(
            first.local_surface_ud, barrier_center_xy, tangent, canonical_normal
        )
    )
    normal_world = (
        None
        if first.local_normal_ud is None
        else unit(
            float(first.local_normal_ud[0]) * tangent
            + float(first.local_normal_ud[1]) * canonical_normal
        )
    )
    impact_angle_deg = None
    if normal_world is not None:
        impact_angle_deg = math.degrees(
            math.asin(min(1.0, abs(float(np.dot(direction_world, canonical_normal)))))
        )
    contact_axis = None if surface_world is None else float(first.local_surface_ud[0])
    return GeometricContact(
        feature=first.feature,
        distance_px=first.distance_px,
        face_id=first.face_id,
        center_xy=center_world,
        surface_xy=surface_world,
        normal_xy=normal_world,
        contact_axis_coordinate_px=contact_axis,
        impact_angle_deg=impact_angle_deg,
    )


def reflect_velocity(velocity_xy: FloatArray, outward_normal_xy: FloatArray) -> FloatArray:
    normal = unit(outward_normal_xy)
    return np.asarray(velocity_xy, dtype=np.float64) - 2.0 * float(
        np.dot(velocity_xy, normal)
    ) * normal
