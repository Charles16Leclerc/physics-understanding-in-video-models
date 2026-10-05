"""Minimal, explicitly non-production MP4 renderer for simulator inspection."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from .config import PhysicsConfig
from .models import JudgmentLabels, SimulationResult, Trajectory


def _load_render_dependencies():
    try:
        from PIL import Image, ImageDraw, ImageFont
        import imageio_ffmpeg
    except ImportError as exc:  # pragma: no cover - exercised by CLI error path
        raise RuntimeError(
            "Debug rendering requires the 'render' extra: install with `uv sync --extra render`."
        ) from exc
    return Image, ImageDraw, ImageFont, imageio_ffmpeg


def _font(ImageFont, size: int):
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def _world_to_image(point_xy: np.ndarray, config: PhysicsConfig, scale: int) -> tuple[int, int]:
    return (
        int(round((float(point_xy[0]) + config.frame_half_width_px) * scale)),
        int(round((config.frame_half_height_px - float(point_xy[1])) * scale)),
    )


def _draw_dashed_rectangle(draw, box, *, fill, width: int, dash: int) -> None:
    left, top, right, bottom = box
    for start in range(left, right, 2 * dash):
        draw.line((start, top, min(start + dash, right), top), fill=fill, width=width)
        draw.line((start, bottom, min(start + dash, right), bottom), fill=fill, width=width)
    for start in range(top, bottom, 2 * dash):
        draw.line((left, start, left, min(start + dash, bottom)), fill=fill, width=width)
        draw.line((right, start, right, min(start + dash, bottom)), fill=fill, width=width)


def _draw_frame(
    result: SimulationResult,
    trajectory: Trajectory,
    frame_index: int,
    config: PhysicsConfig,
    scale: int,
    judgment_labels: JudgmentLabels | None,
):
    Image, ImageDraw, ImageFont, _ = _load_render_dependencies()
    width = config.frame_width_px * scale
    height = config.frame_height_px * scale
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    grid_color = (222, 226, 230)
    for coordinate in range(0, config.frame_width_px + 1, int(config.cell_px)):
        pixel = coordinate * scale
        draw.line((pixel, 0, pixel, height), fill=grid_color, width=max(1, scale))
    for coordinate in range(0, config.frame_height_px + 1, int(config.cell_px)):
        pixel = coordinate * scale
        draw.line((0, pixel, width, pixel), fill=grid_color, width=max(1, scale))

    table_left = int(round((config.frame_half_width_px - config.table_half_width_px) * scale))
    table_right = int(round((config.frame_half_width_px + config.table_half_width_px) * scale))
    table_top = int(round((config.frame_half_height_px - config.table_half_height_px) * scale))
    table_bottom = int(round((config.frame_half_height_px + config.table_half_height_px) * scale))
    draw.rectangle(
        (table_left, table_top, table_right, table_bottom),
        outline=(35, 91, 160),
        width=3 * scale,
    )

    roi_left = int(round((config.frame_half_width_px - config.roi_half_width_px) * scale))
    roi_right = int(round((config.frame_half_width_px + config.roi_half_width_px) * scale))
    roi_top = int(round((config.frame_half_height_px - config.roi_half_height_px) * scale))
    roi_bottom = int(round((config.frame_half_height_px + config.roi_half_height_px) * scale))
    _draw_dashed_rectangle(
        draw,
        (roi_left, roi_top, roi_right, roi_bottom),
        fill=(225, 125, 35),
        width=2 * scale,
        dash=7 * scale,
    )

    # The trace is a debug-only overlay and is never part of production rendering.
    trace_points = [
        _world_to_image(point, config, scale)
        for point in trajectory.ball_center_xy[: frame_index + 1]
    ]
    if len(trace_points) >= 2:
        draw.line(trace_points, fill=(72, 156, 95), width=2 * scale)

    barrier_polygon = [
        _world_to_image(vertex, config, scale) for vertex in trajectory.barrier_vertices_xy
    ]
    draw.polygon(barrier_polygon, fill=(185, 190, 198), outline=(35, 39, 47))
    draw.line(barrier_polygon + [barrier_polygon[0]], fill=(35, 39, 47), width=2 * scale)

    event = result.collision_event
    time_s = float(trajectory.frame_times_s[frame_index])
    if (
        event.surface_contact_point_xy is not None
        and event.first_contact_time_s is not None
        and time_s >= event.first_contact_time_s
    ):
        contact_pixel = _world_to_image(event.surface_contact_point_xy, config, scale)
        marker_radius = 4 * scale
        draw.ellipse(
            (
                contact_pixel[0] - marker_radius,
                contact_pixel[1] - marker_radius,
                contact_pixel[0] + marker_radius,
                contact_pixel[1] + marker_radius,
            ),
            fill=(255, 196, 0),
            outline=(90, 60, 0),
            width=scale,
        )

    center = _world_to_image(trajectory.ball_center_xy[frame_index], config, scale)
    radius = int(round(config.ball_radius_px * scale))
    # Never encode validity in object appearance; valid and invalid branches share the same skin.
    ball_fill = (217, 65, 74)
    draw.ellipse(
        (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius),
        fill=ball_fill,
        outline=(65, 18, 23),
        width=2 * scale,
    )

    font_large = _font(ImageFont, 12 * scale)
    font_small = _font(ImageFont, 10 * scale)
    banner_height = 57 * scale
    draw.rectangle((0, 0, width, banner_height), fill=(255, 255, 255), outline=(205, 205, 205))
    collision_text = "yes" if result.contact.true_barrier_collision_exists else "no"
    impact_text = (
        "N/A" if event.impact_angle_deg is None else f"{event.impact_angle_deg:.1f}°"
    )
    status_text = result.contact.status.upper()
    if judgment_labels is not None:
        validity = "VALID" if judgment_labels.validity_binary else "INVALID"
        status_text = f"JUDGMENT {validity}"
    line_one = (
        f"{status_text} | hit={collision_text} | impact={impact_text} | "
        f"speed={result.scene.speed_cells_per_s:.2f} cell/s"
    )
    line_two = (
        f"frame={frame_index:02d}/{config.num_frames - 1:02d}  t={time_s:.3f}s | "
        f"theta_v={math.degrees(result.scene.velocity_angle_rad):.1f}° | "
        f"barrier_phi={math.degrees(result.scene.barrier_axis_angle_rad):.1f}°"
    )
    if judgment_labels is not None and not judgment_labels.validity_binary:
        line_two += f" | delta={judgment_labels.angular_violation_deg:.1f}°"
    draw.text((7 * scale, 5 * scale), line_one, fill=(20, 20, 20), font=font_large)
    draw.text((7 * scale, 30 * scale), line_two, fill=(45, 45, 45), font=font_small)

    is_context = frame_index < config.num_context_frames
    phase = "CONTEXT" if is_context else "FUTURE"
    phase_color = (37, 99, 171) if is_context else (42, 138, 74)
    phase_text = f"{phase}  frame {frame_index}"
    text_box = draw.textbbox((0, 0), phase_text, font=font_large)
    text_width = text_box[2] - text_box[0]
    text_height = text_box[3] - text_box[1]
    padding = 5 * scale
    x0 = width - text_width - 2 * padding - 6 * scale
    y0 = height - text_height - 2 * padding - 6 * scale
    draw.rounded_rectangle(
        (x0, y0, width - 6 * scale, height - 6 * scale),
        radius=4 * scale,
        fill=phase_color,
    )
    draw.text((x0 + padding, y0 + padding), phase_text, fill="white", font=font_large)

    legend = "table=blue | ROI=orange | trail=green"
    draw.text((7 * scale, (config.frame_height_px - 16) * scale), legend, fill=(70, 70, 70), font=font_small)

    if scale != 1:
        image = image.resize(
            (config.frame_width_px, config.frame_height_px), resample=Image.Resampling.LANCZOS
        )
    return image


def render_debug_video(
    result: SimulationResult,
    output_path: Path,
    config: PhysicsConfig,
    *,
    trajectory: Trajectory | None = None,
    judgment_labels: JudgmentLabels | None = None,
    supersample: int = 2,
) -> None:
    """Render one trajectory to a clear H.264 MP4 for human inspection."""
    _, _, _, imageio_ffmpeg = _load_render_dependencies()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    active_trajectory = trajectory or result.trajectory
    writer = imageio_ffmpeg.write_frames(
        str(output_path),
        (config.frame_width_px, config.frame_height_px),
        fps=config.fps,
        codec="libx264",
        pix_fmt_in="rgb24",
        pix_fmt_out="yuv420p",
        quality=7,
        ffmpeg_log_level="warning",
        output_params=["-movflags", "+faststart"],
    )
    writer.send(None)
    try:
        for frame_index in range(config.num_frames):
            frame = _draw_frame(
                result,
                active_trajectory,
                frame_index,
                config,
                supersample,
                judgment_labels,
            )
            writer.send(np.asarray(frame, dtype=np.uint8).tobytes())
    finally:
        writer.close()
