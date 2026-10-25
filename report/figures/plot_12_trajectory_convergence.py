"""Trajectory convergence.

Source of every number: `site/src/content/docs/labs/rmd17-dynamics-observable.mdx`,
the published lab page for the rMD17 trajectory observable. There is no
`labs/rmd17_system_state/observable-summary.json` in this repository, so the
reviewed artefact for this lab is the page itself, and the convergence table is
parsed out of it rather than transcribed. The parser is shared with the
uncertainty figure, which reads the same page.

What the figure shows. The cumulative mean of the radius of gyration over the
first k chronologically ordered frames, compared with the full 100,000-frame
mean, for both molecules. The horizontal axis is the number of frames included
on a log scale and the vertical axis is the signed difference from the full
trajectory mean.

The malonaldehyde curve does not settle monotonically. It is closer at a
thousand frames than it is at ten thousand, so a reader who checked only the
ten-thousand-frame point would conclude that more frames made the estimate
worse. That is in the data and it is drawn as it stands.

What it does not show. One trajectory per molecule and one level of theory, so
nothing here speaks to replicate dependence or force-field sensitivity. No new
simulation is run. A radius of gyration is one scalar for a nine-atom molecule
and its dynamic range is inherently small. Ten percent of a trajectory is not
automatically enough, and a fixed number of frames does not transfer its
adequacy from one molecule to another.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import figure_style as style  # noqa: E402  (the module sits next to this script)
from plot_11_correlated_frames_error_bars import read_observable_page  # noqa: E402

FIGURE_NUMBER = 12
STEM = "plot_12_trajectory_convergence"
SYSTEMS = ["ethanol", "malonaldehyde"]

CAPTION = (
    "The cumulative mean of the radius of gyration against the full 100,000-frame mean, from the "
    "rMD17 lab page. {values}. The malonaldehyde curve is not monotone, being closer at a thousand "
    "frames than at ten thousand, and that is drawn as the data stands. One trajectory per "
    "molecule and one level of theory means nothing here speaks to replicate dependence or "
    "force-field sensitivity."
)


def build() -> dict[str, Path]:
    """Draw the figure and write its two files plus its caption fragment."""
    style.apply_style("light")
    tokens = style.tokens("light")
    colours = style.categorical("light")
    dashes = style.dashes("light")

    page = read_observable_page()
    convergence = sorted(page["convergence"], key=lambda entry: entry["frames"])
    frames = [entry["frames"] for entry in convergence]

    fig = style.figure(style.FIGURE_WIDTH, 4.2)
    ax = fig.add_subplot(111)
    fig.subplots_adjust(left=0.10, right=0.985, bottom=0.145, top=0.90)

    series = [
        ("ethanol", "Ethanol", colours["teal"], "o", dashes["teal"]),
        ("malonaldehyde", "Malonaldehyde", colours["coral"], "s", dashes["coral"]),
    ]
    for key, _label, colour, marker, dash in series:
        values = [entry[key] for entry in convergence]
        ax.plot(
            frames,
            values,
            color=colour,
            marker=marker,
            markersize=6.0,
            markerfacecolor=colour,
            markeredgecolor=tokens["ink"],
            markeredgewidth=0.5,
            linewidth=1.8,
            linestyle=dash,
            zorder=3,
        )
        for frame, value in zip(frames, values, strict=True):
            if value == 0:
                continue
            ax.annotate(
                f"{value:+.5f}",
                xy=(frame, value),
                xytext=(0, 9 if key == "ethanol" else -15),
                textcoords="offset points",
                ha="center",
                fontsize=7.0,
                color=tokens["ink"],
            )

    ax.axhline(0, color=tokens["ink"], linewidth=0.9, zorder=2)
    ax.annotate(
        "the full-trajectory mean",
        xy=(frames[0], 0),
        xytext=(6, -12),
        textcoords="offset points",
        ha="left",
        fontsize=7.4,
        color=tokens["muted"],
    )
    ax.set_xscale("log")
    ax.set_xticks(frames)
    ax.set_xticklabels([f"{frame:,}" for frame in frames], fontsize=8.4)
    ax.set_xlabel("Frames included, chronologically ordered", fontsize=8.5)
    ax.set_ylabel("Difference from the full-trajectory mean (Å)", fontsize=8.5)
    ax.set_ylim(-0.032, 0.012)
    ax.grid(axis="y", linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)
    style.title(ax, "Cumulative mean against the full trajectory")

    handles = [
        _handle(colour, marker, dash) for _, _, colour, marker, dash in series
    ]
    ax.legend(
        handles,
        [label for _, label, _, _, _ in series],
        loc="lower left",
        fontsize=8.2,
        handletextpad=0.5,
        borderpad=0.3,
        frameon=False,
        ncol=2,
        columnspacing=1.6,
    )

    written = style.save(fig, STEM)
    values_text = style.english_list(
        f"{entry['ethanol']:+.5f} Å for ethanol and {entry['malonaldehyde']:+.5f} Å for "
        f"malonaldehyde at {entry['frames']:,} frames"
        for entry in convergence
        if entry["frames"] != max(frames)
    )
    style.register_caption(FIGURE_NUMBER, CAPTION.format(values=values_text))
    return written


def _handle(colour: str, marker: str, dash: object):
    """A legend handle in the shape of a line mark."""
    from matplotlib.lines import Line2D

    return Line2D(
        [0],
        [0],
        color=colour,
        marker=marker,
        markersize=5.6,
        markerfacecolor=colour,
        markeredgecolor=style.tokens("light")["ink"],
        markeredgewidth=0.5,
        linewidth=1.8,
        linestyle=dash,
    )


if __name__ == "__main__":
    for artefact in build().items():
        print(f"wrote {artefact[1]}")
