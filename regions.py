"""Deterministic connected-region analysis for small binary masks."""
import argparse
import html
import json
from pathlib import Path


def validate(mask):
    if not isinstance(mask, list) or not mask or not isinstance(mask[0], list) or not mask[0]:
        raise ValueError('mask must be a nonempty rectangular array')
    width = len(mask[0])
    if width * len(mask) > 65536:
        raise ValueError('mask exceeds the 65,536 pixel learning-tool limit')
    for row in mask:
        if not isinstance(row, list) or len(row) != width:
            raise ValueError('mask rows must have equal lengths')
        if any(type(v) is not int or v not in (0, 1) for v in row):
            raise ValueError('pixels must be integers 0 or 1')
    return width, len(mask)


def analyze(mask, connectivity=4, min_area=1):
    width, height = validate(mask)
    if connectivity not in (4, 8) or type(min_area) is not int or min_area < 1:
        raise ValueError('connectivity must be 4 or 8 and min_area a positive integer')
    neighbors = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if connectivity == 8:
        neighbors += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    seen, regions = set(), []
    labels = [[0] * width for _ in range(height)]
    removed = 0
    for y in range(height):
        for x in range(width):
            if not mask[y][x] or (x, y) in seen:
                continue
            stack, pixels = [(x, y)], []
            seen.add((x, y))
            while stack:
                px, py = stack.pop()
                pixels.append((px, py))
                for dx, dy in neighbors:
                    nx, ny = px + dx, py + dy
                    if 0 <= nx < width and 0 <= ny < height and mask[ny][nx] and (nx, ny) not in seen:
                        seen.add((nx, ny))
                        stack.append((nx, ny))
            if len(pixels) < min_area:
                removed += len(pixels)
                continue
            rid = len(regions) + 1
            xs, ys = zip(*pixels)
            for px, py in pixels:
                labels[py][px] = rid
            box = [min(xs), min(ys), max(xs), max(ys)]
            box_area = (box[2] - box[0] + 1) * (box[3] - box[1] + 1)
            perimeter = sum(1 for px, py in pixels for dx, dy in neighbors[:4]
                            if not (0 <= px + dx < width and 0 <= py + dy < height)
                            or not mask[py + dy][px + dx])
            regions.append(dict(id=rid, area=len(pixels), bbox=box,
                                centroid=[sum(xs) / len(xs), sum(ys) / len(ys)],
                                fill_ratio=len(pixels) / box_area, perimeter_edges=perimeter))
    return dict(width=width, height=height, connectivity=connectivity, min_area=min_area,
                removed_pixels=removed, regions=regions, labels=labels)


def visual(result):
    """Vector output: actual supplied mask labels, not a camera screenshot."""
    w, h = result['width'], result['height']
    size = min(50, 650 / max(w, h))
    ox, oy = 70, 190
    colors = ['#38bdf8', '#a78bfa', '#34d399', '#fb7185', '#fbbf24']
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000">',
             '<rect width="1600" height="1000" fill="#0b1224"/>',
             '<g font-family="Arial,sans-serif" fill="#e2e8f0">',
             '<text x="70" y="80" font-size="44" font-weight="bold">MASK REGION INSPECTOR</text>',
             '<text x="70" y="125" font-size="22">Computed binary-mask visualization • Synthetic fixture • Not robot validation</text>']
    for y, row in enumerate(result['labels']):
        for x, rid in enumerate(row):
            color = colors[(rid - 1) % len(colors)] if rid else '#1e293b'
            parts.append(f'<rect x="{ox+x*size}" y="{oy+y*size}" width="{size-1}" height="{size-1}" fill="{color}"/>')
    for r in result['regions']:
        x0, y0, x1, y1 = r['bbox']
        cx, cy = r['centroid']
        parts.append(f'<rect x="{ox+x0*size}" y="{oy+y0*size}" width="{(x1-x0+1)*size}" height="{(y1-y0+1)*size}" fill="none" stroke="white" stroke-width="2"/>')
        parts.append(f'<circle cx="{ox+(cx+.5)*size}" cy="{oy+(cy+.5)*size}" r="6" fill="white"/>')
    parts.append(f'<text x="820" y="215" font-size="28">{len(result["regions"])} retained regions</text>')
    parts.append(f'<text x="820" y="255" font-size="21">Connectivity: {result["connectivity"]} • Minimum area: {result["min_area"]}</text>')
    for i, r in enumerate(result['regions'][:12]):
        cy = 320 + i * 44
        text = f'#{r["id"]}   area {r["area"]} px   centroid ({r["centroid"][0]:.2f}, {r["centroid"][1]:.2f})'
        parts.append(f'<text x="820" y="{cy}" font-size="21">{html.escape(text)}</text>')
    parts.append('<text x="70" y="920" font-size="20">White outline = inclusive bounding box • White dot = pixel-center centroid</text></g></svg>')
    return ''.join(parts)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='JSON object with a mask array')
    parser.add_argument('--out', type=Path, required=True, help='new output directory; existing directories are refused')
    parser.add_argument('--connectivity', type=int, choices=[4, 8], default=4)
    parser.add_argument('--min-area', type=int, default=1)
    args = parser.parse_args(argv)
    try:
        if args.input.stat().st_size > 1000000:
            raise ValueError('input exceeds 1 MB limit')
        data = json.loads(args.input.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or 'mask' not in data:
            raise ValueError('input must contain mask')
        result = analyze(data['mask'], args.connectivity, args.min_area)
        args.out.mkdir(parents=True, exist_ok=False)
        (args.out / 'report.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        (args.out / 'regions.svg').write_text(visual(result), encoding='utf-8')
        print(f'{len(result["regions"])} regions; {result["removed_pixels"]} pixels filtered; output: {args.out}')
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
