"""Balanced Contact-dataset selection and production rendering orchestration."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from . import __version__
from .config import PhysicsConfig
from .renderer import (
    ALL_RENDER_FAMILIES,
    RENDERER_VERSION,
    AppearanceSpec,
    AssetBank,
    RenderFamily,
    appearance_to_dict,
    render_video,
    sample_appearance_spec,
)
from .sampler import sample_scene
from .serialization import dumps_json, write_json
from .simulator import simulate_scene


@dataclass(frozen=True, slots=True)
class BalancedContactSelection:
    positive_proposal_indices: tuple[int, ...]
    negative_proposal_indices: tuple[int, ...]
    proposal_status_counts: dict[str, int]

    @property
    def count_per_class(self) -> int:
        return len(self.positive_proposal_indices)


def select_balanced_contact_indices(
    *,
    config: PhysicsConfig,
    num_proposals: int,
    scene_seed: int,
    selection_seed: int,
    max_per_class: int | None = None,
) -> BalancedContactSelection:
    """Keep positives and randomly downsample negatives to the same final count."""

    if num_proposals <= 0:
        raise ValueError("num_proposals must be positive")
    if max_per_class is not None and max_per_class <= 0:
        raise ValueError("max_per_class must be positive when provided")
    positives: list[int] = []
    negatives: list[int] = []
    counts: Counter[str] = Counter()
    for proposal_index in range(num_proposals):
        result = simulate_scene(sample_scene(config, scene_seed, proposal_index), config)
        counts[result.contact.status] += 1
        if result.contact.status == "positive":
            positives.append(proposal_index)
        elif result.contact.status == "negative":
            negatives.append(proposal_index)

    if not positives:
        raise RuntimeError("no accepted positive scenes were found")
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(selection_seed)))
    if max_per_class is not None and len(positives) > max_per_class:
        positives = sorted(
            int(index)
            for index in rng.choice(positives, size=max_per_class, replace=False).tolist()
        )
    target = len(positives)
    if len(negatives) < target:
        raise RuntimeError(
            f"not enough negatives for 50:50 selection: positives={target}, negatives={len(negatives)}"
        )
    selected_negatives = sorted(
        int(index) for index in rng.choice(negatives, size=target, replace=False).tolist()
    )
    return BalancedContactSelection(
        positive_proposal_indices=tuple(positives),
        negative_proposal_indices=tuple(selected_negatives),
        proposal_status_counts=dict(counts),
    )


def _balanced_family_assignments(
    count: int,
    families: tuple[RenderFamily, ...],
    rng: np.random.Generator,
) -> list[RenderFamily]:
    assignments = [families[index % len(families)] for index in range(count)]
    rng.shuffle(assignments)
    return assignments


def _derived_render_seed(root_seed: int, proposal_index: int, family: RenderFamily) -> int:
    family_code = ALL_RENDER_FAMILIES.index(family)
    sequence = np.random.SeedSequence([root_seed, proposal_index, family_code, 0xA97E_4D21])
    words = sequence.generate_state(2, dtype=np.uint32)
    return int(words[0]) | (int(words[1]) << 32)


def _write_jsonl_line(stream, value: object) -> None:
    stream.write(dumps_json(value) + "\n")


def _validate_families(families: Iterable[str]) -> tuple[RenderFamily, ...]:
    values = tuple(families)
    if not values:
        raise ValueError("at least one render family is required")
    invalid = [family for family in values if family not in ALL_RENDER_FAMILIES]
    if invalid:
        raise ValueError(f"unknown render families: {invalid}")
    if len(set(values)) != len(values):
        raise ValueError("render families must not contain duplicates")
    return values  # type: ignore[return-value]


def render_balanced_contact_dataset(
    *,
    config: PhysicsConfig,
    num_proposals: int,
    scene_seed: int,
    selection_seed: int,
    render_seed_root: int,
    output_dir: Path,
    asset_bank_root: Path,
    families: Iterable[str] = ALL_RENDER_FAMILIES,
    max_per_class: int | None = None,
    supersample: int = 2,
) -> dict[str, object]:
    """Render a label-balanced Contact dataset and JSONL index without assigning splits."""

    selected_families = _validate_families(families)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    index_dir = output_dir / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    asset_bank = AssetBank(asset_bank_root)
    selection = select_balanced_contact_indices(
        config=config,
        num_proposals=num_proposals,
        scene_seed=scene_seed,
        selection_seed=selection_seed,
        max_per_class=max_per_class,
    )

    assignment_rng = np.random.Generator(
        np.random.PCG64(np.random.SeedSequence([selection_seed, 0x6F1A_2C93]))
    )
    positive_families = _balanced_family_assignments(
        selection.count_per_class, selected_families, assignment_rng
    )
    negative_families = _balanced_family_assignments(
        selection.count_per_class, selected_families, assignment_rng
    )
    jobs = [
        ("positive", index, family)
        for index, family in zip(selection.positive_proposal_indices, positive_families, strict=True)
    ] + [
        ("negative", index, family)
        for index, family in zip(selection.negative_proposal_indices, negative_families, strict=True)
    ]

    appearance_path = index_dir / "appearances.jsonl"
    render_path = index_dir / "renders.jsonl"
    contact_path = output_dir / "manifests" / "contact.jsonl"
    contact_path.parent.mkdir(parents=True, exist_ok=True)
    rendered_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    with (
        appearance_path.open("w", encoding="utf-8") as appearance_stream,
        render_path.open("w", encoding="utf-8") as render_stream,
        contact_path.open("w", encoding="utf-8") as contact_stream,
    ):
        for status, proposal_index, family in jobs:
            result = simulate_scene(sample_scene(config, scene_seed, proposal_index), config)
            if result.contact.status != status:
                raise RuntimeError("replayed proposal status differs from balanced selection")
            render_seed = _derived_render_seed(render_seed_root, proposal_index, family)
            appearance: AppearanceSpec = sample_appearance_spec(
                latent_scene_id=result.scene.latent_scene_id,
                render_seed=render_seed,
                asset_bank=asset_bank,
                render_family=family,
            )
            filename = f"{proposal_index:08d}_{result.scene.latent_scene_id}.mp4"
            video_path = output_dir / "videos" / family / status / filename
            render_record = render_video(
                result.trajectory,
                appearance,
                video_path,
                asset_bank,
                config,
                supersample=supersample,
            )
            relative_video_path = video_path.relative_to(output_dir).as_posix()
            render_dict = asdict(render_record)
            render_dict["video_path"] = relative_video_path
            _write_jsonl_line(appearance_stream, appearance_to_dict(appearance))
            _write_jsonl_line(render_stream, render_dict)
            _write_jsonl_line(
                contact_stream,
                {
                    "sample_id": render_record.render_variant_id,
                    "latent_scene_id": result.scene.latent_scene_id,
                    "trajectory_variant_id": result.trajectory.trajectory_variant_id,
                    "render_variant_id": render_record.render_variant_id,
                    "appearance_spec_id": appearance.appearance_spec_id,
                    "video_path": relative_video_path,
                    "split": None,
                    "render_regime": appearance.render_regime,
                    "render_family": appearance.render_family,
                    "status": result.contact.status,
                    "contact_binary": result.contact.contact_binary,
                    "observation_start_frame": 0,
                    "observation_end_frame": config.num_context_frames - 1,
                    "context_frame_indices": list(range(config.num_context_frames)),
                    "future_frame_indices": list(
                        range(config.num_context_frames, config.num_frames)
                    ),
                },
            )
            rendered_counts[status] += 1
            family_counts[family] += 1

    summary: dict[str, object] = {
        "dataset_version": "v1-renderer-pilot",
        "simulator_version": __version__,
        "renderer_version": RENDERER_VERSION,
        "asset_bank_version": asset_bank.manifest["asset_bank_version"],
        "physics_config_hash": config.config_hash(),
        "num_proposals": num_proposals,
        "scene_seed": scene_seed,
        "selection_seed": selection_seed,
        "render_seed_root": render_seed_root,
        "split_assignment": None,
        "requested_families": list(selected_families),
        "proposal_status_counts": selection.proposal_status_counts,
        "selected_positive_count": selection.count_per_class,
        "selected_negative_count": selection.count_per_class,
        "rendered_status_counts": dict(rendered_counts),
        "rendered_family_counts": dict(family_counts),
        "positive_fraction": 0.5,
        "paths": {
            "appearances": appearance_path.relative_to(output_dir).as_posix(),
            "renders": render_path.relative_to(output_dir).as_posix(),
            "contact_manifest": contact_path.relative_to(output_dir).as_posix(),
        },
    }
    write_json(output_dir / "dataset_summary.json", summary)
    return summary

