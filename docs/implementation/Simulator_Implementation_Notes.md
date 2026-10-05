# Simulator implementation notes

This file records narrow engineering choices that were not scientific design decisions in the
knowledge base. The normative benchmark specification remains
`docs/knowledge base/05_Benchmark_and_Experiment_Design.md`.

## Deterministic random streams

The proposal RNG follows the frozen `PCG64 + SeedSequence` construction. Within one proposal, the
draw order is fixed as:

1. speed;
2. velocity angle;
3. barrier axis angle;
4. context-boundary ball-center x and y;
5. orientation-conditioned barrier-center x and y.

Judgment uses a separate PCG64 stream with entropy
`[judgment_seed, scene_seed, proposal_index, 100]`; `100` is the reserved Judgment stream code.
Changing either sequence is dataset-versioning relevant.

## Collision geometry

Disk-vs-rectangle contact is solved as point-vs-rounded-rectangle contact in barrier-local
coordinates. Long and short offset faces and all four radius arcs are solved analytically; the
minimum nonnegative path distance is the first contact. Feature-join and tangent cases inside the
configured epsilon are `ambiguous` and rejected.

`candidate_collision_time_s` is the absolute clip timestamp, not TTC. TTC remains the distinct
`ttc_from_context_s` label.

Corner contacts retain time, center, physical corner and face ID for diagnostics but deliberately
have no normal or post-collision response, matching the v1 rule that corner reflection is not a
legal event. Rejected short-face contacts use their well-defined face normal for diagnostic
trajectory construction.

For a trajectory leaving a known active face, the no-second-collision check first uses convexity:
a ray moving into the exterior supporting half-plane of a convex rectangle cannot hit it again.
The general ray check remains as a fallback when no initial face normal is available. This avoids
artificial re-contact from an epsilon-scale restart near a tangent face.

## Judgment pairs

Both `+delta` and `-delta` are fully checked for every sampled severity. If both pass, the same
Judgment RNG chooses one uniformly. Alternate-barrier feasibility additionally verifies that the
unchanged incoming velocity approaches the rotated active face and that exact reflection from it
matches the proposed bad direction.

## Pilot storage

Canonical JSON records use `null` and never NaN/Inf. The compact NPZ analysis artifact stores
optional numeric arrays as a value array plus an explicit boolean mask; zero-filled masked values
must not be interpreted as observations.

## Debug renderer boundary

The test renderer is intentionally not a production dataset renderer. At the user's request it
draws the cell grid, visual-table outline, Physics ROI, past trajectory and textual labels. These
are debugging overlays and must not be used for model experiments. Valid and invalid Judgment
branches use the same object and barrier appearance; only trajectory and debug text differ.

Rendering uses 2x supersampling followed by Lanczos downsampling and writes 448x448, 24 fps,
24-frame H.264 MP4 files with no motion blur.
