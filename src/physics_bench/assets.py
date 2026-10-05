"""Deterministic procedural visual-asset bank for renderer v1."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


ASSET_BANK_VERSION = "v1-procedural-2026-10-06"


@dataclass(frozen=True, slots=True)
class AssetBankConfig:
    """Geometry and replay settings for the static renderer asset bank."""

    seed: int = 20_261_006
    frame_size_px: int = 448
    table_width_px: int = 420
    table_height_px: int = 308
    rail_width_px: int = 8
    supersample: int = 4

    @property
    def surface_width_px(self) -> int:
        return self.table_width_px - 2 * self.rail_width_px

    @property
    def surface_height_px(self) -> int:
        return self.table_height_px - 2 * self.rail_width_px

    @property
    def table_left_px(self) -> int:
        return (self.frame_size_px - self.table_width_px) // 2

    @property
    def table_top_px(self) -> int:
        return (self.frame_size_px - self.table_height_px) // 2


SURFACE_COLORS: dict[str, tuple[tuple[int, int, int], ...]] = {
    "canonical_neutral": ((226, 226, 221),),
    "billiards": ((47, 112, 73), (37, 101, 68), (54, 121, 82), (43, 95, 70)),
    "air_hockey": ((238, 238, 235), (232, 235, 238), (244, 243, 237), (235, 238, 236)),
    "tabletop": ((225, 219, 205), (224, 226, 222), (232, 228, 218), (219, 225, 228)),
}

OUTSIDE_COLORS: dict[str, tuple[tuple[int, int, int], ...]] = {
    "canonical_neutral": ((48, 50, 52),),
    "billiards": ((44, 42, 40), (52, 48, 45)),
    "air_hockey": ((58, 61, 64), (66, 68, 70)),
    "tabletop": ((72, 70, 67), (68, 71, 72)),
}

RAIL_COLORS: dict[str, tuple[tuple[int, int, int], ...]] = {
    "canonical_neutral": ((108, 113, 118),),
    "billiards": ((74, 48, 34), (58, 42, 34), (83, 53, 37)),
    "air_hockey": ((92, 99, 105), (82, 91, 103), (110, 112, 114)),
    # The document names these materials but intentionally leaves exact RGB values adjustable.
    "tabletop": ((118, 116, 112), (157, 139, 112), (119, 126, 130)),
}

BALL_COLORS: dict[str, tuple[tuple[str, tuple[int, int, int]], ...]] = {
    "canonical_neutral": (("muted_red", (182, 62, 56)),),
    "billiards": (
        ("muted_red", (184, 72, 64)),
        ("cobalt_blue", (63, 99, 158)),
        ("ochre", (190, 147, 55)),
        ("muted_orange", (194, 103, 58)),
        ("ivory", (215, 208, 191)),
    ),
    "air_hockey": (
        ("red", (190, 61, 57)),
        ("blue", (55, 92, 154)),
        ("charcoal", (62, 66, 70)),
        ("orange", (201, 104, 50)),
        ("dark_teal", (42, 102, 106)),
    ),
    "tabletop": (
        ("red", (184, 67, 61)),
        ("blue", (62, 97, 151)),
        ("orange", (197, 111, 56)),
        ("dark_teal", (48, 103, 104)),
        ("charcoal", (69, 72, 74)),
    ),
}

BARRIER_COLORS: dict[str, tuple[tuple[str, tuple[int, int, int]], ...]] = {
    "canonical_neutral": (("canonical_dark_metal", (76, 81, 86)),),
    "billiards": (
        ("dark_wood", (82, 54, 39)),
        ("near_black", (52, 48, 45)),
        ("dark_brown", (96, 63, 43)),
    ),
    "air_hockey": (
        ("dark_plastic", (64, 69, 74)),
        ("blue_gray", (73, 84, 98)),
        ("light_plastic", (155, 159, 161)),
    ),
    "tabletop": (
        ("aluminum_gray", (130, 136, 140)),
        ("dark_metal", (69, 74, 78)),
        ("matte_black", (52, 54, 56)),
    ),
}


def _load_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:  # pragma: no cover - exercised by CLI error path
        raise RuntimeError(
            "Asset generation requires Pillow: install with `uv sync --extra render`."
        ) from exc
    return Image, ImageDraw, ImageFont


def _seed(root_seed: int, asset_id: str) -> int:
    payload = f"{root_seed}:{asset_id}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "little")


def _rng(root_seed: int, asset_id: str) -> np.random.Generator:
    return np.random.default_rng(_seed(root_seed, asset_id))


def _clip_rgb(values: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(values), 0, 255).astype(np.uint8)


def _fine_texture(
    size: tuple[int, int],
    base_rgb: tuple[int, int, int],
    rng: np.random.Generator,
    amplitude: float,
) -> np.ndarray:
    width, height = size
    base = np.asarray(base_rgb, dtype=np.float32)
    noise = rng.normal(0.0, amplitude * float(np.mean(base)), (height, width, 1))
    return _clip_rgb(base[None, None, :] + noise)


def _mottled_texture(
    size: tuple[int, int],
    base_rgb: tuple[int, int, int],
    rng: np.random.Generator,
    amplitude: float,
) -> np.ndarray:
    Image, _, _ = _load_pillow()
    width, height = size
    coarse_width = max(8, width // 20)
    coarse_height = max(8, height // 20)
    coarse = rng.normal(127.5, 34.0, (coarse_height, coarse_width)).clip(0, 255).astype(np.uint8)
    smooth = Image.fromarray(coarse, mode="L").resize((width, height), Image.Resampling.BICUBIC)
    low_frequency = (np.asarray(smooth, dtype=np.float32) - 127.5) / 127.5
    fine = rng.normal(0.0, 0.18, (height, width))
    variation = amplitude * (0.82 * low_frequency + 0.18 * fine)
    base = np.asarray(base_rgb, dtype=np.float32)
    return _clip_rgb(base[None, None, :] * (1.0 + variation[:, :, None]))


def _surface_image(
    family: str,
    index: int,
    config: AssetBankConfig,
) -> Any:
    Image, _, _ = _load_pillow()
    base_rgb = SURFACE_COLORS[family][index]
    size = (config.surface_width_px, config.surface_height_px)
    generator = _rng(config.seed, f"surface:{family}:{index}")
    if family == "canonical_neutral":
        array = np.broadcast_to(np.asarray(base_rgb, dtype=np.uint8), (size[1], size[0], 3)).copy()
    elif family == "billiards":
        array = _fine_texture(size, base_rgb, generator, amplitude=0.018)
    elif family == "air_hockey":
        array = _mottled_texture(size, base_rgb, generator, amplitude=0.006)
    else:
        array = _mottled_texture(size, base_rgb, generator, amplitude=0.018)
    return Image.fromarray(array, mode="RGB")


def _outside_image(
    family: str,
    index: int,
    config: AssetBankConfig,
) -> Any:
    Image, _, _ = _load_pillow()
    base_rgb = OUTSIDE_COLORS[family][index]
    size = (config.frame_size_px, config.frame_size_px)
    if family == "canonical_neutral":
        array = np.broadcast_to(np.asarray(base_rgb, dtype=np.uint8), (size[1], size[0], 3)).copy()
    else:
        array = _mottled_texture(
            size,
            base_rgb,
            _rng(config.seed, f"outside:{family}:{index}"),
            amplitude=0.008,
        )
    return Image.fromarray(array, mode="RGB")


def _rail_image(
    family: str,
    index: int,
    config: AssetBankConfig,
) -> Any:
    Image, ImageDraw, _ = _load_pillow()
    scale = config.supersample
    width = config.table_width_px * scale
    height = config.table_height_px * scale
    rail = config.rail_width_px * scale
    base_rgb = RAIL_COLORS[family][index]
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width - 1, height - 1), fill=(*base_rgb, 255))
    draw.rectangle((rail, rail, width - rail - 1, height - rail - 1), fill=(0, 0, 0, 0))

    # A uniform, non-directional inner/outer edge separates surface, rail, and outside.
    edge = tuple(max(0, channel - 20) for channel in base_rgb) + (255,)
    draw.rectangle((0, 0, width - 1, height - 1), outline=edge, width=scale)
    draw.rectangle((rail, rail, width - rail - 1, height - rail - 1), outline=edge, width=scale)

    if family == "billiards":
        pocket_rgb = (25, 24, 23, 255)
        radius = 8 * scale
        centers = (
            (0, 0),
            (width // 2, 0),
            (width - 1, 0),
            (0, height - 1),
            (width // 2, height - 1),
            (width - 1, height - 1),
        )
        for center_x, center_y in centers:
            draw.ellipse(
                (
                    center_x - radius,
                    center_y - radius,
                    center_x + radius,
                    center_y + radius,
                ),
                fill=pocket_rgb,
            )
    return image.resize(
        (config.table_width_px, config.table_height_px),
        Image.Resampling.LANCZOS,
    )


def _marking_image(index: int, config: AssetBankConfig) -> Any:
    Image, ImageDraw, _ = _load_pillow()
    scale = config.supersample
    width = config.surface_width_px * scale
    height = config.surface_height_px * scale
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    color = (139, 165, 181, 76)
    line = 2 * scale
    center_x = width // 2
    center_y = height // 2
    radius = 42 * scale
    draw.line((center_x, 0, center_x, height), fill=color, width=line)
    draw.ellipse(
        (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
        outline=color,
        width=line,
    )
    if index >= 1:
        inset = 38 * scale
        draw.rounded_rectangle(
            (inset, inset, width - inset, height - inset),
            radius=24 * scale,
            outline=color,
            width=line,
        )
    if index >= 2:
        goal_depth = 42 * scale
        goal_half_height = 58 * scale
        draw.arc(
            (-goal_depth, center_y - goal_half_height, goal_depth, center_y + goal_half_height),
            -90,
            90,
            fill=color,
            width=line,
        )
        draw.arc(
            (width - goal_depth, center_y - goal_half_height, width + goal_depth, center_y + goal_half_height),
            90,
            270,
            fill=color,
            width=line,
        )
    return image.resize(
        (config.surface_width_px, config.surface_height_px),
        Image.Resampling.LANCZOS,
    )


def _ball_image(rgb: tuple[int, int, int], config: AssetBankConfig) -> Any:
    Image, ImageDraw, _ = _load_pillow()
    diameter = 35
    scale = config.supersample
    image = Image.new("RGBA", (diameter * scale, diameter * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((0, 0, diameter * scale - 1, diameter * scale - 1), fill=(*rgb, 255))
    return image.resize((diameter, diameter), Image.Resampling.LANCZOS)


def _barrier_image(
    family: str,
    material_id: str,
    rgb: tuple[int, int, int],
    config: AssetBankConfig,
) -> Any:
    Image, ImageDraw, _ = _load_pillow()
    scale = config.supersample
    width_px, height_px = 140, 28
    width, height = width_px * scale, height_px * scale
    generator = _rng(config.seed, f"barrier:{family}:{material_id}")
    noise = generator.normal(0.0, 0.009 * float(np.mean(rgb)), (height, width, 1))
    noise = 0.5 * (noise + noise[::-1, ::-1])
    base = np.asarray(rgb, dtype=np.float32)[None, None, :]
    rgba = np.empty((height, width, 4), dtype=np.uint8)
    rgba[:, :, :3] = _clip_rgb(base + noise)
    rgba[:, :, 3] = 255
    image = Image.fromarray(rgba, mode="RGBA")
    draw = ImageDraw.Draw(image)

    dark = tuple(max(0, channel - 28) for channel in rgb) + (255,)
    light = tuple(min(255, channel + 24) for channel in rgb) + (255,)
    draw.rectangle((0, 0, width - 1, height - 1), outline=dark, width=scale)
    inset = 2 * scale
    draw.rectangle((inset, inset, width - inset - 1, height - inset - 1), outline=light, width=scale)

    bolt_rgb = (148, 153, 157, 255) if family == "canonical_neutral" else (166, 169, 171, 255)
    bolt_edge = (66, 69, 72, 255)
    center_x = (width - 1) / 2.0
    center_y = (height - 1) / 2.0
    radius = 2.5 * scale
    for u in (-45.0, 45.0):
        for v in (-5.0, 5.0):
            x = center_x + u * scale
            y = center_y + v * scale
            box = (x - radius, y - radius, x + radius, y + radius)
            draw.ellipse(box, fill=bolt_rgb, outline=bolt_edge, width=scale)

    image = image.resize((width_px, height_px), Image.Resampling.LANCZOS)
    # Enforce exact 180-degree sprite symmetry after antialiasing and quantization.
    array = np.asarray(image, dtype=np.uint16)
    symmetric = ((array + array[::-1, ::-1]) // 2).astype(np.uint8)
    return Image.fromarray(symmetric, mode="RGBA")


def _save_asset(
    image: Any,
    output_dir: Path,
    relative_path: Path,
    *,
    asset_id: str,
    kind: str,
    family: str,
    base_rgb: tuple[int, int, int] | None,
    seed: int | None,
    records: list[dict[str, Any]],
) -> Path:
    path = output_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    records.append(
        {
            "asset_id": asset_id,
            "kind": kind,
            "family": family,
            "path": relative_path.as_posix(),
            "mode": image.mode,
            "width_px": image.width,
            "height_px": image.height,
            "base_rgb": list(base_rgb) if base_rgb is not None else None,
            "seed": seed,
            "sha256": digest,
        }
    )
    return path


def _compose_background(
    outside: Any,
    surface: Any,
    rail: Any,
    marking: Any | None,
    config: AssetBankConfig,
) -> Any:
    image = outside.copy()
    surface_xy = (
        config.table_left_px + config.rail_width_px,
        config.table_top_px + config.rail_width_px,
    )
    image.paste(surface, surface_xy)
    if marking is not None:
        image.paste(marking, surface_xy, marking)
    image.paste(rail, (config.table_left_px, config.table_top_px), rail)
    return image


def _contact_sheet(previews: list[tuple[str, Any]], config: AssetBankConfig) -> Any:
    Image, ImageDraw, ImageFont = _load_pillow()
    thumb = 224
    label_height = 24
    columns = 4
    rows = (len(previews) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * thumb, rows * (thumb + label_height)), (236, 236, 234))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (label, preview) in enumerate(previews):
        column = index % columns
        row = index // columns
        x = column * thumb
        y = row * (thumb + label_height)
        sheet.paste(preview.resize((thumb, thumb), Image.Resampling.LANCZOS), (x, y))
        draw.rectangle((x, y + thumb, x + thumb, y + thumb + label_height), fill=(250, 250, 248))
        draw.text((x + 6, y + thumb + 6), label, fill=(30, 30, 30), font=font)
    return sheet


def _object_contact_sheet(objects: list[tuple[str, Any]]) -> Any:
    Image, ImageDraw, ImageFont = _load_pillow()
    cell_width = 224
    cell_height = 120
    columns = 4
    rows = (len(objects) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), (232, 233, 233))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (label, sprite) in enumerate(objects):
        column = index % columns
        row = index // columns
        x0 = column * cell_width
        y0 = row * cell_height
        if sprite.width == 35:
            display_size = (84, 84)
        else:
            display_size = (196, 39)
        display = sprite.resize(display_size, Image.Resampling.LANCZOS)
        x = x0 + (cell_width - display.width) // 2
        y = y0 + 5 + (84 - display.height) // 2
        sheet.paste(display, (x, y), display)
        draw.multiline_text((x0 + 6, y0 + 94), label, fill=(28, 30, 32), font=font, spacing=1)
    return sheet


def generate_asset_bank(
    output_dir: Path,
    config: AssetBankConfig | None = None,
) -> dict[str, Any]:
    """Generate all canonical and diverse v1 assets plus composed previews."""

    config = config or AssetBankConfig()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    cached_surfaces: dict[tuple[str, int], Any] = {}
    cached_outside: dict[tuple[str, int], Any] = {}
    cached_rails: dict[tuple[str, int], Any] = {}
    cached_markings: dict[int, Any] = {}
    previews: list[tuple[str, Any]] = []
    object_previews: list[tuple[str, Any]] = []

    for family in SURFACE_COLORS:
        for index, base_rgb in enumerate(SURFACE_COLORS[family]):
            asset_id = f"{family}_surface_{index}"
            image = _surface_image(family, index, config)
            cached_surfaces[(family, index)] = image
            _save_asset(
                image,
                output_dir,
                Path("surfaces") / family / f"surface_{index}.png",
                asset_id=asset_id,
                kind="surface",
                family=family,
                base_rgb=base_rgb,
                seed=_seed(config.seed, f"surface:{family}:{index}"),
                records=records,
            )

        for index, base_rgb in enumerate(OUTSIDE_COLORS[family]):
            asset_id = f"{family}_outside_{index}"
            image = _outside_image(family, index, config)
            cached_outside[(family, index)] = image
            _save_asset(
                image,
                output_dir,
                Path("outside") / family / f"outside_{index}.png",
                asset_id=asset_id,
                kind="outside_background",
                family=family,
                base_rgb=base_rgb,
                seed=_seed(config.seed, f"outside:{family}:{index}"),
                records=records,
            )

        for index, base_rgb in enumerate(RAIL_COLORS[family]):
            asset_id = f"{family}_rail_{index}"
            image = _rail_image(family, index, config)
            cached_rails[(family, index)] = image
            _save_asset(
                image,
                output_dir,
                Path("rails") / family / f"rail_{index}.png",
                asset_id=asset_id,
                kind="table_rail",
                family=family,
                base_rgb=base_rgb,
                seed=None,
                records=records,
            )

        for color_id, base_rgb in BALL_COLORS[family]:
            asset_id = f"{family}_ball_{color_id}"
            ball = _ball_image(base_rgb, config)
            object_previews.append((f"{family}\nball: {color_id}", ball))
            _save_asset(
                ball,
                output_dir,
                Path("balls") / family / f"{color_id}.png",
                asset_id=asset_id,
                kind="ball",
                family=family,
                base_rgb=base_rgb,
                seed=None,
                records=records,
            )

        for material_id, base_rgb in BARRIER_COLORS[family]:
            asset_id = f"{family}_barrier_{material_id}"
            barrier = _barrier_image(family, material_id, base_rgb, config)
            object_previews.append((f"{family}\nbarrier: {material_id}", barrier))
            _save_asset(
                barrier,
                output_dir,
                Path("barriers") / family / f"{material_id}.png",
                asset_id=asset_id,
                kind="barrier",
                family=family,
                base_rgb=base_rgb,
                seed=_seed(config.seed, f"barrier:{family}:{material_id}"),
                records=records,
            )

    for index in range(3):
        image = _marking_image(index, config)
        cached_markings[index] = image
        _save_asset(
            image,
            output_dir,
            Path("markings") / "air_hockey" / f"marking_{index}.png",
            asset_id=f"air_hockey_marking_{index}",
            kind="marking",
            family="air_hockey",
            base_rgb=None,
            seed=None,
            records=records,
        )

    for family, surface_colors in SURFACE_COLORS.items():
        for index in range(len(surface_colors)):
            outside_index = index % len(OUTSIDE_COLORS[family])
            rail_index = index % len(RAIL_COLORS[family])
            marking = cached_markings[index % 3] if family == "air_hockey" else None
            preview = _compose_background(
                cached_outside[(family, outside_index)],
                cached_surfaces[(family, index)],
                cached_rails[(family, rail_index)],
                marking,
                config,
            )
            previews.append((f"{family} / {index}", preview))
            _save_asset(
                preview,
                output_dir,
                Path("background_previews") / family / f"background_{index}.png",
                asset_id=f"{family}_background_preview_{index}",
                kind="background_preview",
                family=family,
                base_rgb=surface_colors[index],
                seed=None,
                records=records,
            )

    contact_sheet = _contact_sheet(previews, config)
    _save_asset(
        contact_sheet,
        output_dir,
        Path("contact_sheet.png"),
        asset_id="asset_bank_contact_sheet",
        kind="contact_sheet",
        family="all",
        base_rgb=None,
        seed=None,
        records=records,
    )
    object_contact_sheet = _object_contact_sheet(object_previews)
    _save_asset(
        object_contact_sheet,
        output_dir,
        Path("object_contact_sheet.png"),
        asset_id="object_asset_contact_sheet",
        kind="object_contact_sheet",
        family="all",
        base_rgb=None,
        seed=None,
        records=records,
    )

    manifest = {
        "asset_bank_version": ASSET_BANK_VERSION,
        "generator": "physics_bench.assets.generate_asset_bank",
        "procedural_only": True,
        "root_seed": config.seed,
        "frame_size_px": config.frame_size_px,
        "table_size_px": [config.table_width_px, config.table_height_px],
        "surface_size_px": [config.surface_width_px, config.surface_height_px],
        "rail_width_px": config.rail_width_px,
        "ball_diameter_px": 35,
        "barrier_size_px": [140, 28],
        "supersample": config.supersample,
        "assets": records,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
