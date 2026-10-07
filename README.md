# Physics Understanding in Video Models

This repository contains the benchmark and mechanistic-interpretability project documented in
[`docs/knowledge base`](docs/knowledge%20base). The current code implements the v1 analytic
single-disk / finite-barrier simulator, Reflection Judgment pair generator, latent pilot
statistics, deterministic visual asset bank, and production/debug MP4 renderers.

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

## Render a balanced Contact dataset

The production renderer consumes only a latent trajectory and an explicit replayable
`AppearanceSpec`. The dataset wrapper keeps every selected positive and randomly downsamples
accepted negatives to the same count. No train/val/test split is assigned yet; the nullable split
field is retained in the manifest for the later latent-scene-level split step.

```bash
.venv/bin/physics-bench render-contact \
  --num-proposals 100000 \
  --scene-seed 20261005 \
  --selection-seed 38410771 \
  --render-seed 71902633 \
  --families canonical_neutral billiards air_hockey tabletop \
  --asset-bank assets/renderer/v1 \
  --output outputs/renderer_contact_v1
```

For a small visual smoke test, add `--max-per-class 4`. Output contains H.264 MP4 files,
`index/appearances.jsonl`, `index/renders.jsonl`, and `manifests/contact.jsonl`.

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
src/physics_bench/renderer.py         production AppearanceSpec sampler and RGB/MP4 renderer
src/physics_bench/render_dataset.py   balanced Contact selection and dataset writer
src/physics_bench/cli.py              command-line interface
```

Implementation choices made where the specification intentionally left engineering freedom are
recorded in
[`docs/implementation/Simulator_Implementation_Notes.md`](docs/implementation/Simulator_Implementation_Notes.md).
