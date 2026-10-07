# Renderer v1 Procedural Asset Notes

This note records the small engineering choices required to instantiate the renderer asset-bank
specification in `05_Benchmark_and_Experiment_Design.md`. The knowledge base remains normative.

## Implemented bank

- Canonical: one fixed surface, outside background, rail, ball, and barrier.
- Each Diverse family: four surfaces, two outside backgrounds, three rails, five balls, and three
  barriers.
- Air Hockey additionally has three symmetric marking overlays.
- `background_previews/` contains four ready-to-inspect 448×448 composites per Diverse family and
  one Canonical composite. These previews do not collapse the independently selectable source
  layers used by the future renderer.
- All texture noise is deterministic and keyed by the root seed plus semantic asset ID. Felt,
  plastic, metal, and outside-background noise remains isotropic; Canonical/Tabletop use a weak,
  non-periodic long-axis wood grain to strengthen horizontal-table semantics.
- Ball and barrier sprites are RGBA; backgrounds and surfaces are RGB. Geometry is generated at
  4× resolution and antialiased down to final size where edges are involved.
- Every 140×28 barrier is divided into a 105 px raised central body and two 17.5 px flatter end
  plates. Each end plate has two 11 px cross-recess screw heads; the complete sprite remains exactly
  180° symmetric and inside the simulator footprint.
- Billiards uses a 7 px dark wood outer rail, a 5 px green felt cushion, a visible cushion/surface
  seam, six circular pockets, and 13 px rounded outer corners.
- Air Hockey keeps the 420×308 playing surface but adds an 8 px external rail, giving a 436×324
  outer footprint. Its 58 px corner radius, pale 14 px-spaced air holes, and standard symmetric
  zone/goal/face-off markings are all outside the physics definition.
- Canonical/Tabletop remove the contrasting picture-frame rail, use a 6 px corner radius, and rely
  on surface grain plus the table/outside contrast to convey the tabletop boundary.

## Choices left open by the document

1. Billiards pocket diameter was not numerically fixed. The bank uses 14 px circular pockets; their
   centers keep the pockets on the non-physical edge region.
2. The Air-Hockey reference established standard marking semantics but not exact geometry. The
   implementation uses fully symmetric center, zone, goal, face-off-circle, crosshair, dot, and
   optional goal-arc/inset-rink elements, all in the prior low-contrast blue-gray.
3. The requested wood grain creates an intentional weak long-axis appearance cue. Its luminance
   amplitude is 3.0–3.2%, non-periodic, and independently seeded; this should be included in later
   appearance/physics independence audits.
4. Texture amplitudes otherwise remain conservative: felt 1.8%, outside 0.8%, Air-Hockey surface
   0.6%, and barrier roughness 0.9%.

The generated `manifest.json` records dimensions, color, seed, path, and SHA-256 for every PNG.
