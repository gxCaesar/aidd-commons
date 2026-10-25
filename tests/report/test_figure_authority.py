"""Source/denominator regressions without reading mutable catalogue projections."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "report/figures"))

import figure_sources as sources  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import plot_1_registry_composition as plot1  # noqa: E402
import plot_5_self_record_vs_reading as plot5  # noqa: E402
import plot_7_access_and_licence as plot7  # noqa: E402


def reading_payload() -> dict:
    counts = [93, 93, 81, 62, 81]
    return {
        "as_of": "2026-10-25",
        "taxonomy": {"topics": 93},
        "second_readings": [
            {
                "id": plot5.READING_ID,
                "reviewed_on": "2026-09-11",
                "reviewer": (
                    "Initial batches began on 2026-09-11. "
                    "A later batch on 2026-10-24 re-read topics. "
                    "An unrelated software date is 2026-12-31."
                ),
                "cells": 93,
                "equal": 93,
                "reading_deeper": 0,
                "reading_shallower": 0,
                "thresholds": [
                    {"threshold": threshold, "recorded": count, "reading": count}
                    for threshold, count in zip(plot5.THRESHOLD_TITLES, counts, strict=True)
                ],
            }
        ],
    }


class FigureAuthorityTests(unittest.TestCase):
    def test_custom_pie_model_terms_stay_outside_the_creative_commons_layer(self):
        self.assertEqual(
            plot7._licence_layer(
                [
                    "CC BY-NC-SA 4.0",
                    "Arc Research Institute PIE Model Non-Commercial License",
                ]
            ),
            "Other stated terms",
        )
        with self.assertRaises(KeyError):
            plot7._licence_layer(["Unmapped future licence"])

    def test_catalogue_caption_uses_the_supplied_projection_and_verification_dates(self):
        resources = [
            {"id": "first", "kind": "model", "last_verified": "2026-09-11"},
            {"id": "second", "kind": "benchmark", "last_verified": "2026-10-25"},
        ]
        caption = plot1.caption(resources, [("benchmark", 1), ("model", 1)])
        self.assertIn("2 catalogue records", caption)
        self.assertIn("canonical Atlas resources.v1 projection", caption)
        self.assertIn("2026-09-11 to 2026-10-25", caption)

    def test_openness_join_requires_the_same_unique_record_ids(self):
        resources = [{"id": "first"}, {"id": "second"}]
        sources.validate_openness_join(resources, [{"id": "second"}, {"id": "first"}])
        with self.assertRaisesRegex(ValueError, "missing.*second.*unexpected.*other"):
            sources.validate_openness_join(resources, [{"id": "first"}, {"id": "other"}])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            sources.validate_openness_join(resources, [{"id": "first"}, {"id": "first"}])
        with self.assertRaisesRegex(ValueError, "catalogue.*duplicate"):
            sources.validate_openness_join([{"id": "first"}, {"id": "first"}], [{"id": "first"}])

    def test_current_aggregate_date_does_not_replace_the_initial_or_latest_batch_dates(self):
        payload = reading_payload()
        series = sources.reading_series(payload, payload["second_readings"][0])
        self.assertEqual(series.aggregate_as_of, "2026-10-25")
        self.assertEqual(series.initiated_on, "2026-09-11")
        self.assertEqual(series.documented_through, "2026-10-24")

    def test_the_actual_93_topic_plot_does_not_clip_the_equal_bar(self):
        payload = reading_payload()
        captured: dict = {}

        def inspect_figure(fig, stem):
            ax = fig.axes[0]
            counts = [patch_.get_width() for patch_ in ax.patches]
            self.assertEqual(counts, [93, 0, 0])
            sources.validate_count_bounds(counts, ax.get_xlim())
            self.assertGreater(ax.get_xlim()[1], 93)
            self.assertEqual(ax.get_xlabel(), "Topics out of 93")
            plt.close(fig)
            return {}

        def capture_caption(number, text):
            captured[number] = text

        with (
            patch.object(plot5.style, "load_json", return_value=payload),
            patch.object(plot5.style, "save", side_effect=inspect_figure),
            patch.object(plot5.style, "register_caption", side_effect=capture_caption),
        ):
            plot5.build()
        self.assertIn("projection dated 2026-10-25", captured[5])
        self.assertIn("series began on 2026-09-11", captured[5])
        self.assertIn("re-readings through 2026-10-24", captured[5])
        self.assertIn("not an independent replication", captured[5])

    def test_the_known_66_limit_defect_and_wrong_denominator_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "93.*outside.*66"):
            sources.validate_count_bounds([93, 0, 0], (0, 66))
        payload = reading_payload()
        payload["second_readings"][0]["cells"] = 92
        with self.assertRaisesRegex(ValueError, "topic denominator"):
            sources.reading_series(payload, payload["second_readings"][0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
