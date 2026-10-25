"""Exercise native figure delivery and its wrong-size/stale-caption failure modes."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load_script(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "site/scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


renderer = load_script("site_figure_renderer", "make-site-figures.py")
checker = load_script("site_figure_checker", "check-site-figures.py")

import matplotlib.pyplot as plt  # noqa: E402


class AtlasFigureDeliveryTests(unittest.TestCase):
    def test_the_native_schematic_entry_point_writes_pdf_and_png_only(self):
        import schematic_style

        with tempfile.TemporaryDirectory(prefix="aidd-schematic-delivery-") as directory:
            canvas = schematic_style.Canvas(2, 1)
            paths = canvas.save(Path(directory), "schematic-test")
            self.assertEqual([path.suffix for path in paths], [".pdf", ".png"])
            self.assertTrue(all(path.is_file() for path in paths))
            self.assertFalse(list(Path(directory).glob("*.svg")))
            plt.close(canvas.fig)

    def test_native_pair_valid_and_known_delivery_defects(self):
        with tempfile.TemporaryDirectory(prefix="aidd-figure-delivery-") as directory:
            output = Path(directory)
            fig = plt.figure(figsize=(2, 1))
            fig.add_axes((0.2, 0.2, 0.7, 0.7)).bar([0], [93], hatch="//")
            with patch.object(renderer, "FIGURE_OUT", output):
                products = renderer.save_preview(fig, "plot_5_self_record_vs_reading")
            self.assertEqual(set(products), {"png", "pdf"})
            self.assertFalse(list(output.glob("*.svg")))
            self.assertFalse(plt.fignum_exists(fig.number))
            row = {
                "id": "second-reading",
                "source_stem": "plot_5_self_record_vs_reading",
                "file": products["png"].name,
                "pdf": products["pdf"].name,
                "width": 600,
                "height": 300,
                "alt": "A retained aggregate of 93 topics, not independent replication.",
                "caption": "Current aggregate caption.",
                "pages": ["/audit/"],
            }
            captions = {"5": row["caption"]}
            self.assertEqual(checker.check_delivery(row, output, captions, {}), [])

            wrong_size = {**row, "width": 601}
            self.assertEqual(
                checker.check_delivery(wrong_size, output, captions, {}),
                ["second-reading: declared dimensions differ from the PNG"],
            )
            stale = {**row, "caption": "Earlier single-pass caption."}
            self.assertEqual(
                checker.check_delivery(stale, output, captions, {}),
                ["second-reading: caption differs from its native source manifest"],
            )
            with patch.object(Path, "is_file", return_value=False):
                missing = checker.check_delivery(row, output, captions, {})
            self.assertTrue(any(".pdf is not a regular delivery file" in item for item in missing))

    def test_an_empty_production_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="aidd-figure-manifest-") as directory:
            path = Path(directory) / "manifest.json"
            path.write_text('{"figures": []}', encoding="utf-8")
            with patch.object(checker, "MANIFEST_PATH", path):
                self.assertEqual(checker.check_manifest(), ["the manifest registers no figure"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
