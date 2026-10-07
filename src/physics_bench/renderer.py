"""Production renderer for latent trajectories and explicit appearance specifications."""

from __future__ import annotations

import colorsys
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any, Iterator, Literal

import numpy as np

from .assets import (
    ASSET_BANK_VERSION,
    BALL_COLORS,
    BARRIER_COLORS,
    OUTSIDE_COLORS,
    RAIL_COLORS,
    SURFACE_COLORS,
    AssetBankConfig,
    compose_background_layers,
)
from .config import PhysicsConfig
from .models import Trajectory


RENDERER_VERSION = "renderer-v1-2026-10-07"
RenderRegime = Literal["canonical", "diverse"]
RenderFamily = Literal["canonical_neutral", "billiards", "air_hockey", "tabletop"]
RGB = tuple[int, int, int]
DIVERSE_FAMILIES: tuple[RenderFamily, ...] = ("billiards", "air_hockey", "tabletop")
ALL_RENDER_FAMILIES: tuple[RenderFamily, ...] = (
    "canonical_neutral",
    "billiards",
    "air_hockey",
    "tabletop",
)


@dataclass(frozen=True, slots=True)
class AppearanceSpec:
    appearance_spec_id: str
    render_seed: int
    asset_bank_version: str
    renderer_version: str

    render_regime: RenderRegime
    render_family: RenderFamily

    surface_style_id: str
    surface_base_rgb: RGB
    surface_texture_id: str
    surface_texture_seed: int
    surface_texture_strength: float
    surface_brightness_gain: float
    surface_saturation_gain: float
    surface_hue_jitter_deg: float

    table_rail_style_id: str
    outside_background_style_id: str

    ball_color_id: str
    ball_base_rgb: RGB
    ball_brightness_gain: float
    ball_saturation_gain: float
    ball_hue_jitter_deg: float

    barrier_material_id: str
    barrier_base_rgb: RGB
    barrier_brightness_gain: float
    barrier_texture_strength: float
    bolt_style_id: str
    bolt_count: int

    global_brightness_gain: float
    global_gamma: float
    global_saturation_gain: float

    marking_style_id: str | None

    support_inside_barrier_footprint: bool
    motion_blur: bool
    directional_light: bool
    cast_shadow: bool


@dataclass(frozen=True, slots=True)
class RenderRecord:
    render_variant_id: str
    appearance_spec_id: str
    trajectory_variant_id: str
    video_path: str
    frame_count: int
    fps: int
    width_px: int
    height_px: int
    codec: str


class AssetBank:
    """Read and validate the versioned procedural PNG asset bank."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        manifest_path = self.root / "manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"asset-bank manifest not found: {manifest_path}")
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if self.manifest.get("asset_bank_version") != ASSET_BANK_VERSION:
            raise ValueError(
                "asset bank version mismatch: "
                f"expected {ASSET_BANK_VERSION!r}, got {self.manifest.get('asset_bank_version')!r}"
            )
        self.records = {
            str(record["asset_id"]): record for record in self.manifest.get("assets", [])
        }

    def record(self, asset_id: str) -> dict[str, Any]:
        try:
            return self.records[asset_id]
        except KeyError as exc:
            raise KeyError(f"asset ID not present in bank: {asset_id}") from exc

    def load(self, asset_id: str):
        try:
            from PIL import Image
        except ImportError as exc:  # pragma: no cover - exercised by CLI error path
            raise RuntimeError(
                "Rendering requires Pillow: install with `uv sync --extra render`."
            ) from exc
        record = self.record(asset_id)
        path = self.root / str(record["path"])
        with Image.open(path) as image:
            return image.copy()


def _validate_seed(seed: int) -> None:
    if not 0 <= seed < 1 << 64:
        raise ValueError("render_seed must fit uint64")


def _appearance_id(latent_scene_id: str, render_seed: int) -> str:
    return f"{latent_scene_id}:appearance:{render_seed:016x}"


def _texture_strength(family: RenderFamily) -> float:
    return {
        "canonical_neutral": 0.032,
        "billiards": 0.018,
        "air_hockey": 0.006,
        "tabletop": 0.030,
    }[family]


def _barrier_texture_strength(family: RenderFamily) -> float:
    return 0.0 if family == "canonical_neutral" else 0.009


def _base_color_by_name(
    entries: tuple[tuple[str, RGB], ...],
    index: int,
) -> tuple[str, RGB]:
    name, color = entries[index]
    return name, color


def _jittered_rgb(
    rgb: RGB,
    brightness: float,
    saturation: float,
    hue_deg: float,
) -> np.ndarray:
    red, green, blue = (channel / 255.0 for channel in rgb)
    hue, sat, value = colorsys.rgb_to_hsv(red, green, blue)
    adjusted = colorsys.hsv_to_rgb(
        (hue + hue_deg / 360.0) % 1.0,
        min(1.0, max(0.0, sat * saturation)),
        min(1.0, max(0.0, value * brightness)),
    )
    return 255.0 * np.asarray(adjusted, dtype=np.float64)


def _has_minimum_ball_contrast(
    surface_rgb: RGB,
    ball_rgb: RGB,
    *,
    surface_brightness: float,
    surface_saturation: float,
    surface_hue: float,
    ball_brightness: float,
    ball_saturation: float,
    ball_hue: float,
) -> bool:
    surface = _jittered_rgb(
        surface_rgb, surface_brightness, surface_saturation, surface_hue
    )
    ball = _jittered_rgb(ball_rgb, ball_brightness, ball_saturation, ball_hue)
    rgb_distance = float(np.linalg.norm(surface - ball))
    luma_weights = np.asarray((0.2126, 0.7152, 0.0722), dtype=np.float64)
    luma_difference = abs(float(np.dot(surface - ball, luma_weights)))
    return rgb_distance >= 55.0 or luma_difference >= 42.0


def sample_appearance_spec(
    *,
    latent_scene_id: str,
    render_seed: int,
    asset_bank: AssetBank,
    render_family: RenderFamily | None = None,
) -> AppearanceSpec:
    """Sample one replayable appearance without consulting any physics label."""

    _validate_seed(render_seed)
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(render_seed)))
    family: RenderFamily
    if render_family is None:
        family = DIVERSE_FAMILIES[int(rng.integers(0, len(DIVERSE_FAMILIES)))]
    else:
        family = render_family
    if family not in ALL_RENDER_FAMILIES:
        raise ValueError(f"unknown render family: {family}")

    canonical = family == "canonical_neutral"
    regime: RenderRegime = "canonical" if canonical else "diverse"
    if canonical:
        surface_index = outside_index = rail_index = ball_index = barrier_index = 0
        marking_index = None
        surface_brightness = surface_saturation = 1.0
        surface_hue = 0.0
        ball_brightness = ball_saturation = 1.0
        ball_hue = 0.0
        barrier_brightness = 1.0
        global_brightness = global_gamma = global_saturation = 1.0
    else:
        surface_index = int(rng.integers(0, len(SURFACE_COLORS[family])))
        outside_index = int(rng.integers(0, len(OUTSIDE_COLORS[family])))
        rail_index = int(rng.integers(0, len(RAIL_COLORS[family])))
        ball_candidates = rng.permutation(len(BALL_COLORS[family])).tolist()
        ball_index = int(ball_candidates[0])
        barrier_index = int(rng.integers(0, len(BARRIER_COLORS[family])))
        marking_index = int(rng.integers(0, 3)) if family == "air_hockey" else None
        surface_brightness = float(rng.uniform(0.96, 1.04))
        surface_saturation = float(rng.uniform(0.96, 1.04))
        surface_hue = float(rng.uniform(-2.0, 2.0))
        ball_brightness = float(rng.uniform(0.95, 1.05))
        ball_saturation = float(rng.uniform(0.95, 1.05))
        ball_hue = float(rng.uniform(-2.0, 2.0))
        barrier_brightness = float(rng.uniform(0.96, 1.04))
        global_brightness = float(rng.uniform(0.96, 1.04))
        global_gamma = float(rng.uniform(0.97, 1.03))
        global_saturation = float(rng.uniform(0.96, 1.04))
        for candidate in ball_candidates:
            candidate_rgb = BALL_COLORS[family][int(candidate)][1]
            if _has_minimum_ball_contrast(
                SURFACE_COLORS[family][surface_index],
                candidate_rgb,
                surface_brightness=surface_brightness,
                surface_saturation=surface_saturation,
                surface_hue=surface_hue,
                ball_brightness=ball_brightness,
                ball_saturation=ball_saturation,
                ball_hue=ball_hue,
            ):
                ball_index = int(candidate)
                break
        else:  # pragma: no cover - current palettes always contain a valid candidate
            raise RuntimeError("no ball palette entry satisfies the minimum-contrast check")

    surface_id = f"{family}_surface_{surface_index}"
    outside_id = f"{family}_outside_{outside_index}"
    rail_id = f"{family}_rail_{rail_index}"
    ball_name, ball_rgb = _base_color_by_name(BALL_COLORS[family], ball_index)
    barrier_name, barrier_rgb = _base_color_by_name(BARRIER_COLORS[family], barrier_index)
    ball_id = f"{family}_ball_{ball_name}"
    barrier_id = f"{family}_barrier_{barrier_name}"
    marking_id = None if marking_index is None else f"air_hockey_marking_{marking_index}"
    surface_record = asset_bank.record(surface_id)

    return AppearanceSpec(
        appearance_spec_id=_appearance_id(latent_scene_id, render_seed),
        render_seed=render_seed,
        asset_bank_version=ASSET_BANK_VERSION,
        renderer_version=RENDERER_VERSION,
        render_regime=regime,
        render_family=family,
        surface_style_id=surface_id,
        surface_base_rgb=tuple(SURFACE_COLORS[family][surface_index]),
        surface_texture_id=surface_id,
        surface_texture_seed=int(surface_record["seed"]),
        surface_texture_strength=_texture_strength(family),
        surface_brightness_gain=surface_brightness,
        surface_saturation_gain=surface_saturation,
        surface_hue_jitter_deg=surface_hue,
        table_rail_style_id=rail_id,
        outside_background_style_id=outside_id,
        ball_color_id=ball_id,
        ball_base_rgb=tuple(ball_rgb),
        ball_brightness_gain=ball_brightness,
        ball_saturation_gain=ball_saturation,
        ball_hue_jitter_deg=ball_hue,
        barrier_material_id=barrier_id,
        barrier_base_rgb=tuple(barrier_rgb),
        barrier_brightness_gain=barrier_brightness,
        barrier_texture_strength=_barrier_texture_strength(family),
        bolt_style_id="four_symmetric_cross_recess_screws",
        bolt_count=4,
        global_brightness_gain=global_brightness,
        global_gamma=global_gamma,
        global_saturation_gain=global_saturation,
        marking_style_id=marking_id,
        support_inside_barrier_footprint=True,
        motion_blur=False,
        directional_light=False,
        cast_shadow=False,
    )


def _load_render_dependencies():
    try:
        from PIL import Image, ImageEnhance
        import imageio_ffmpeg
    except ImportError as exc:  # pragma: no cover - exercised by CLI error path
        raise RuntimeError(
            "Production rendering requires the 'render' extra: `uv sync --extra render`."
        ) from exc
    return Image, ImageEnhance, imageio_ffmpeg


def _adjust_image(
    image: Any,
    *,
    brightness: float = 1.0,
    saturation: float = 1.0,
    hue_deg: float = 0.0,
    gamma: float = 1.0,
):
    Image, ImageEnhance, _ = _load_render_dependencies()
    alpha = image.getchannel("A") if image.mode == "RGBA" else None
    rgb = image.convert("RGB")
    if saturation != 1.0:
        rgb = ImageEnhance.Color(rgb).enhance(saturation)
    if brightness != 1.0:
        rgb = ImageEnhance.Brightness(rgb).enhance(brightness)
    if hue_deg != 0.0:
        hsv = np.asarray(rgb.convert("HSV"), dtype=np.uint8).copy()
        shift = int(round(hue_deg / 360.0 * 255.0))
        hsv[:, :, 0] = (hsv[:, :, 0].astype(np.int16) + shift) % 256
        rgb = Image.fromarray(hsv, mode="HSV").convert("RGB")
    if gamma != 1.0:
        inverse_gamma = 1.0 / gamma
        lut = [int(round(255.0 * ((value / 255.0) ** inverse_gamma))) for value in range(256)]
        rgb = rgb.point(lut * 3)
    if alpha is None:
        return rgb
    rgba = rgb.convert("RGBA")
    rgba.putalpha(alpha)
    return rgba


def _prepare_appearance(
    appearance: AppearanceSpec,
    asset_bank: AssetBank,
    asset_config: AssetBankConfig,
) -> tuple[Any, Any, Any]:
    outside = asset_bank.load(appearance.outside_background_style_id).convert("RGB")
    surface = asset_bank.load(appearance.surface_style_id).convert("RGB")
    surface = _adjust_image(
        surface,
        brightness=appearance.surface_brightness_gain,
        saturation=appearance.surface_saturation_gain,
        hue_deg=appearance.surface_hue_jitter_deg,
    )
    rail = asset_bank.load(appearance.table_rail_style_id).convert("RGBA")
    marking = (
        None
        if appearance.marking_style_id is None
        else asset_bank.load(appearance.marking_style_id).convert("RGBA")
    )
    background = compose_background_layers(
        appearance.render_family,
        outside,
        surface,
        rail,
        marking,
        asset_config,
    )
    ball = _adjust_image(
        asset_bank.load(appearance.ball_color_id).convert("RGBA"),
        brightness=appearance.ball_brightness_gain,
        saturation=appearance.ball_saturation_gain,
        hue_deg=appearance.ball_hue_jitter_deg,
    )
    barrier = _adjust_image(
        asset_bank.load(appearance.barrier_material_id).convert("RGBA"),
        brightness=appearance.barrier_brightness_gain,
    )
    return background, ball, barrier


def _world_to_image(point_xy: np.ndarray, config: PhysicsConfig) -> tuple[float, float]:
    return (
        float(point_xy[0]) + config.frame_half_width_px,
        config.frame_half_height_px - float(point_xy[1]),
    )


def _paste_centered(canvas: Any, sprite: Any, center_xy: tuple[float, float], scale: int) -> None:
    center_x = center_xy[0] * scale
    center_y = center_xy[1] * scale
    left = int(round(center_x - sprite.width / 2.0))
    top = int(round(center_y - sprite.height / 2.0))
    canvas.paste(sprite, (left, top), sprite)


def iter_rendered_frames(
    trajectory: Trajectory,
    appearance: AppearanceSpec,
    asset_bank: AssetBank,
    config: PhysicsConfig,
    *,
    supersample: int = 2,
) -> Iterator[np.ndarray]:
    """Yield RGB frames; rendering depends only on trajectory and appearance."""

    if supersample < 1:
        raise ValueError("supersample must be >= 1")
    if len(trajectory.frame_times_s) != config.num_frames:
        raise ValueError("trajectory frame count differs from PhysicsConfig")
    if appearance.motion_blur or appearance.directional_light or appearance.cast_shadow:
        raise ValueError("renderer v1 forbids motion blur, directional light, and cast shadow")

    Image, _, _ = _load_render_dependencies()
    asset_config = AssetBankConfig(supersample=max(2, supersample))
    background, ball, barrier = _prepare_appearance(appearance, asset_bank, asset_config)
    frame_size = (config.frame_width_px * supersample, config.frame_height_px * supersample)
    static_frame = background.resize(frame_size, Image.Resampling.LANCZOS)

    barrier_center_world = np.mean(trajectory.barrier_vertices_xy, axis=0)
    barrier_center_image = _world_to_image(barrier_center_world, config)
    tangent = np.asarray(trajectory.barrier_tangent_xy, dtype=np.float64)
    # PIL's positive rotation is visually counter-clockwise, which already maps a
    # world-space (x right, y up) axis to image coordinates (x right, y down).
    barrier_angle_deg = math.degrees(math.atan2(float(tangent[1]), float(tangent[0])))
    barrier_large = barrier.resize(
        (int(round(barrier.width * supersample)), int(round(barrier.height * supersample))),
        Image.Resampling.LANCZOS,
    )
    barrier_rotated = barrier_large.rotate(
        barrier_angle_deg,
        resample=Image.Resampling.BICUBIC,
        expand=True,
    )
    _paste_centered(static_frame, barrier_rotated, barrier_center_image, supersample)

    ball_large = ball.resize(
        (int(round(ball.width * supersample)), int(round(ball.height * supersample))),
        Image.Resampling.LANCZOS,
    )
    for frame_index in range(config.num_frames):
        frame = static_frame.copy()
        ball_center_image = _world_to_image(trajectory.ball_center_xy[frame_index], config)
        _paste_centered(frame, ball_large, ball_center_image, supersample)
        if supersample != 1:
            frame = frame.resize(
                (config.frame_width_px, config.frame_height_px),
                Image.Resampling.LANCZOS,
            )
        frame = _adjust_image(
            frame,
            brightness=appearance.global_brightness_gain,
            saturation=appearance.global_saturation_gain,
            gamma=appearance.global_gamma,
        )
        yield np.asarray(frame, dtype=np.uint8).copy()


def render_video(
    trajectory: Trajectory,
    appearance: AppearanceSpec,
    output_path: Path,
    asset_bank: AssetBank,
    config: PhysicsConfig,
    *,
    supersample: int = 2,
) -> RenderRecord:
    """Encode one production H.264 MP4 and return its canonical render record."""

    _, _, imageio_ffmpeg = _load_render_dependencies()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
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
        for frame in iter_rendered_frames(
            trajectory,
            appearance,
            asset_bank,
            config,
            supersample=supersample,
        ):
            writer.send(frame.tobytes())
    finally:
        writer.close()

    render_variant_id = (
        f"{trajectory.trajectory_variant_id}:render:{appearance.render_seed:016x}"
    )
    return RenderRecord(
        render_variant_id=render_variant_id,
        appearance_spec_id=appearance.appearance_spec_id,
        trajectory_variant_id=trajectory.trajectory_variant_id,
        video_path=str(output_path),
        frame_count=config.num_frames,
        fps=config.fps,
        width_px=config.frame_width_px,
        height_px=config.frame_height_px,
        codec="h264/libx264/yuv420p",
    )


def appearance_to_dict(appearance: AppearanceSpec) -> dict[str, Any]:
    return asdict(appearance)
