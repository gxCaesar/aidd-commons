"""Access level and licence layers.

Source of every number: `site/public/data/resources.v1.json`, the catalogue
export, used as a live projection rather than a historical release snapshot.
Every record carries an access level and a list of licences, each with
its own scope and evidence.

What the figure shows. The left panel counts records by access level. The right
panel counts records by licence layer.

The licence layers are a grouping this script makes, so they are stated here in
full and the mapping is enforced rather than assumed: every licence name in the
catalogue must appear in the table below, and a name that does not raise an
error instead of being counted silently. The layers run from the most
permissive to the most restrictive, and a record that carries more than one
licence is counted once, in the most restrictive layer it carries, so that the
unit of the panel is the record rather than the licence entry. The number of
multi-licence records is derived from the same projection in the caption.

What it does not show. The access level is what a reader could establish about
access, not a guarantee that the artefact runs. A licence name is not a legal
opinion, and the scope field on each licence is not folded into the layer
count. A record with no licence recorded is not a record with no licence; it
is a record whose licence has not been read, which is why that bar is drawn
empty rather than coloured.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import figure_style as style  # noqa: E402  (the module sits next to this script)
from figure_sources import catalogue_projection  # noqa: E402

FIGURE_NUMBER = 7
STEM = "plot_7_access_and_licence"

#: Licence layers, most permissive first. The order is also the order of
#: restriction used when a record carries more than one licence.
LICENCE_LAYERS: list[tuple[str, list[str]]] = [
    (
        "Public domain dedication",
        [
            "CC0",
            "CC0 1.0",
            "CC0 1.0 Universal",
            "CC0-1.0",
            "United States Government work, public domain",
        ],
    ),
    (
        "Permissive software licence",
        ["MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause", "ASL", "New BSD"],
    ),
    (
        "Creative Commons attribution",
        [
            "CC-BY-4.0",
            "CC BY 4.0",
            "CC BY-4.0",
            "Creative Commons Attribution 4.0 International",
            "Creative Commons Attribution 4.0 International Public License",
        ],
    ),
    (
        "Copyleft",
        [
            "GPL-3.0",
            "GPL-2.0",
            "GPL-2.0 with clarifying addendum",
            "LGPL-2.1",
            "MPL-2.0",
            "GNU Affero General Public License v3",
            "CC BY-SA 4.0",
            "Creative Commons Attribution-ShareAlike 3.0 Unported",
        ],
    ),
    (
        "Creative Commons non-commercial",
        [
            "CC BY-NC 4.0",
            "CC-BY-NC-ND-4.0",
            # The share-alike variant is non-commercial first. It adds a
            # share-alike condition, and the non-commercial restriction is the
            # one that decides what a reader may do with the artefact.
            "CC BY-NC-SA 4.0",
        ],
    ),
    (
        "Other stated terms",
        [
            # A vendor's own open model licence, published as its own terms
            # rather than as a variant of a standard licence.
            "NVIDIA Open Model License",
            # A specification offered under a community specification licence
            # together with an attribution licence, published as its own terms.
            "Community-Spec-1.0 with CC-BY-3.0",
            # A data portal's own use terms, and an academic licence that
            # permits research use and withholds commercial use. Both are
            # published terms rather than variants of a standard licence.
            "DepMap Portal Data Terms and Conditions",
            "DrugBank Academic License",
            # A portal's own data licence, published as its own terms: it
            # charges nothing and restricts no use, but it does require an
            # acknowledgement and that redistributed products say whether
            # they carry the most current data.
            "GTEx Portal Data License",
            # Apache-2.0 conditioned by the Commons Clause v1.0. The clause
            # withholds the right to sell the software, so the grant is not the
            # permissive one.
            "Apache-2.0 with Commons Clause v1.0",
            "EMBL-EBI Terms of Use",
            "Polaris Platform Agreement",
            "The scFoundation License",
            "Other (Open)",
            "Proprietary, no open-source licence",
            # PIE checkpoints use Arc's custom model terms, separate from the
            # repository's Creative Commons source-code licence.
            "Arc Research Institute PIE Model Non-Commercial License",
        ],
    ),
]
NO_LICENCE = "No licence recorded"

#: Access levels, most open first. The order is a presentational one; the
#: counts are not.
ACCESS_ORDER = [
    "open_weights",
    "open_source",
    "source_available",
    "research_only",
    "gated",
    "closed",
    "unverified",
]


def caption(
    resources: list[dict],
    access_counts: Counter,
    layer_counts: Counter,
) -> str:
    """The caption fragment, with its numbers taken from the file that was read."""
    access = ", ".join(
        f"{access_counts[level]} {level.replace('_', ' ')}"
        for level in ACCESS_ORDER
        if access_counts[level] and level != "unverified"
    )
    layers = ", ".join(
        f"{layer_counts[name]} {name.lower()}" for name, _ in LICENCE_LAYERS if layer_counts[name]
    )
    snapshot = catalogue_projection(resources)
    multi_licence = sum(len(record.get("licenses", [])) > 1 for record in resources)
    return (
        f"Access level and licence layer for the {snapshot.records} catalogue records. "
        f"{snapshot.source_note()} "
        f"{access_counts['unverified']} records carry no verified access level and "
        f"{layer_counts[NO_LICENCE]} record no licence. The verified access levels are {access}. "
        f"By licence layer, {layers}. The {multi_licence} records with more than one licence "
        "are counted once, in their most restrictive stated layer."
    )


def _licence_layer(names: list[str]) -> str:
    """The most restrictive layer among a record's licences."""
    rank = {name: index for index, (_, members) in enumerate(LICENCE_LAYERS) for name in members}
    unknown = [name for name in names if name not in rank]
    if unknown:
        raise KeyError(f"licence names without a layer: {unknown}")
    return LICENCE_LAYERS[max(rank[name] for name in names)][0]


def build() -> dict[str, Path]:
    """Draw the figure and write its two files plus its caption fragment."""
    style.apply_style("light")
    tokens = style.tokens("light")
    colours = style.categorical("light")
    resources = style.load_json(style.DATA_DIR / "resources.v1.json")

    access_counts = Counter(record["access_level"]["value"] for record in resources)
    layer_counts = Counter()
    for record in resources:
        names = [licence["name"] for licence in record.get("licenses", [])]
        layer_counts[_licence_layer(names) if names else NO_LICENCE] += 1

    fig = style.figure(style.FIGURE_WIDTH, 4.3)
    axes = style.axes_grid(
        fig,
        1,
        2,
        left=0.235,
        right=0.985,
        bottom=0.135,
        top=0.90,
        wspace=0.52,
        width_ratios=[1.0, 1.15],
    )
    access_ax, licence_ax = axes

    access_values = [access_counts[level] for level in ACCESS_ORDER]
    access_positions = list(range(len(ACCESS_ORDER)))[::-1]
    container = access_ax.barh(
        access_positions,
        access_values,
        height=0.62,
        color=colours["teal"],
        edgecolor=tokens["ink"],
        linewidth=0.6,
        zorder=3,
    )
    for bar, level in zip(container, ACCESS_ORDER, strict=True):
        bar.set_hatch(style.hatch_for_index(ACCESS_ORDER.index(level)))
    access_ax.set_yticks(access_positions)
    access_ax.set_yticklabels([level.replace("_", " ") for level in ACCESS_ORDER], fontsize=8.0)
    access_ax.tick_params(axis="y", length=0)
    access_ax.set_xlabel("Records", fontsize=8.5)
    access_ax.set_xlim(0, max(access_values) * 1.16)
    access_ax.set_xticks([0, 40, 80, 120])
    access_ax.grid(axis="x", linewidth=0.6, alpha=0.7)
    access_ax.set_axisbelow(True)
    style.title(access_ax, "Access level")
    style.bar_labels(
        access_ax, container, access_values, orientation="horizontal", pad=4, fontsize=7.8
    )

    licence_order = [name for name, _ in LICENCE_LAYERS] + [NO_LICENCE]
    licence_values = [layer_counts[name] for name in licence_order]
    licence_positions = list(range(len(licence_order)))[::-1]
    container = licence_ax.barh(
        licence_positions,
        licence_values,
        height=0.62,
        color=colours["teal"],
        edgecolor=tokens["ink"],
        linewidth=0.6,
        zorder=3,
    )
    for bar, name in zip(container, licence_order, strict=True):
        if name == NO_LICENCE:
            bar.set_facecolor(tokens["panel"])
            bar.set_hatch("..")
        else:
            bar.set_hatch(style.hatch_for_index(licence_order.index(name)))
    licence_ax.set_yticks(licence_positions)
    licence_ax.set_yticklabels(
        [
            "public domain dedication",
            "permissive software\nlicence",
            "Creative Commons\nattribution",
            "copyleft",
            "Creative Commons\nnon-commercial",
            "other stated terms",
            "no licence recorded",
        ],
        fontsize=8.0,
    )
    licence_ax.tick_params(axis="y", length=0)
    licence_ax.set_xlabel("Records", fontsize=8.5)
    licence_ax.set_xlim(0, max(licence_values) * 1.16)
    licence_ax.set_xticks([0, 40, 80, 120])
    licence_ax.grid(axis="x", linewidth=0.6, alpha=0.7)
    licence_ax.set_axisbelow(True)
    style.title(licence_ax, "Licence layer")
    style.bar_labels(
        licence_ax, container, licence_values, orientation="horizontal", pad=4, fontsize=7.8
    )

    written = style.save(fig, STEM)
    style.register_caption(FIGURE_NUMBER, caption(resources, access_counts, layer_counts))
    return written


if __name__ == "__main__":
    for artefact in build().items():
        print(f"wrote {artefact[1]}")
