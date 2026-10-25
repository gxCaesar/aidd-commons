# rMD17 system-state teaching lab

This lab implements a small, frozen teaching baseline for revised MD17 v4. It uses only the
`energies` target and pair-distance features built from `nuclear_charges` and `coords`. Forces,
`old_energies`, and `old_forces` are schema validation inputs only; they never enter a model.

The following development commands are for a fresh workspace only. This
completed author workspace retains the one-time marker and completed output;
do not use it to download, reconstruct, or rerun the study. The pretest and
locked-evaluation paths reject after the completed paired result, and a further
development download would not add evidence to it.

Run the fresh-workspace commands from the repository root:

```bash
uv run python labs/rmd17_system_state/run_lab.py validate-protocol
uv run python labs/rmd17_system_state/run_lab.py download-development
uv run python labs/rmd17_system_state/run_lab.py pretest
```

`download-development` retrieves only ethanol and malonaldehyde. The observed Figshare v4 files
for these systems are 67.2 MB each (decimal MB). The public aggregate is written to
`labs/rmd17_system_state/development-summary.json`; detailed local evidence and downloaded data
stay in ignored canonical directories below this lab.

The split first stably orders frames by original index, then samples 1,000 ranks into 600 train,
200 validation, and 200 evaluation rows. This is an original-index ordering challenge, not an
independence guarantee: molecular-dynamics frames remain time-correlated, and within-system
development evidence does not establish cross-system generalization.

The five source-provided train/test CSV pairs are not used. The source record does not identify
their indices as a temporal order or document their mapping to the version-4 NPZ rows, so they do
not silently replace this lab's declared `old_indices` procedure.

The historical development record remains ethanol and malonaldehyde. The paired
benzene and uracil evaluation completed once on 2026-09-08 with the
development-selected frozen alpha 100. Each system uses 600 training, 200
validation, and 200 evaluation frames from the frozen 1,000-frame selection.

[`locked-summary.json`](locked-summary.json) is the sanitized public aggregate,
separate from the unchanged development summary. Its projection command reads
only completed metrics and does not download, refit, or evaluate:

```bash
uv run python labs/rmd17_system_state/export_locked_summary.py
```

| System  | Ridge MAE (kcal/mol) | Train-mean MAE (kcal/mol) |
| ------- | -------------------: | ------------------------: |
| benzene |   1.6022730996053722 |        2.2343735356479013 |
| uracil  |   3.1238744298947863 |         3.720448133704194 |

Ridge is lower than the train-mean control in both within-system evaluations.
This is not zero-shot transfer to an unseen molecular system, a force-model
result, or a frame-pooled generalization claim: the reporting unit is the two
systems, and no confidence interval or p value is reported. The locked artifact
does not retain per-frame Ridge predictions, so post-run verification
independently recomputed the train-mean baselines and target ranges but not the
Ridge metrics. The one-time marker remains and must not be removed or rerun.
