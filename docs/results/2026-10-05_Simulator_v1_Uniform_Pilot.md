# Simulator v1 independent-uniform pilot

## Run identity

```text
date: 2026-10-05
num_proposals: 100,000
scene_seed: 20,261,005
judgment_seed_root: 91,735,113
proposal_mode: independent_uniform
output: outputs/pilot/v1_uniform_100k
```

The run used the unmodified v1 physics hyperparameters from knowledge-base document 05. No
acceptance-rate or marginal-distribution optimization was applied.

## Throughput

```text
latent simulation + Judgment generation + artifact writing: 45.80 s
throughput: 2,183 proposals/s
```

The separate debug-video pass generated 64 H.264 MP4 files.

## Contact classification

| Status | Count | Proposal rate |
|---|---:|---:|
| Positive | 1,871 | 1.871% |
| Strict-safe negative | 13,332 | 13.332% |
| Reject | 84,797 | 84.797% |
| Accepted total | 15,203 | 15.203% |

Rejection reasons are multi-label and therefore do not sum to the rejected count.

| Rejection reason | Count |
|---|---:|
| `ball_end_outside_physics_roi` | 50,107 |
| `ball_start_outside_physics_roi` | 26,133 |
| `context_collision` | 19,383 |
| `collision_too_early` | 15,955 |
| `negative_ray_enters_safety_region` | 8,864 |
| `collision_too_late` | 6,281 |
| `ray_hit_beyond_video` | 4,104 |
| `corner_contact` | 3,387 |
| `endpoint_margin_violation` | 3,037 |
| `short_face_contact` | 1,594 |
| `impact_angle_too_small` | 237 |
| `ball_collision_center_outside_physics_roi` | 162 |

## Distribution checks

The proposal speed mean was `6.74969 cells/s`, essentially the expected midpoint `6.75` of the
uniform `[5.0, 8.5)` prior.

One-sample Kolmogorov–Smirnov checks after mapping every proposal variable to $U[0,1]$:

| Proposal variable | KS D | p-value |
|---|---:|---:|
| speed | 0.00228 | 0.676 |
| velocity angle | 0.00228 | 0.673 |
| barrier axis angle | 0.00236 | 0.635 |
| context center x | 0.00199 | 0.825 |
| context center y | 0.00247 | 0.575 |
| conditional barrier center x | 0.00148 | 0.980 |
| conditional barrier center y | 0.00238 | 0.623 |

These checks show no evidence against the specified uniform proposal prior at this sample size.

```text
positive speed mean: 6.68116 cells/s
negative speed mean: 6.39998 cells/s
positive impact angle mean: 59.93 degrees
positive impact angle median: 62.96 degrees
positive impact range: 10.19–89.99 degrees
```

Point-biserial / encoded correlations within the accepted Contact pool:

```text
speed vs positive label:                    +0.0948
ball–barrier center distance vs label:      -0.4042
sin(theta_v) / cos(theta_v) vs label:       approximately +0.0073
sin(2 phi) vs label:                        -0.0081
cos(2 phi) vs label:                        -0.0406
```

These are observations for the first pilot, not optimization decisions. In particular, the strong
distance-label relation and the positive/negative speed shift should be reviewed before building a
balanced final Contact dataset.

## Judgment generation

All 1,871 dynamics-eligible positives produced a valid matched invalid variant within the maximum
128 attempts.

```text
generation rate: 100%
mean attempts: 1.339
median attempts: 1
maximum attempts: 62
mean accepted delta: 42.94 degrees
delta range: 5.12–89.88 degrees
negative sign: 965
positive sign: 906
```

As expected from geometry-conditioned acceptance, accepted severity is not perfectly uniform;
the exact histogram is stored in `summary.json`.

## Artifacts

```text
outputs/pilot/v1_uniform_100k/summary.json
outputs/pilot/v1_uniform_100k/pilot_arrays.npz
outputs/pilot/v1_uniform_100k/accepted_scenes.jsonl.gz
outputs/pilot/v1_uniform_100k/sample_manifest.json
outputs/pilot/v1_uniform_100k/debug_videos/
```

The debug set contains 24 positive, 24 negative and 8 valid/invalid Judgment pairs. Debug videos
show the cell grid, visual table, Physics ROI, trajectory trail and textual metadata; they are not
production training renders.
