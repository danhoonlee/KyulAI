# ImperialAX Logo Export Set

This folder contains Illustrator-compatible exports generated from the cropped PNG logo assets.

## Folders

- `ai_compatible/`: `.ai` files that are PDF-compatible and openable in Adobe Illustrator.
- `pdf_compatible/`: matching PDF files for print/design handoff.
- `svg_embedded/`: SVG wrappers with the high-resolution PNG embedded.
- `png_4x/`: 4x upscaled PNG files rendered from the cropped source assets.

## Important Note

The original source provided here is a raster PNG, not a native vector logo file. These `.ai` files preserve the cropped artwork at high resolution, but they are not editable native vector paths. For production-grade signage, large-format printing, or final brand master files, the main logo should be manually rebuilt or traced as clean vector paths in Illustrator.

Recommended practical usage:

- Website/header/app usage: use `png_4x/` or `svg_embedded/`.
- Illustrator layout work: use `ai_compatible/`.
- Print/vendor handoff: send `pdf_compatible/` plus this note.
- Final master logo package: rebuild the core `IAX` mark and `ImperialAX` wordmark as true vector paths.
