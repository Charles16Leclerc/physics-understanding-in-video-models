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
- All texture noise is isotropic, deterministic, and keyed by the root seed plus semantic asset ID.
- Ball and barrier sprites are RGBA; backgrounds and surfaces are RGB. Geometry is generated at
  4× resolution and antialiased down to final size where edges are involved.

## Choices left open by the document

1. The Tabletop rail categories were named but had no exact RGB values. v1 candidates use neutral
   gray `[118,116,112]`, pale wood `[157,139,112]`, and muted metal `[119,126,130]`.
2. The document allows a 6–10 px rail. The first bank uses 8 px, leaving 6 px between the inner rail
   edge and the latent Physics ROI on every side.
3. Billiards pocket size was unspecified. Preview rails use 8 px radius circles clipped at the six
   conventional edge locations; they remain entirely outside the Physics ROI.
4. Air-Hockey marking geometry was qualitative. The three candidates progressively add a center
   line/circle, a symmetric inset rink outline, and symmetric goal arcs. They use low-alpha
   blue-gray lines and never depend on trajectory or labels.
5. Texture amplitudes are set below the documented maxima: felt 1.8%, tabletop 1.8%, outside 0.8%,
   Air-Hockey surface 0.6%, and barrier roughness 0.9%.

The generated `manifest.json` records dimensions, color, seed, path, and SHA-256 for every PNG.
