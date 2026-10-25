# EGFR structure evidence lab

Two offline commands read three deposited crystal structures of the human EGFR
kinase domain and treat them as evidence rather than as answers. **No structure is
prepared, protonated, minimised or docked, and no pocket-prediction method is run.**

```bash
python labs/egfr_structures/inspect_state.py show     # what each file says, and how a site is defined
python labs/egfr_structures/inspect_state.py check
python labs/egfr_structures/inspect_complex.py show   # contacts, interactions and poses
python labs/egfr_structures/inspect_complex.py check
```

Python 3.11 or newer and NumPy. No network access once the files are present.

## The three files

| Entry | Ligand | Why it is here |
| --- | --- | --- |
| 1M17 | erlotinib (AQ4) | The reference frame for every superposition |
| 4HJO | erlotinib (AQ4) | The same ligand in a kinase domain its depositors call inactive |
| 1XKK | lapatinib (FMM) | A different quinazoline with a larger substituent |

They were downloaded on 2026-09-11 as gzipped PDBx/mmCIF from the RCSB PDB file
service and are stored decompressed in `structures/`, so every category the labs
read can be opened in a text editor. Decompression is the only step. The manifest
`entries.json` records each source URL, byte size, PDB entry identifier, deposition
date and latest deposited revision. Both checks validate these fields before
reporting a verdict. They do not certify byte-for-byte identity. PDB archive data
files are released under CC0 1.0. wwPDB asks that the original authors be credited,
and both commands print each entry's primary citation.

## What the two commands teach

`inspect_state.py` reads each file as a record of an experiment: method,
resolution, R-work and R-free, the construct that was crystallised, the residues
the model does not contain, and the depositor's numbering. The hinge methionine is
author residue 769 in two files and 793 in the third, so every cross-entry
comparison maps residues to UniProt P00533 through the file's own alignment, and
the check confirms five landmark residues after mapping. One conformational
descriptor, the Lys745 NZ to Glu762 CD distance, is computed and set beside the
depositors' own label. The binding site is then reported at 4, 5 and 6 A and grows
at every step, and an axis-aligned docking box drawn around one ligand is shown to
change volume in another frame and to miss part of a different ligand.

`inspect_complex.py` separates a contact, which is geometry, from an interaction,
which adds an assumption about protonation. Donor and acceptor roles are declared
in the manifest because no file models a hydrogen, and the check verifies every
declared role against the ligand's own bonding. It lists water-mediated contacts,
builds a residue interaction fingerprint per complex, compares the two erlotinib
poses atom by atom, places every ligand rigidly into every receptor state, and
finally perturbs the 1M17 crystal pose in two declared rigid motions. Those two
**constructed** poses are labelled wherever they are printed. One passes a 2 A RMSD
convention and loses the hinge contact; the other passes it, keeps the hinge
contact and clashes.

## Observed values

Computed on 2026-09-11 on an Apple arm64 machine with Python 3.11.15 and NumPy
2.4.6. The values are deterministic functions of the three files and the declared
cutoffs.

| Quantity | 1M17 | 4HJO | 1XKK |
| --- | --- | --- | --- |
| Resolution (A) | 2.60 | 2.75 | 2.40 |
| Lys745 NZ to Glu762 CD (A) | 3.71 | 14.41 | 13.73 |
| Site residues at 4 / 5 / 6 A | 15 / 20 / 25 | 17 / 20 / 26 | 23 / 28 / 37 |
| Waters modelled | 20 | 34 | 77 |

The two erlotinib poses differ by 1.65 A RMSD over 29 atoms after superposition on
20 site C-alpha atoms, 0.80 A in the quinazoline core and 1.96 A elsewhere, with
one atom moving 3.55 A.

The parser uses only the standard library. On 2026-09-11 it was cross-checked
against gemmi 0.7.5 on all three files: identical atom sets, coordinates, B-factors
and occupancies (2546, 2264 and 2376 atoms), identical refinement values, titles
and sequence alignments, and identical unobserved residues inside the aligned
segment.

## What the checks lock

Sixteen state checks and fifteen complex checks. A missing or nonregular file,
byte-size mismatch, wrong entry identifier or mismatched deposition or revision
stops both commands before any verdict. Tests are in
`labs/tests/test_egfr_structures.py`. Known-bad edits include truncation, a wrong
accession or revision, comparing residues by author number, declaring a role the ligand's bonding contradicts, and
protonating the hinge-facing nitrogen, which turns the same 2.70 A pair from a
possible hydrogen bond into an impossible one without moving an atom.

## What this lab does not show

Three structures of one protein cannot define an allosteric or transient pocket,
because every ligand here sits in the ATP site. A clash in a rigid placement says a
pose does not fit that receptor conformation, not that the ligand cannot bind. The
distance descriptor agrees with a label; it does not assign a state. None of the
numbers above is a binding affinity.

The bilingual lab page is at `site/src/content/docs/labs/egfr-structure-evidence.mdx`
with its Chinese edition under `zh-cn/`.
