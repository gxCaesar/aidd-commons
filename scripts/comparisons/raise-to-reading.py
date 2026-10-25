"""Raise the self record to the depth an independent reading already supports.

The second reading is the project's only route to raising a topic, and several
readings have already said `assessed` on a runnable basis for topics whose
record still says `executable`. The record is not allowed to be deeper than the
reading, and it is not required to be deeper, so these twenty-nine topics sat
one step below what an independent reviewer had verified.

    python scripts/comparisons/raise-to-reading.py            # report the plan
    python scripts/comparisons/raise-to-reading.py --write    # apply it

The reading's own limits are copied into the note, because a raise that states
only the verdict would claim more than the reviewer checked. The edits are
line-level, so the surrounding file keeps its shape.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "catalog/comparisons/systems/aidd-commons.yaml"

#: topic id -> (new depth, new run basis, note edit).
#:
#: A note edit is either ("append", text) or ("replace", old, new). The replace
#: form is used where the old note stated a reason for staying at the shallower
#: depth, which the reading removes.
RAISES: dict[str, tuple[str, str, tuple]] = {
    't07-property-task-split-design': (
        'assessed',
        'real-data',
        (
            "append",
            "The fiftieth independent reading at commit 042dfe9 scored the topic assessed on real "
            "data, and the self record now states the reading. The reading named what the laboratory "
            "does not reach, that a combined future-series, time and source partition is discussed "
            "but not implemented."
        ),
    ),
    't07-calibration': (
        'assessed',
        'real-data',
        (
            "append",
            "The fiftieth independent reading at commit 042dfe9 scored the topic assessed on real "
            "data, and the self record now states the reading. The reading named what the laboratory "
            "does not reach, that the public-data execution covers marginal regression intervals "
            "while classification calibration and subgroup-conditional calibration lack comparable "
            "runnable tasks."
        ),
    ),
    't07-interpretability-sar': (
        'assessed',
        'authored',
        (
            "append",
            "The fiftieth independent reading at commit 042dfe9 scored the topic assessed on authored "
            "inputs, and the self record now states the reading. The reading named what the "
            "laboratory does not reach, that measured analogue validation and a comparison of "
            "explanation methods are absent."
        ),
    ),
    't07-property-decision-use': (
        'assessed',
        'real-data',
        (
            "append",
            "The fiftieth independent reading at commit 042dfe9 scored the topic assessed on real "
            "data, and the self record now states the reading. The reading named what the laboratory "
            "does not reach, that no prospective experimental outcome and no coverage guarantee for "
            "the selected batch is established."
        ),
    ),
    't07-chemical-standardisation': (
        'assessed',
        'real-data',
        (
            "replace",
            "No exercise tests the learner on them, so this is not scored as assessed."
,
            "The fiftieth independent reading at commit 042dfe9 scored the topic assessed on real "
            "data, and the self record now states the reading. The reading found that the "
            "worked-answer exercises test salt-to-parent identity, duplicate grouping and the "
            "retention of tested forms under declared rules, and that the runnable ChEMBL audits "
            "apply the declared rules to public records. It also named what the laboratory does not "
            "reach, that no integrated property-dataset exercise freezes and applies the charge, "
            "tautomer, stereochemistry and mixture policies together."
        ),
    ),
    't07-property-representation-selection': (
        'assessed',
        'real-data',
        (
            "append",
            "The fiftieth independent reading at commit 042dfe9 scored the topic assessed on real "
            "data, and the self record now states the reading. The reading named what the laboratory "
            "does not reach, that the graph and three-dimensional choices are explained but lack "
            "matched executable comparisons for this property task."
        ),
    ),
    't08-exposure-pk-endpoint': (
        'assessed',
        'real-data',
        (
            "replace",
            "The self record takes the shallower of the two, executable."
,
            "The fiftieth independent reading at commit 042dfe9 scored the topic assessed on real "
            "data, and the self record now states the reading. The reading named what the laboratory "
            "does not reach, that the public-data execution covers clearance only, without measured "
            "absorption, distribution, oral bioavailability or route-dependent exposure profiles."
        ),
    ),
    't08-metabolism-ddi-risk': (
        'assessed',
        'real-data',
        (
            "replace",
            "The self record takes the shallower of the two, executable."
,
            "The fiftieth independent reading at commit 042dfe9 scored the topic assessed on real "
            "data, and the self record now states the reading. The reading named what the laboratory "
            "does not reach, that the transporter assays, the enzyme induction, the metabolite "
            "identification and the quantitative drug-pair interaction interpretation are not "
            "exercised."
        ),
    ),
    't08-safety-toxicity-endpoint': (
        'assessed',
        'authored',
        (
            "append",
            "The fiftieth independent reading at commit 042dfe9 scored the topic assessed on authored "
            "inputs, and the self record now states the reading. The reading named what the "
            "laboratory does not reach, that the topic-specific runnable demonstration contains no "
            "measured toxicity and no exposure-linked risk estimates."
        ),
    ),
    't05-omics-perturbation-representation': (
        'assessed',
        'real-data',
        (
            "replace",
            "The self record takes the shallower of the two, executable."
,
            "The fiftieth independent reading at commit 042dfe9 scored the topic assessed on real "
            "data, and the self record now states the reading. The reading named what the laboratory "
            "does not reach, that the time-course encoding, the varying doses, the single-cell donor "
            "structure and the genetic perturbations are not exercised."
        ),
    ),
    't11-dynamic-simulation-observable': (
        'assessed',
        'real-data',
        (
            "replace",
            "The self record takes the shallower of the two, executable."
,
            "The fiftieth independent reading at commit 042dfe9 scored the topic assessed on real "
            "data, and the self record now states the reading. The reading named what the laboratory "
            "does not reach, that the task neither runs a new simulation nor compares ensembles, and "
            "it recorded that the local raw trajectories were unavailable in the reading sandbox."
        ),
    ),
    't11-convergence-protocol-uncertainty': (
        'assessed',
        'real-data',
        (
            "replace",
            "The self record takes the shallower of the two, executable."
,
            "The fiftieth independent reading at commit 042dfe9 scored the topic assessed on real "
            "data, and the self record now states the reading. The reading named what the laboratory "
            "does not reach, that the replicate dependence, the force-field sensitivity, the "
            "integrator and numerical error and the decision value per unit of compute are not "
            "tested, and it recorded that the local raw trajectories were unavailable in the reading "
            "sandbox."
        ),
    ),
    't12-design-objective-constraints': (
        'assessed',
        'authored',
        (
            "append",
            "The fiftieth independent reading at commit 042dfe9 scored the topic assessed on authored "
            "inputs, and the self record now states the reading. The reading named what the "
            "laboratory does not reach, that the biological target context, the synthesis limits "
            "supported by routes and the experimentally justified property thresholds are absent."
        ),
    ),
    't12-candidate-design-space': (
        'assessed',
        'authored',
        (
            "append",
            "The fiftieth independent reading at commit 042dfe9 scored the topic assessed on authored "
            "inputs, and the self record now states the reading. The reading named what the "
            "laboratory does not reach, that the practical assessment concerns fixed two-dimensional "
            "enumeration and that the learned graph and string spaces and the three-dimensional "
            "spaces lack comparable reachability tasks."
        ),
    ),
    't12-validity-novelty-synthetic-screen': (
        'assessed',
        'authored',
        (
            "append",
            "The fiftieth independent reading at commit 042dfe9 scored the topic assessed on authored "
            "inputs, and the self record now states the reading. The reading named what the "
            "laboratory does not reach, that no generative-model memorization experiment and no route "
            "validation is performed, and that the route feasibility is left unassessed."
        ),
    ),
    't05-protein-sequence-structure-representation': (
        'assessed',
        'real-data',
        (
            "replace",
            "Recorded at executable rather than assessed because no exercise asks the reader to "
            "construct or audit that mapping, although the second reading credited the lesson's "
            "pooling exercise."
,
            "The fifty-first independent reading at commit 042dfe9 scored the topic assessed on real "
            "data, and the self record now states the reading. The reading found that the "
            "masked-pooling exercises have worked answers, and that the task on the deposited "
            "sequences maps them to the reference residues and checks the geometric representations "
            "across structures using public coordinates. It also named what the laboratory does not "
            "reach, that the surface encodings and weighted ensembles receive brief explanations "
            "without worked construction or dedicated assessment."
        ),
    ),
    't09-binder-classification': (
        'assessed',
        'authored',
        (
            "append",
            "The fifty-first independent reading at commit 042dfe9 scored the topic assessed on "
            "authored inputs, and the self record now states the reading. The reading found that the "
            "executable checks and the worked-answer exercise cover the positive thresholds, the "
            "measured inactives, the assumed decoys, the class balance and the scaffold "
            "generalization units, and it named what the laboratory does not reach, that the "
            "measurements are explicitly invented and that no binder classifier is fitted or "
            "evaluated."
        ),
    ),
    't09-affinity-ranking': (
        'assessed',
        'real-data',
        (
            "append",
            "The fifty-first independent reading at commit 042dfe9 scored the topic assessed on real "
            "data, and the self record now states the reading. The reading found that the code "
            "predicts held-out continuous affinities and compares the row-weighted and the "
            "complex-weighted errors, and that the worked-answer exercises assess the independent "
            "units and the endpoint and unit comparability. It also named what the laboratory does "
            "not reach, that the within-series ligand ranking and the ranking-specific uncertainty "
            "remain unworked."
        ),
    ),
    't09-screening-selection-repurposing-transfer': (
        'assessed',
        'real-data',
        (
            "append",
            "The fifty-first independent reading at commit 042dfe9 scored the topic assessed on real "
            "data, and the self record now states the reading. The reading named what the laboratory "
            "does not reach, that the off-target evaluation, the transfer between repurposing "
            "indications and the prospective experimental follow-up are not demonstrated, and that "
            "the runnable evidence concerns two retrospective assays on one target."
        ),
    ),
    't10-complex-cofolding-hypothesis': (
        'assessed',
        'real-data',
        (
            "append",
            "The fifty-first independent reading at commit 042dfe9 scored the topic assessed on real "
            "data, and the self record now states the reading. The reading named what the laboratory "
            "does not reach, that the monomer, complex and co-folding distinctions remain largely "
            "declarative, that no actual structures or binding measurements are compared, and that "
            "the catalogue inspection establishes claim separation and not predictive accuracy."
        ),
    ),
    't10-structural-confidence-alternatives': (
        'assessed',
        'real-data',
        (
            "replace",
            "Recorded at executable rather than assessed because neither lab exercise asks about "
            "confidence or alternatives, although the second reading credited the lesson's exercises. "
            "Disorder and training overlap are not analysed."
,
            "The fifty-first independent reading at commit 042dfe9 scored the topic assessed on real "
            "data, and the self record now states the reading. The reading found that the public "
            "structures support executable comparisons of alternate states, missing residues, "
            "structural uncertainty and steric clashes, and that the cutoff and screening-plan "
            "exercises have worked answers while another exercise interprets pLDDT conservatively. It "
            "also named what the laboratory does not reach, that the ensemble populations and the "
            "training-overlap audits are not operationalized and that the disorder is addressed "
            "mainly through the missing residues."
        ),
    ),
    't11-docking-scoring-protocol': (
        'assessed',
        'authored',
        (
            "append",
            "The fifty-first independent reading at commit 042dfe9 scored the topic assessed on "
            "authored inputs, and the self record now states the reading. The reading named what the "
            "laboratory does not reach, that the assessed task is protocol reasoning and that the "
            "actual docking search, the rescoring and the decoy-based empirical validation are not "
            "performed."
        ),
    ),
    't14-retrosynthetic-disconnection': (
        'assessed',
        'authored',
        (
            "append",
            "The fifty-first independent reading at commit 042dfe9 scored the topic assessed on "
            "authored inputs, and the self record now states the reading. The reading named what the "
            "laboratory does not reach, that no learned disconnector runs and that the laboratory "
            "feasibility is explicitly unassessed."
        ),
    ),
    't15-acquisition-policy-uncertainty': (
        'assessed',
        'real-data',
        (
            "replace",
            "The self record takes the shallower of the two, executable."
,
            "The fifty-first independent reading at commit 042dfe9 scored the topic assessed on real "
            "data, and the self record now states the reading. The reading named what the laboratory "
            "does not reach, that the information-gain policies are not worked through and that the "
            "executable uncertainty signal explicitly lacks predictive-calibration validation."
        ),
    ),
    't16-human-review-authority-evaluation': (
        'assessed',
        'real-data',
        (
            "append",
            "The fifty-first independent reading at commit 042dfe9 scored the topic assessed on "
            "public data, and the self record now states the reading. The reading found that the "
            "fixed five-dimension audit uses actual retained PaperQA outputs and ChEMBL-derived "
            "records, and that the unused-source and false-passing exercises have explicit rejection "
            "targets. It also named what the laboratory does not reach, that it assesses record "
            "auditing rather than agents attempting new tasks, that the human-authorization evidence "
            "is incomplete and that the material does not demonstrate a successful authorized "
            "execution."
        ),
    ),
    't17-ood-transportability': (
        'assessed',
        'real-data',
        (
            "append",
            "The fifty-first independent reading at commit 042dfe9 scored the topic assessed on "
            "public data, and the self record now states the reading. The reading named what the "
            "laboratory does not reach, that the evidence spans two retrospective same-target assays "
            "and that the broader external populations and prospective settings are discussed but not "
            "empirically evaluated."
        ),
    ),
    't17-reproduction-reporting-receipt': (
        'assessed',
        'real-data',
        (
            "replace",
            "No exercise tests the learner on it, so it is not scored as assessed."
,
            "The fifty-first independent reading at commit 042dfe9 scored the topic assessed on "
            "public data, and the self record now states the reading. The reading found that the "
            "checks enforce the agreement among the protocol, environment, selection and result "
            "records, that the FreeSolv case constructs and validates the source and version, the "
            "command, the seeded protocol and the output provenance, and that the drift-rejection "
            "targets and the reproduction-scope exercise assess the learning. It also named what the "
            "laboratory does not reach, that the code revision and the comprehensive failure and "
            "limitation records are not consistently bound into one rerunnable receipt."
        ),
    ),
    't06-mechanism-hypothesis-counterevidence': (
        'assessed',
        'real-data',
        (
            'append',
            " The fifty-second independent reading at commit 468b151 scored the topic"
            " assessed on public data, and the self record now states the reading. The"
            " reading found that the runnable task compares target-specific and"
            " generic-stress patterns against explicit verification targets, and that"
            " the inspection passed. It also named what the laboratory does not reach,"
            " that the runnable case lacks a named disease mechanism, an identified"
            " mediator and a target-engagement measurement, and that the"
            " disease-relevant causal validation remains a proposed next step.",
        ),
    ),
    't13-biologic-modality-construct': (
        'assessed',
        'real-data',
        (
            'append',
            " The fifty-second independent reading at commit 468b151 scored the topic"
            " assessed on public data, and the self record now states the reading. The"
            " reading found that the runnable audit checks committed UniProt and"
            " DailyMed passages and supplies an interpretation exercise with an answer,"
            " and that the inspection passed. It also named what the laboratory does"
            " not reach, that the executable cohort is limited to six protein"
            " therapeutics.",
        ),
    ),
    't18-evidence-package-claim-chain': (
        'assessed',
        'real-data',
        (
            'append',
            " The fifty-second independent reading at commit 468b151 scored the topic"
            " assessed on public data, and the self record now states the reading. The"
            " reading found that the eight-link audit and the answered interpretation"
            " exercise test bounded claims using activity, CYP inhibition and"
            " clearance records, and that the inspection passed. It also named what the"
            " laboratory does not reach, that mechanism, intended-target validation,"
            " safety, synthesis and independent reproducibility remain unmeasured, and"
            " that CYP inhibition and in vitro clearance do not establish therapeutic"
            " selectivity or systemic exposure, so no complete empirical nomination"
            " chain is demonstrated.",
        ),
    ),
    't18-counterevidence-failure-analysis': (
        'assessed',
        'real-data',
        (
            "append",
            "The fifty-first independent reading at commit 042dfe9 scored the topic assessed on "
            "public data, and the self record now states the reading. The reading named what the "
            "laboratory does not reach, that the assay-limit and alternative-mechanism exercises are "
            "constructed and that actual failed biological candidate nominations are not supplied."
        ),
    ),
}

def split_blocks(lines: list[str]) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Split the file into its preamble and its ordered topic blocks.

    The blocks are handled separately and the file is reassembled afterwards,
    because inserting a line into one block shifts the line numbers of every
    block after it.
    """
    preamble: list[str] = []
    blocks: list[tuple[str, list[str]]] = []
    current_id: str | None = None
    current: list[str] = []

    for line in lines:
        if line.startswith("- topic_id: "):
            if current_id is not None:
                blocks.append((current_id, current))
            current_id = line[len("- topic_id: ") :].strip()
            current = [line]
            continue
        if current_id is None:
            preamble.append(line)
        else:
            current.append(line)

    if current_id is not None:
        blocks.append((current_id, current))
    return preamble, blocks


def edit_block(topic_id: str, block: list[str]) -> list[str]:
    """Apply one raise to one topic block."""
    depth, run_basis, edit = RAISES[topic_id]
    block = list(block)

    for index, line in enumerate(block):
        if line.startswith("  depth: "):
            block[index] = f"  depth: {depth}"
            break
    else:
        raise SystemExit(f"{topic_id}: no depth line to edit")

    basis = next(
        (index for index, line in enumerate(block) if line.startswith("  run_basis: ")),
        None,
    )
    if basis is None:
        depth_line = next(
            index for index, line in enumerate(block) if line.startswith("  depth: ")
        )
        block.insert(depth_line + 1, f"  run_basis: {run_basis}")
    else:
        block[basis] = f"  run_basis: {run_basis}"

    note_line = next(
        (index for index, line in enumerate(block) if line.startswith("  note: ")),
        None,
    )
    if note_line is None:
        raise SystemExit(f"{topic_id}: no note line to edit")
    raw = block[note_line][len("  note: ") :]
    # A note is either a plain scalar or a double-quoted one, and a quoted one has
    # to keep its closing quote at the end of the line.
    quoted = raw.startswith('"') and raw.endswith('"')
    note = raw[1:-1] if quoted else raw
    if edit[0] == "append":
        # The appended text is written without a leading space, because the
        # table is generated as source lines and the space between two words
        # would not survive the split. The separator is added here instead.
        addition = " " + edit[1].lstrip()
        # The script is a migration tool and may be run again on a tree that
        # already carries a raise, so an addition that is already in the note
        # is left alone rather than written twice.
        if addition.strip()[:60] in note:
            print(f"{topic_id}: already raised")
            return block
        note = note + addition
    else:
        if edit[1] not in note:
            # A raise that has already been applied leaves the replacement in
            # place and the replaced text gone, so this is the second run.
            if edit[2].strip()[:60] in note:
                print(f"{topic_id}: already raised")
                return block
            raise SystemExit(f"{topic_id}: the note does not contain the replaced text")
        note = note.replace(edit[1], edit[2])
    block[note_line] = f'  note: "{note}"' if quoted else f"  note: {note}"

    print(f"{topic_id}: depth {depth}, run basis {run_basis}")
    return block


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    arguments = parser.parse_args()

    lines = SYSTEM.read_text(encoding="utf-8").splitlines()
    preamble, blocks = split_blocks(lines)
    known = {topic_id for topic_id, _ in blocks}
    missing = [topic for topic in RAISES if topic not in known]
    if missing:
        print(f"topics not found: {missing}", file=sys.stderr)
        return 1

    updated: list[str] = list(preamble)
    for topic_id, block in blocks:
        updated.extend(edit_block(topic_id, block) if topic_id in RAISES else block)

    if arguments.write:
        SYSTEM.write_text("\n".join(updated) + "\n", encoding="utf-8")
        print(f"wrote {len(RAISES)} raises to {SYSTEM.name}")
    else:
        print("re-run with --write to apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
