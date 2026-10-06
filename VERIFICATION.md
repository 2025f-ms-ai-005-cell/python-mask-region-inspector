# Verification — October 6, 2026

- Bundled Python on Windows: `python -B -m unittest -v`: 11 tests passed, exit 0.
- `python -B regions.py sample.json --min-area 2 --out demo`: executed successfully; three regions, one filtered pixel.
- Outputs: JSON measurements and computed 1600 × 1000 SVG, from original synthetic mask.
- Negative tests deliberately print parser errors for invalid JSON and existing output directory; both pass by verifying rejection.
- No real-camera, dataset accuracy, learned segmentation or robot execution evaluated.
