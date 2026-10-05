"""Command-line entry points for tests, pilots, and debug videos."""

from __future__ import annotations

import argparse
from pathlib import Path

from .assets import AssetBankConfig, generate_asset_bank
from .config import PhysicsConfig
from .debug_renderer import render_debug_video
from .pilot import run_pilot
from .serialization import write_json


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="physics-bench")
    subparsers = parser.add_subparsers(dest="command", required=True)
    pilot = subparsers.add_parser("pilot", help="run the pure-latent pilot and optional debug rendering")
    pilot.add_argument("--num-proposals", type=int, default=100_000)
    pilot.add_argument("--scene-seed", type=int, default=20_261_005)
    pilot.add_argument("--judgment-seed", type=int, default=91_735_113)
    pilot.add_argument("--output", type=Path, default=Path("outputs/pilot/v1_uniform_100k"))
    pilot.add_argument("--render-positive", type=int, default=24)
    pilot.add_argument("--render-negative", type=int, default=24)
    pilot.add_argument("--render-judgment-pairs", type=int, default=8)
    pilot.add_argument("--no-render", action="store_true")
    pilot.add_argument("--progress-every", type=int, default=10_000)
    assets = subparsers.add_parser("assets", help="generate the deterministic renderer v1 asset bank")
    assets.add_argument("--seed", type=int, default=20_261_006)
    assets.add_argument("--output", type=Path, default=Path("assets/renderer/v1"))
    return parser


def _run_pilot(args: argparse.Namespace) -> int:
    config = PhysicsConfig()
    artifacts = run_pilot(
        config=config,
        num_proposals=args.num_proposals,
        scene_seed=args.scene_seed,
        judgment_seed_root=args.judgment_seed,
        output_dir=args.output,
        positive_sample_count=args.render_positive,
        negative_sample_count=args.render_negative,
        judgment_sample_count=args.render_judgment_pairs,
        progress_every=args.progress_every,
    )
    if not args.no_render:
        video_dir = args.output / "debug_videos"
        rendered: list[dict[str, object]] = []
        for label, samples in (
            ("positive", artifacts.positive_samples),
            ("negative", artifacts.negative_samples),
        ):
            for index, result in enumerate(samples):
                path = video_dir / label / f"{index:03d}_{result.scene.latent_scene_id}.mp4"
                render_debug_video(result, path, config)
                rendered.append(
                    {"kind": label, "latent_scene_id": result.scene.latent_scene_id, "path": str(path)}
                )
        for index, (base, pair) in enumerate(artifacts.judgment_samples):
            if pair.valid is None or pair.invalid is None:
                continue
            pair_dir = video_dir / "judgment" / f"{index:03d}_{pair.metadata.judgment_pair_id.replace(':', '_')}"
            valid_path = pair_dir / "valid.mp4"
            invalid_path = pair_dir / "invalid.mp4"
            render_debug_video(
                base,
                valid_path,
                config,
                trajectory=pair.valid.trajectory,
                judgment_labels=pair.valid.labels,
            )
            render_debug_video(
                base,
                invalid_path,
                config,
                trajectory=pair.invalid.trajectory,
                judgment_labels=pair.invalid.labels,
            )
            rendered.extend(
                [
                    {"kind": "judgment_valid", "judgment_pair_id": pair.metadata.judgment_pair_id, "path": str(valid_path)},
                    {"kind": "judgment_invalid", "judgment_pair_id": pair.metadata.judgment_pair_id, "path": str(invalid_path)},
                ]
            )
        write_json(args.output / "debug_videos" / "manifest.json", rendered)
    print(f"pilot complete: {args.output}")
    print(artifacts.summary["status_rates"])
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "pilot":
        return _run_pilot(args)
    if args.command == "assets":
        manifest = generate_asset_bank(args.output, AssetBankConfig(seed=args.seed))
        print(f"asset bank complete: {args.output}")
        print(f"generated {len(manifest['assets'])} PNG assets")
        return 0
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
