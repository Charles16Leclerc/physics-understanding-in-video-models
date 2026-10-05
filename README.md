# Physics Understanding in Video Models

This repository contains the benchmark and mechanistic-interpretability project documented in
[`docs/knowledge base`](docs/knowledge%20base). The current code implements the v1 analytic
single-disk / finite-barrier simulator, Reflection Judgment pair generator, latent pilot
statistics, and a debug-only MP4 renderer.

## Setup

The core simulator depends only on NumPy. MP4 rendering uses Pillow and a bundled FFmpeg binary
from `imageio-ffmpeg`.

```bash
cd /mnt/khz/physics-understanding-in-video-models
UV_CACHE_DIR=/mnt/khz/.cache/uv uv sync --extra render
```

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The suite covers exact long-face, short-face, corner, tangent and no-contact geometry;
deterministic PCG64 sampling; proposal-prior statistics; positive/negative/reject acceptance;
right-continuous event frames; elastic reflection; Judgment-pair constraints; randomized scene
invariants; pilot artifacts; and real H.264 MP4 encoding.

## Generate the renderer v1 asset bank

The canonical and three Diverse-family visual assets are generated procedurally and can be
replayed exactly from their recorded seed:

```bash
.venv/bin/physics-bench assets --output assets/renderer/v1 --seed 20261006
```

The output contains separate surface, outside-background, rail, marking, ball, and barrier PNGs,
composed 448×448 background previews, a contact sheet, and a SHA-256 manifest.

## Run the v1 latent pilot

```bash
.venv/bin/physics-bench pilot \
  --num-proposals 100000 \
  --scene-seed 20261005 \
  --judgment-seed 91735113 \
  --output outputs/pilot/v1_uniform_100k
```

Use `--no-render` for statistics only. By default the command reservoir-samples and renders:

- 24 Contact-positive videos;
- 24 strict-safe Contact-negative videos;
- 8 matched Judgment pairs (16 videos).

Generated artifacts include:

```text
summary.json                 aggregate rates, histograms, correlations, rejection counts
pilot_arrays.npz             compact masked arrays for follow-up analysis
accepted_scenes.jsonl.gz     complete accepted records and Judgment metadata
sample_manifest.json         exact deterministic sample IDs
debug_videos/                annotated 448x448 H.264 MP4 files
```

`outputs/` is intentionally ignored by Git because pilot data and videos are reproducible from
the recorded config, code version and seeds.

## Package layout

```text
src/physics_bench/config.py           frozen v1 configuration and config hash
src/physics_bench/models.py           canonical schema records
src/physics_bench/sampler.py          deterministic independent-uniform proposals
src/physics_bench/geometry.py         exact disk-vs-finite-rectangle geometry
src/physics_bench/simulator.py        trajectories, events, acceptance, task labels
src/physics_bench/judgment.py         matched valid/invalid reflection pairs
src/physics_bench/pilot.py            large-pilot writer and distribution statistics
src/physics_bench/debug_renderer.py   non-production diagnostic MP4 renderer
src/physics_bench/assets.py           deterministic procedural renderer asset bank
src/physics_bench/cli.py              command-line interface
```

Implementation choices made where the specification intentionally left engineering freedom are
recorded in
[`docs/implementation/Simulator_Implementation_Notes.md`](docs/implementation/Simulator_Implementation_Notes.md).
