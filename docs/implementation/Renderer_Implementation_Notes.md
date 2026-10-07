# Renderer v1 Implementation Notes

This note records renderer engineering choices that instantiate
`05_Benchmark_and_Experiment_Design.md`. The knowledge base remains normative.

## Core renderer boundary

`physics_bench.renderer` accepts only:

- a `Trajectory`;
- an explicit `AppearanceSpec`;
- frame/encoding configuration and the static asset bank.

It never receives Contact/Judgment labels and therefore cannot select appearance from a label.
Production frames contain no text, label, phase indicator, ROI box, grid, contact marker, or
trajectory trail. The old `debug_renderer.py` remains separate for human diagnostics.

`AppearanceSpec` serializes every required style ID and continuous jitter value. Canonical fixes
all IDs and gains. Diverse independently samples a family-specific discrete preset plus only the
narrow jitter ranges authorized in section 41. Identical `(latent_scene_id, render_seed, family)`
inputs replay exactly.

After applying the sampled component jitter analytically, ball selection requires either RGB
distance ≥ 55 or luminance difference ≥ 42 from the selected surface base. If a candidate fails,
the renderer takes the next item in a seed-determined random palette permutation; physics is never
changed.

## Rasterization and encoding

- Static background layers are composed once per video and reused for all 24 frames.
- Barrier center/orientation are derived from trajectory vertices/tangent, not from task labels.
- Positive world-axis angles are passed as positive visual rotations to Pillow; the world-to-image
  y-axis inversion is already embodied by Pillow's counter-clockwise rotation convention.
- Ball position is the only per-frame visual change besides the corresponding latent trajectory.
- Default rasterization is 2× supersampling followed by Lanczos downsampling to 448×448.
- Output is 24 frames at 24 fps, H.264/libx264, RGB input, yuv420p output, with fast-start metadata.
- Motion blur, directional lighting, and cast shadows are rejected by renderer validation.

## First Contact dataset writer

`physics_bench.render_dataset` performs a deterministic two-pass construction:

1. classify all proposal indices;
2. keep all accepted positives (or an explicit smoke-test cap);
3. sample accepted negative indices without replacement using `selection_seed` until their count
   exactly equals the selected positive count;
4. replay only selected scenes and render them.

Thus the production default is exactly positive:negative = 1:1. `--max-per-class` is a test-only
cap and samples both classes down to the requested count.

Family assignment is balanced separately inside each Contact class, up to an unavoidable remainder
when the class count is not divisible by the number of requested families. Style jitter is sampled
from render seeds that depend only on proposal index, family, and `render_seed_root`.

## Split and index scope

The first writer deliberately does not assign train/val/test. Contact manifest rows include
`split: null`, so a later latent-scene-level split can populate the field without rerendering.

This implementation writes replayable JSONL index mirrors now. Canonical typed Parquet tables and
the complete multi-task `TaskManifestBuilder` remain a later dataset-packaging step; rendering and
50:50 Contact selection do not depend on that storage choice.
