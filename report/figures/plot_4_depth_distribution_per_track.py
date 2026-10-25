"""Depth distribution per track.

Source of every number: `site/public/data/comparison.v1.json`, the frozen
comparison audit, and only the rows whose provider is this project. Those 93
rows carry one of three observed depths (worked, executable, assessed) and, for
every row that has a runnable task, the basis that task rests on (real-data or
authored).

What the figure shows. The left panel counts each track's topics by observed
depth. Depth is an ordered quantity, so it takes the palette's ordered ladder,
pale for worked and dark for assessed. The right panel splits the runnable
topics of each track by what their runnable task rests on. A task that computes
on measured records, or that runs a real simulation, docking or structure
prediction, rests on real data; a task that runs on hand-written or synthetic
inputs rests on authored inputs. The audit counts an executable-on-real-data
cell only when the basis is real data, so the split is what decides that
threshold.

What it does not show. The depth is what a reviewer of this project observed
in the material, not what a learner achieved and not what a model scored. The
run basis says what the task rests on, not whether the task is correct. Five
tracks have no runnable topic at all, which the figure shows as an empty bar
rather than as a zero, because a track with no runnable topic is a different
fact from a track whose runnable topics were not counted.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import figure_style as style  # noqa: E402  (the module sits next to this script)

FIGURE_NUMBER = 4
STEM = "plot_4_depth_distribution_per_track"
SELF_ID = "aidd-commons"
DEPTHS = ["worked", "executable", "assessed"]
BASES = ["real-data", "authored"]
BASE_COLOUR = {"real-data": "ember", "authored": "slate"}

CAPTION = (
    "Observed depth per track for this project's {topics} audited topics, beside the basis each "
    "track's runnable topics rest on. {depths}, and of the {runnable} runnable topics {bases}. "
    "Depth records what a reviewer observed in the material, not what a learner achieved."
)


def build() -> dict[str, Path]:
    """Draw the figure and write its two files plus its caption fragment."""
    style.apply_style("light")
    tokens = style.tokens("light")
    colours = style.categorical("light")
    hatches = style.atlas_palette.HATCH
    ladder = style.ladder_steps("light", len(DEPTHS))

    payload = style.load_json(style.DATA_DIR / "comparison.v1.json")
    rows = [row for row in payload["rows"] if row["provider_id"] == SELF_ID]

    order: list[str] = []
    depth_by_track: dict[str, Counter] = defaultdict(Counter)
    base_by_track: dict[str, Counter] = defaultdict(Counter)
    track_order: dict[str, int] = {}
    for row in sorted(rows, key=lambda item: item["track_order"]):
        track = row["track_id"]
        if track not in depth_by_track:
            order.append(track)
            track_order[track] = row["track_order"]
        depth_by_track[track][row["depth"]] += 1
        if row["run_basis"]:
            base_by_track[track][row["run_basis"]] += 1

    labels = list(order)
    positions = list(range(len(order)))[::-1]

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
        width_ratios=[1.55, 1.0],
    )
    depth_ax, basis_ax = axes

    left_edges = [0.0] * len(order)
    for depth, colour in zip(DEPTHS, ladder, strict=True):
        values = [depth_by_track[track][depth] for track in order]
        container = depth_ax.barh(
            positions,
            values,
            left=left_edges,
            height=0.68,
            color=colour,
            edgecolor=tokens["ink"],
            linewidth=0.5,
            label=depth,
            zorder=3,
        )
        for bar in container:
            bar.set_hatch(style.hatch_for_index(DEPTHS.index(depth)))
        left_edges = [edge + value for edge, value in zip(left_edges, values, strict=True)]

    depth_ax.set_yticks(positions)
    depth_ax.set_yticklabels(labels, fontsize=7.4)
    depth_ax.tick_params(axis="y", length=0)
    depth_ax.set_xlabel("Topics", fontsize=8.5)
    depth_ax.set_xlim(0, max(left_edges) * 1.18)
    depth_ax.set_xticks([0, 2, 4, 6, 8])
    depth_ax.grid(axis="x", linewidth=0.6, alpha=0.7)
    depth_ax.set_axisbelow(True)
    style.title(depth_ax, "Observed depth per track")
    depth_ax.legend(
        loc="lower right",
        fontsize=8.0,
        handlelength=1.4,
        handletextpad=0.5,
        borderpad=0.3,
        frameon=False,
    )
    for position, total in zip(positions, left_edges, strict=True):
        depth_ax.annotate(
            str(int(total)),
            xy=(total, position),
            xytext=(4, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=7.4,
            color=tokens["ink"],
        )

    left_edges = [0.0] * len(order)
    for basis in BASES:
        values = [base_by_track[track][basis] for track in order]
        container = basis_ax.barh(
            positions,
            values,
            left=left_edges,
            height=0.68,
            color=colours[BASE_COLOUR[basis]],
            edgecolor=tokens["ink"],
            linewidth=0.5,
            label=basis,
            zorder=3,
        )
        for bar in container:
            bar.set_hatch(hatches[BASE_COLOUR[basis]])
        left_edges = [edge + value for edge, value in zip(left_edges, values, strict=True)]

    basis_ax.set_yticks(positions)
    basis_ax.set_yticklabels([])
    basis_ax.set_ylim(-0.7, len(order) - 0.3)
    basis_ax.set_xlabel("Runnable topics", fontsize=8.5)
    basis_ax.set_xlim(0, 10)
    basis_ax.set_xticks([0, 2, 4, 6, 8])
    basis_ax.grid(axis="x", linewidth=0.6, alpha=0.7)
    basis_ax.set_axisbelow(True)
    style.title(basis_ax, "Run basis")
    basis_ax.legend(
        loc="lower right",
        fontsize=8.0,
        handlelength=1.4,
        handletextpad=0.5,
        borderpad=0.3,
        frameon=False,
    )
    for position, _track, total in zip(positions, order, left_edges, strict=True):
        if total == 0:
            basis_ax.annotate(
                "none",
                xy=(0, position),
                xytext=(4, 0),
                textcoords="offset points",
                ha="left",
                va="center",
                fontsize=7.4,
                color=tokens["muted"],
            )
            continue
        basis_ax.annotate(
            str(int(total)),
            xy=(total, position),
            xytext=(4, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=7.4,
            color=tokens["ink"],
        )

    written = style.save(fig, STEM)
    depth_totals = {depth: sum(depth_by_track[track][depth] for track in order) for depth in DEPTHS}
    basis_totals = {basis: sum(base_by_track[track][basis] for track in order) for basis in BASES}
    runnable = sum(depth_totals[depth] for depth in DEPTHS if depth != "worked")
    style.register_caption(
        FIGURE_NUMBER,
        CAPTION.format(
            topics=len(rows),
            depths=style.english_list(f"{depth_totals[depth]} {depth}" for depth in DEPTHS),
            runnable=runnable,
            bases=(
                f"{basis_totals['real-data']} rest on real data and "
                f"{basis_totals['authored']} rest on authored inputs"
            ),
        ),
    )
    return written


if __name__ == "__main__":
    for artefact in build().items():
        print(f"wrote {artefact[1]}")
