"""Large pure-latent pilot generation and distribution diagnostics."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import gzip
import json
import math
from pathlib import Path
import time
from typing import Generic, TypeVar

import numpy as np

from . import __version__
from .config import PhysicsConfig
from .judgment import generate_judgment_pair
from .models import JudgmentPair, SimulationResult
from .sampler import sample_scene
from .serialization import dumps_json, to_builtin, write_json
from .simulator import simulate_scene


T = TypeVar("T")
STATUS_CODE = {"reject": 0, "negative": 1, "positive": 2}
FEATURE_CODE = {"none": 0, "long_face": 1, "short_face": 2, "corner": 3, "ambiguous": 4}


class Reservoir(Generic[T]):
    def __init__(self, capacity: int, rng: np.random.Generator) -> None:
        self.capacity = capacity
        self.rng = rng
        self.items: list[T] = []
        self.seen = 0

    def add(self, item: T) -> None:
        self.seen += 1
        if len(self.items) < self.capacity:
            self.items.append(item)
            return
        replacement = int(self.rng.integers(0, self.seen))
        if replacement < self.capacity:
            self.items[replacement] = item


@dataclass(slots=True)
class PilotArtifacts:
    summary: dict[str, object]
    positive_samples: list[SimulationResult]
    negative_samples: list[SimulationResult]
    judgment_samples: list[tuple[SimulationResult, JudgmentPair]]


def _histogram(values: np.ndarray, bins: np.ndarray) -> dict[str, object]:
    counts, edges = np.histogram(values, bins=bins)
    return {"edges": edges.tolist(), "counts": counts.astype(int).tolist()}


def _histogram2d(
    x: np.ndarray,
    y: np.ndarray,
    x_edges: np.ndarray,
    y_edges: np.ndarray,
) -> dict[str, object]:
    counts, x_bins, y_bins = np.histogram2d(x, y, bins=(x_edges, y_edges))
    return {
        "x_edges": x_bins.tolist(),
        "y_edges": y_bins.tolist(),
        "counts": counts.astype(int).tolist(),
    }


def _describe(values: np.ndarray) -> dict[str, float | int | None]:
    if values.size == 0:
        return {"count": 0, "mean": None, "std": None, "min": None, "q25": None, "median": None, "q75": None, "max": None}
    quantiles = np.quantile(values, [0.0, 0.25, 0.5, 0.75, 1.0])
    return {
        "count": int(values.size),
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "min": float(quantiles[0]),
        "q25": float(quantiles[1]),
        "median": float(quantiles[2]),
        "q75": float(quantiles[3]),
        "max": float(quantiles[4]),
    }


def _correlation(values: np.ndarray, labels: np.ndarray) -> float | None:
    if values.size < 2 or np.std(values) == 0.0 or np.std(labels) == 0.0:
        return None
    return float(np.corrcoef(values, labels)[0, 1])


def _summary_from_arrays(
    config: PhysicsConfig,
    num_proposals: int,
    scene_seed: int,
    judgment_seed_root: int,
    elapsed_s: float,
    arrays: dict[str, np.ndarray],
    status_counts: Counter[str],
    rejection_counts: Counter[str],
    judgment_counts: Counter[str],
) -> dict[str, object]:
    status = arrays["status_code"]
    positive = status == STATUS_CODE["positive"]
    negative = status == STATUS_CODE["negative"]
    accepted = positive | negative
    collision_mask = arrays["collision_mask"]
    impact_mask = arrays["impact_mask"]
    judgment_mask = arrays["judgment_generated"]

    speed_bins = np.linspace(config.speed_min_cells_per_s, config.speed_max_cells_per_s, 36)
    velocity_bins = np.linspace(0.0, 2.0 * math.pi, 37)
    axis_bins = np.linspace(0.0, math.pi, 37)
    impact_bins = np.linspace(0.0, 90.0, 19)
    delta_bins = np.linspace(config.violation_delta_min_deg, config.violation_delta_max_deg, 18)
    center_x_edges = np.linspace(-config.center_half_width_px, config.center_half_width_px, 25)
    center_y_edges = np.linspace(-config.center_half_height_px, config.center_half_height_px, 21)
    barrier_x_edges = np.linspace(-config.roi_half_width_px, config.roi_half_width_px, 25)
    barrier_y_edges = np.linspace(-config.roi_half_height_px, config.roi_half_height_px, 21)

    accepted_labels = positive[accepted].astype(np.float64)
    accepted_speed = arrays["speed_cells_per_s"][accepted]
    accepted_velocity_angle = arrays["velocity_angle_rad"][accepted]
    accepted_barrier_angle = arrays["barrier_axis_angle_rad"][accepted]

    return {
        "dataset_version": "v1-pilot",
        "simulator_version": __version__,
        "config_hash": config.config_hash(),
        "config": config.to_dict(),
        "scene_seed": scene_seed,
        "judgment_seed_root": judgment_seed_root,
        "num_proposals": num_proposals,
        "elapsed_seconds": elapsed_s,
        "proposals_per_second": num_proposals / elapsed_s,
        "status_counts": dict(status_counts),
        "status_rates": {
            key: status_counts.get(key, 0) / num_proposals
            for key in ("positive", "negative", "reject")
        },
        "rejection_reason_counts": dict(rejection_counts.most_common()),
        "judgment": {
            "counts": dict(judgment_counts),
            "generation_rate_per_positive": (
                judgment_counts.get("generated", 0) / status_counts["positive"]
                if status_counts["positive"]
                else None
            ),
            "delta_deg": _describe(arrays["judgment_delta_deg"][judgment_mask]),
            "delta_histogram": _histogram(arrays["judgment_delta_deg"][judgment_mask], delta_bins),
            "sign_counts": {
                "negative": int(np.sum(arrays["judgment_sign"][judgment_mask] == -1)),
                "positive": int(np.sum(arrays["judgment_sign"][judgment_mask] == 1)),
            },
            "attempts": _describe(arrays["judgment_attempts"][positive].astype(np.float64)),
        },
        "distributions": {
            "speed_cells_per_s": {
                "proposal": _describe(arrays["speed_cells_per_s"]),
                "positive": _describe(arrays["speed_cells_per_s"][positive]),
                "negative": _describe(arrays["speed_cells_per_s"][negative]),
                "proposal_histogram": _histogram(arrays["speed_cells_per_s"], speed_bins),
                "positive_histogram": _histogram(arrays["speed_cells_per_s"][positive], speed_bins),
                "negative_histogram": _histogram(arrays["speed_cells_per_s"][negative], speed_bins),
            },
            "velocity_angle_rad": {
                "proposal_histogram": _histogram(arrays["velocity_angle_rad"], velocity_bins),
                "positive_histogram": _histogram(arrays["velocity_angle_rad"][positive], velocity_bins),
                "negative_histogram": _histogram(arrays["velocity_angle_rad"][negative], velocity_bins),
            },
            "barrier_axis_angle_rad": {
                "proposal_histogram": _histogram(arrays["barrier_axis_angle_rad"], axis_bins),
                "positive_histogram": _histogram(arrays["barrier_axis_angle_rad"][positive], axis_bins),
                "negative_histogram": _histogram(arrays["barrier_axis_angle_rad"][negative], axis_bins),
            },
            "impact_angle_deg": {
                "positive": _describe(arrays["impact_angle_deg"][positive & impact_mask]),
                "positive_histogram": _histogram(
                    arrays["impact_angle_deg"][positive & impact_mask], impact_bins
                ),
            },
            "post_velocity_angle_rad": {
                "positive_histogram": _histogram(
                    arrays["post_velocity_angle_rad"][positive], velocity_bins
                )
            },
        },
        "spatial_histograms": {
            "p_context_proposal": _histogram2d(
                arrays["p_context_xy"][:, 0], arrays["p_context_xy"][:, 1], center_x_edges, center_y_edges
            ),
            "p_context_positive": _histogram2d(
                arrays["p_context_xy"][positive, 0], arrays["p_context_xy"][positive, 1], center_x_edges, center_y_edges
            ),
            "p_context_negative": _histogram2d(
                arrays["p_context_xy"][negative, 0], arrays["p_context_xy"][negative, 1], center_x_edges, center_y_edges
            ),
            "barrier_center_proposal": _histogram2d(
                arrays["barrier_center_xy"][:, 0], arrays["barrier_center_xy"][:, 1], barrier_x_edges, barrier_y_edges
            ),
            "collision_point": _histogram2d(
                arrays["collision_point_xy"][collision_mask, 0],
                arrays["collision_point_xy"][collision_mask, 1],
                center_x_edges,
                center_y_edges,
            ),
        },
        "accepted_label_correlations": {
            "speed_cells_per_s": _correlation(accepted_speed, accepted_labels),
            "sin_velocity_angle": _correlation(np.sin(accepted_velocity_angle), accepted_labels),
            "cos_velocity_angle": _correlation(np.cos(accepted_velocity_angle), accepted_labels),
            "sin_2_barrier_angle": _correlation(np.sin(2.0 * accepted_barrier_angle), accepted_labels),
            "cos_2_barrier_angle": _correlation(np.cos(2.0 * accepted_barrier_angle), accepted_labels),
            "ball_barrier_distance_px": _correlation(
                np.linalg.norm(
                    arrays["barrier_center_xy"][accepted] - arrays["p_context_xy"][accepted], axis=1
                ),
                accepted_labels,
            ),
        },
        "diagnostic_counts": {
            "raw_collision_exists": int(np.sum(arrays["raw_collision_exists"])),
            "collision_point_available": int(np.sum(collision_mask)),
            "impact_angle_available": int(np.sum(impact_mask)),
        },
    }


def run_pilot(
    *,
    config: PhysicsConfig,
    num_proposals: int,
    scene_seed: int,
    judgment_seed_root: int,
    output_dir: Path,
    positive_sample_count: int = 24,
    negative_sample_count: int = 24,
    judgment_sample_count: int = 8,
    progress_every: int = 10_000,
) -> PilotArtifacts:
    if num_proposals <= 0:
        raise ValueError("num_proposals must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    run_manifest = {
        "dataset_version": "v1-pilot",
        "simulator_version": __version__,
        "config_hash": config.config_hash(),
        "scene_seed": scene_seed,
        "judgment_seed_root": judgment_seed_root,
        "num_proposals": num_proposals,
        "config": config.to_dict(),
    }
    write_json(output_dir / "config.json", run_manifest)

    arrays: dict[str, np.ndarray] = {
        "status_code": np.zeros(num_proposals, dtype=np.uint8),
        "speed_cells_per_s": np.empty(num_proposals, dtype=np.float64),
        "velocity_angle_rad": np.empty(num_proposals, dtype=np.float64),
        "barrier_axis_angle_rad": np.empty(num_proposals, dtype=np.float64),
        "p_context_xy": np.empty((num_proposals, 2), dtype=np.float64),
        "barrier_center_xy": np.empty((num_proposals, 2), dtype=np.float64),
        "raw_collision_exists": np.zeros(num_proposals, dtype=np.bool_),
        "collision_feature_code": np.zeros(num_proposals, dtype=np.uint8),
        "collision_mask": np.zeros(num_proposals, dtype=np.bool_),
        "collision_point_xy": np.zeros((num_proposals, 2), dtype=np.float64),
        "impact_mask": np.zeros(num_proposals, dtype=np.bool_),
        "impact_angle_deg": np.zeros(num_proposals, dtype=np.float64),
        "post_velocity_angle_rad": np.zeros(num_proposals, dtype=np.float64),
        "judgment_generated": np.zeros(num_proposals, dtype=np.bool_),
        "judgment_delta_deg": np.zeros(num_proposals, dtype=np.float64),
        "judgment_sign": np.zeros(num_proposals, dtype=np.int8),
        "judgment_attempts": np.zeros(num_proposals, dtype=np.uint16),
    }
    status_counts: Counter[str] = Counter()
    rejection_counts: Counter[str] = Counter()
    judgment_counts: Counter[str] = Counter()
    sampling_sequence = np.random.SeedSequence([scene_seed, 0xD38B_51A7])
    positive_reservoir = Reservoir[SimulationResult](
        positive_sample_count, np.random.Generator(np.random.PCG64(sampling_sequence.spawn(1)[0]))
    )
    negative_reservoir = Reservoir[SimulationResult](
        negative_sample_count, np.random.Generator(np.random.PCG64(sampling_sequence.spawn(1)[0]))
    )
    judgment_reservoir = Reservoir[tuple[SimulationResult, JudgmentPair]](
        judgment_sample_count, np.random.Generator(np.random.PCG64(sampling_sequence.spawn(1)[0]))
    )

    started = time.perf_counter()
    accepted_path = output_dir / "accepted_scenes.jsonl.gz"
    with gzip.open(accepted_path, "wt", encoding="utf-8", compresslevel=6) as accepted_file:
        for index in range(num_proposals):
            scene = sample_scene(config, scene_seed, index)
            result = simulate_scene(scene, config)
            status_counts[result.contact.status] += 1
            rejection_counts.update(result.acceptance.rejection_reasons)

            arrays["status_code"][index] = STATUS_CODE[result.contact.status]
            arrays["speed_cells_per_s"][index] = scene.speed_cells_per_s
            arrays["velocity_angle_rad"][index] = scene.velocity_angle_rad
            arrays["barrier_axis_angle_rad"][index] = scene.barrier_axis_angle_rad
            arrays["p_context_xy"][index] = scene.p_context_xy
            arrays["barrier_center_xy"][index] = scene.barrier_center_xy
            arrays["raw_collision_exists"][index] = result.contact.true_barrier_collision_exists
            arrays["collision_feature_code"][index] = FEATURE_CODE[
                result.relative_geometry.actual_first_contact_feature
            ]
            event = result.collision_event
            if event.ball_center_at_contact_xy is not None:
                arrays["collision_mask"][index] = True
                arrays["collision_point_xy"][index] = event.ball_center_at_contact_xy
            if event.impact_angle_deg is not None:
                arrays["impact_mask"][index] = True
                arrays["impact_angle_deg"][index] = event.impact_angle_deg
            if event.post_collision_angle_rad is not None:
                arrays["post_velocity_angle_rad"][index] = event.post_collision_angle_rad

            pair: JudgmentPair | None = None
            if result.contact.status == "positive":
                positive_reservoir.add(result)
                judgment_seed = (judgment_seed_root + index) % (1 << 64)
                pair = generate_judgment_pair(result, judgment_seed, config)
                arrays["judgment_attempts"][index] = pair.metadata.violation_sampling_attempt_count
                if pair.generated:
                    judgment_counts["generated"] += 1
                    arrays["judgment_generated"][index] = True
                    arrays["judgment_delta_deg"][index] = pair.metadata.delta_deg
                    arrays["judgment_sign"][index] = pair.metadata.sign
                    judgment_reservoir.add((result, pair))
                else:
                    judgment_counts["failed"] += 1
            elif result.contact.status == "negative":
                negative_reservoir.add(result)

            if result.acceptance.accepted_for_contact:
                accepted_file.write(
                    dumps_json(
                        {
                            "dataset_version": "v1-pilot",
                            "simulator_version": __version__,
                            "config_hash": config.config_hash(),
                            "simulation": result,
                            "judgment_pair": pair,
                        }
                    )
                    + "\n"
                )

            if progress_every and (index + 1) % progress_every == 0:
                elapsed = time.perf_counter() - started
                print(
                    f"pilot {index + 1:,}/{num_proposals:,} "
                    f"({(index + 1) / elapsed:,.0f} proposals/s) "
                    f"positive={status_counts['positive']:,} negative={status_counts['negative']:,}",
                    flush=True,
                )

    elapsed = time.perf_counter() - started
    np.savez_compressed(output_dir / "pilot_arrays.npz", **arrays)
    summary = _summary_from_arrays(
        config,
        num_proposals,
        scene_seed,
        judgment_seed_root,
        elapsed,
        arrays,
        status_counts,
        rejection_counts,
        judgment_counts,
    )
    write_json(output_dir / "summary.json", summary)
    sample_manifest = {
        "positive": [result.scene.latent_scene_id for result in positive_reservoir.items],
        "negative": [result.scene.latent_scene_id for result in negative_reservoir.items],
        "judgment_pairs": [pair.metadata.judgment_pair_id for _, pair in judgment_reservoir.items],
    }
    write_json(output_dir / "sample_manifest.json", sample_manifest)
    return PilotArtifacts(
        summary=to_builtin(summary),
        positive_samples=positive_reservoir.items,
        negative_samples=negative_reservoir.items,
        judgment_samples=judgment_reservoir.items,
    )
