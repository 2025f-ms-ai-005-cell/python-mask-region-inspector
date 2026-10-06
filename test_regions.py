import json
from pathlib import Path
import tempfile
import unittest
from regions import analyze, main, visual


class RegionTests(unittest.TestCase):
    def test_diagonal(self):
        mask = [[1, 0], [0, 1]]
        self.assertEqual(len(analyze(mask, 4)['regions']), 2)
        self.assertEqual(len(analyze(mask, 8)['regions']), 1)

    def test_geometry(self):
        r = analyze([[1, 1], [1, 1]])['regions'][0]
        self.assertEqual((r['area'], r['bbox'], r['centroid'], r['perimeter_edges']),
                         (4, [0, 0, 1, 1], [.5, .5], 8))

    def test_filter(self):
        r = analyze([[1, 0, 1, 1]], min_area=2)
        self.assertEqual(r['removed_pixels'], 1)
        self.assertEqual(r['labels'], [[0, 0, 1, 1]])

    def test_empty_foreground(self):
        self.assertEqual(analyze([[0]])['regions'], [])

    def test_invalid(self):
        for mask in ([], [[]], [[1], [1, 0]], [[True]], [[2]], ['bad']):
            with self.subTest(mask=mask), self.assertRaises(ValueError):
                analyze(mask)

    def test_config(self):
        for c, a in ((3, 1), (4, 0), (4, True)):
            with self.assertRaises(ValueError):
                analyze([[1]], c, a)

    def test_hole(self):
        r = analyze([[1,1,1],[1,0,1],[1,1,1]])['regions'][0]
        self.assertEqual(r['area'], 8)
        self.assertEqual(r['perimeter_edges'], 16)
        self.assertAlmostEqual(r['fill_ratio'], 8 / 9)

    def test_size_limit(self):
        with self.assertRaises(ValueError):
            analyze([[0] * 257 for _ in range(257)])

    def test_cli_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            inp, out = Path(d) / 'input.json', Path(d) / 'out'
            inp.write_text(json.dumps({'mask': [[1, 1]]}), encoding='utf-8')
            main([str(inp), '--out', str(out)])
            self.assertEqual(json.loads((out / 'report.json').read_text())['regions'][0]['area'], 2)
            self.assertIn('MASK REGION INSPECTOR', (out / 'regions.svg').read_text())
            with self.assertRaises(SystemExit):
                main([str(inp), '--out', str(out)])

    def test_bad_json(self):
        with tempfile.TemporaryDirectory() as d:
            inp = Path(d) / 'bad.json'
            inp.write_text('{bad', encoding='utf-8')
            with self.assertRaises(SystemExit):
                main([str(inp), '--out', str(Path(d) / 'out')])

    def test_svg(self):
        import xml.etree.ElementTree as ET
        self.assertEqual(ET.fromstring(visual(analyze([[1]]))).tag, '{http://www.w3.org/2000/svg}svg')


if __name__ == '__main__':
    unittest.main()
