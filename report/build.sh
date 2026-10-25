#!/usr/bin/env bash
set -euo pipefail

report_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
project_root="$(dirname -- "$report_dir")"
work_dir="$project_root/tmp/pdfs"
output_dir="$project_root/output/pdf"
figures_dir="$report_dir/figures"

mkdir -p "$work_dir" "$output_dir"

export LC_ALL=C
export TZ=UTC
export SOURCE_DATE_EPOCH=1788480000
# A hash seed that does not change between runs, so that a set whose order depends on
# an unordered collection is still the same set twice.
export PYTHONHASHSEED=0

# The figures are drawn first, so the document is built from freshly produced artwork
# rather than from whatever happens to be on disk. The orchestrator pins its own epoch
# for the artwork, so the figure files it writes are the committed ones byte for byte,
# and it checks the caption manifests against the files on disk.
python_bin="$project_root/.venv/bin/python"
if [ ! -x "$python_bin" ]; then
  python_bin="$(command -v python3 || true)"
fi
if [ -z "$python_bin" ]; then
  printf '%s\n' "no Python interpreter was found for the figure build" >&2
  exit 1
fi
"$python_bin" "$figures_dir/build_figures.py"

# The document carries each figure's caption in the alt text, and that caption is
# generated from the same committed artefacts as the artwork. The copy is refreshed
# here, so the document cannot state a number the figures do not.
"$python_bin" "$project_root/scripts/report/sync-figure-captions.py"

# Pandoc resolves a relative resource path against the working directory, so the build
# runs from the report directory and the path to the figures stays relative to it. The
# entries cover a figure written as figures/out/<name>.pdf, as out/<name>.pdf and as
# <name>.pdf.
cd "$report_dir"

pandoc \
  "$report_dir/aidd-commons-living-report-v0.1.md" \
  --from=markdown+smart \
  --metadata-file="$report_dir/metadata.yaml" \
  --resource-path=".:figures:figures/out" \
  --bibliography="$report_dir/references.bib" \
  --citeproc \
  --top-level-division=chapter \
  --pdf-engine=xelatex \
  --output="$output_dir/aidd-commons-living-report-v0.1.pdf"

# The engine derives the document identifier from a clock reading, so two builds
# of the same source differ in that one trailer field. It is replaced with a
# digest of the document, which makes the build reproducible without changing
# anything a reader sees.
"$python_bin" "$report_dir/fix_pdf_id.py" "$output_dir/aidd-commons-living-report-v0.1.pdf"

printf '%s\n' "$output_dir/aidd-commons-living-report-v0.1.pdf"
