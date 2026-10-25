"""Curriculum units per track.

Source of every number: `catalog/curriculum/tracks.yaml`, the curriculum
registry that the website renders from and that the coverage audit reads. The
file holds eighteen tracks, each with its ordered lessons, and a flat list of
120 learning units, each carrying the track it belongs to and one of three
layers.

What the figure shows. The left panel counts learning units per track, split
by layer: core, research and practice. The right panel counts the lessons per
track, because a unit is attached to a lesson and the two counts are not the
same thing. The tracks are in curriculum order, so the figure reads as the
sequence the learner walks.

What it does not show. A unit is a learning objective attached to a lesson, not
a piece of content and not an assessment. The counts say nothing about how
long a track takes, how hard it is, or whether a learner reaches the end of
it. Nothing here is a coverage claim, and nothing here is a measure of
learning.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import figure_style as style  # noqa: E402  (the module sits next to this script)

FIGURE_NUMBER = 3
STEM = "plot_3_curriculum_units_per_track"
LAYERS = ["core", "research", "practice"]
LAYER_COLOUR = {"core": "teal", "research": "coral", "practice": "slate"}

CAPTION = (
    "Curriculum units per track across the {tracks} tracks, split by layer, beside the number of "
    "lessons in each track. The curriculum holds {units} learning units in {lessons} lessons, "
    "{layers}. A unit is a learning objective attached to a lesson, so the two counts differ, and "
    "neither one says how long a track takes or whether a learner reaches its end."
)


def build() -> dict[str, Path]:
    """Draw the figure and write its two files plus its caption fragment."""
    style.apply_style("light")
    tokens = style.tokens("light")
    colours = style.categorical("light")
    hatches = style.atlas_palette.HATCH

    registry = style.load_yaml(style.REPO_ROOT / "catalog" / "curriculum" / "tracks.yaml")
    tracks = sorted(registry["tracks"], key=lambda track: track["order"])
    units_per_track: dict[str, Counter] = {track["id"]: Counter() for track in tracks}
    for unit in registry["units"]:
        units_per_track[unit["track_id"]][unit["layer"]] += 1

    labels = [track["id"] for track in tracks]
    positions = list(range(len(tracks)))[::-1]

    fig = style.figure(style.FIGURE_WIDTH, 6.5)
    axes = style.axes_grid(
        fig,
        1,
        2,
        left=0.255,
        right=0.985,
        bottom=0.085,
        top=0.915,
        wspace=0.12,
        width_ratios=[2.5, 1.0],
    )
    units_ax, lessons_ax = axes

    left_edges = [0.0] * len(tracks)
    for layer in LAYERS:
        values = [units_per_track[track["id"]][layer] for track in tracks]
        container = units_ax.barh(
            positions,
            values,
            left=left_edges,
            height=0.68,
            color=colours[LAYER_COLOUR[layer]],
            edgecolor=tokens["ink"],
            linewidth=0.5,
            label=layer,
            zorder=3,
        )
        for bar, layer_name in zip(container, [layer] * len(container), strict=True):
            bar.set_hatch(hatches[LAYER_COLOUR[layer_name]])
        left_edges = [edge + value for edge, value in zip(left_edges, values, strict=True)]

    units_ax.set_yticks(positions)
    units_ax.set_yticklabels(labels, fontsize=7.4)
    units_ax.tick_params(axis="y", length=0)
    units_ax.set_xlabel("Learning units", fontsize=8.5)
    units_ax.set_xlim(0, max(left_edges) * 1.16)
    units_ax.set_xticks([0, 2, 4, 6, 8])
    units_ax.grid(axis="x", linewidth=0.6, alpha=0.7)
    units_ax.set_axisbelow(True)
    style.title(units_ax, "Units per track by layer")
    units_ax.legend(
        loc="lower right",
        fontsize=8.0,
        handlelength=1.4,
        handletextpad=0.5,
        borderpad=0.3,
        frameon=False,
    )
    for position, _track, total in zip(positions, tracks, left_edges, strict=True):
        units_ax.annotate(
            str(int(total)),
            xy=(total, position),
            xytext=(4, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=7.6,
            color=tokens["ink"],
        )

    lesson_counts = [len(track["lessons"]) for track in tracks]
    lessons_ax.hlines(
        positions,
        0,
        lesson_counts,
        color=tokens["rule"],
        linewidth=1.0,
        zorder=2,
    )
    lessons_ax.plot(
        lesson_counts,
        positions,
        linestyle="none",
        marker="o",
        markersize=5.0,
        markerfacecolor=tokens["ink"],
        markeredgecolor=tokens["panel"],
        markeredgewidth=0.6,
        zorder=3,
    )
    lessons_ax.set_yticks(positions)
    lessons_ax.set_yticklabels([])
    lessons_ax.set_ylim(-0.7, len(tracks) - 0.3)
    lessons_ax.set_xlim(0, max(lesson_counts) * 1.22)
    lessons_ax.set_xticks([0, 2, 4, 6])
    lessons_ax.set_xlabel("Lessons", fontsize=8.5)
    lessons_ax.grid(axis="x", linewidth=0.6, alpha=0.7)
    lessons_ax.set_axisbelow(True)
    style.title(lessons_ax, "Lessons per track")

    written = style.save(fig, STEM)
    layer_totals = {
        layer: sum(units_per_track[track["id"]][layer] for track in tracks) for layer in LAYERS
    }
    style.register_caption(
        FIGURE_NUMBER,
        CAPTION.format(
            tracks=len(tracks),
            units=sum(layer_totals.values()),
            lessons=sum(lesson_counts),
            layers=style.english_list(
                f"{layer_totals[layer]} {layer}" for layer in LAYERS if layer_totals[layer]
            ),
        ),
    )
    return written


if __name__ == "__main__":
    for artefact in build().items():
        print(f"wrote {artefact[1]}")
