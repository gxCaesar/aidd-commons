# Local-document PaperQA smoke test

Status, 10 September 2026: the five-question local integration completed, and
both notebook editions execute in offline mode. No human grading was collected.
A CPU-only execution of the optional live branch failed while embedding the first
document under its 150-second indexing limit; no new answer was produced. The
partial notebook and error were retained. A separate CPU execution copy then
completed all 12 code cells in 774.12 seconds and produced one fresh answer.
It used four model threads, zero SDK retries, 600 seconds per document and
2400 seconds per question. Models, texts, the question and retrieval settings
were unchanged. This validates that execution copy, not the default notebook's
unchanged 150/600-second CPU limits. The new answer correctly states “over 110
formats”, but adds overly broad reliability claims and overstates the scope of
a conversion test. It is not a fully supported answer or an accuracy benchmark.
The new output remains separate from the original five saved teaching answers.

Update, 10 September 2026: the notebooks now name that budget instead of hiding
it. `EXECUTION_PROFILE` selects `as-observed`, the unchanged limits of the
observed batch, or `cpu-extended`, the limits of that accepted execution copy.
A profile sets threads and timeouts only. `apply_runtime_budget` compares the
settings before and after with transport limits removed and raises if any other
field moved, and a test asserts that `cpu-extended` reproduces the accepted
copy's settings exactly. Naming the budget does not make it a validated default:
no unattended CPU run of the public notebook has been accepted.

Start with the [English notebook](paperqa_local_tutorial.ipynb) or
[Chinese notebook](paperqa_local_tutorial.zh-CN.ipynb). Each is standalone: upload
to Colab or open in Jupyter, then run top to bottom. The default lesson needs no
API key, network request, model download or GPU. It reads the real example,
checks source copies, exposes a citation-support error and provides an independent
exercise. Student reports go into a fresh folder, separate from observed answers.

`reviewed-example.json` contains the unedited answers, attributed source texts,
retrieved evidence and assistant source-review notes. It excludes private run
control files. All four answerable questions have supported core answers, but
the Open Babel utilities answer misattributes a function in its extra prose.
The unsupported joint-split question receives a refusal backed by only one
retrieved Open Babel chunk, not proof of absence across the full literature.

Observed indexing and answering took 109.368 seconds, excluding setup/downloads.
Sampled GPU memory peaked at 7.334 GB on an RTX A6000; Python peak RSS was
240.3 MB, excluding the model server. Eighteen observed Python socket events
used only the loopback model endpoint, with none denied. This is not an OS-level
network-isolation guarantee or a minimum resource requirement.

The test asks four simple factual questions and one deliberately unsupported
joint-protocol question about two supplied articles. It tests whether the
local integration can index text, produce cited answers and expose insufficient
evidence. It does not reproduce an autonomous literature-search agent, measure
SOTA performance or test generalization to unseen papers. The models may have
seen these public papers during pretraining.

## Inputs and reuse

`corpus.json` defines the document identities, questions and review references.
Reference answers and source anchors are not sent to the model. Only the question
text enters `Docs.aquery`; indexed material is extracted from the papers.

- O'Boyle et al. (2011), *Open Babel: An open chemical toolbox*,
  [PMC3198950](https://pmc.ncbi.nlm.nih.gov/articles/PMC3198950/),
  [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/).
- Du et al. (2023), *CMMS-GCL: cross-modality metabolic stability prediction with
  graph contrastive learning*,
  [PMC10457661](https://pmc.ncbi.nlm.nih.gov/articles/PMC10457661/),
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

The source XML is retrieved through Europe PMC. Preparation checks article
identity, the specific licence URL and each positive question's source quote.
It extracts abstract/body paragraphs and headings, excluding the reference list.
This is a text-only conversion, not a test of PDF layout, figures or complete
table recovery. Full attribution remains in the text header and corpus file.

## Bounded execution recipe

The tested integration used Python 3.13.13 with `paper-qa[pypdf]==2026.8.12`,
Ollama 0.33.3, `qwen3:8b` and `nomic-embed-text:v1.5`. Model weights, software
and article retrieval need network access during setup. Inference uses one
loopback endpoint, `127.0.0.1:11434`, with Ollama cloud features disabled.

The existing local profile is checked before use. For this smoke run, the helper
uses `ollama_chat/` for explicit `think=False`, temperature 0, and at most 1024
generated tokens per chat call. Retrieval uses four chunks, with at most three
answer sources. The server context limit is 8192 tokens and model requests are
serial. These choices are fixed before observing any answers. The effective
settings are saved with the run, rather than silently changing the base profile.
In `run_smoke.py` each document indexing call has a 150-second limit and each
question a 600-second limit; these are unchanged. The observed batch also had a
3600-second inference ceiling; apply an appropriate outer process limit when
running that batch independently. The notebooks reach the same two limits
through `EXECUTION_PROFILE = "as-observed"`, and their `cpu-extended` profile
raises them to 600 and 2400 seconds while adding four model threads, zero SDK
retries and a 900-second chat limit. In the accepted CPU run the embedding
timeout was not forwarded into the HTTP call, so the per-document limit is the
real outer bound. That run changed threads and time limits together and cannot
separate their effects.
Exceptions and handled termination preserve a failed summary and
partial answers; an uncatchable process kill may still prevent final writes.

From the repository root, **after** installing the specified environment and
starting the configured local server:

```bash
python labs/paperqa_local/run_smoke.py prepare --data tmp/paperqa-data-01
python labs/paperqa_local/run_smoke.py run \
  --data tmp/paperqa-data-01 --output tmp/paperqa-results-01
```

Both commands require fresh destination directories; existing outputs are not
overwritten. The preparation command makes public web requests. The inference
process installs a Python socket audit hook that rejects non-loopback endpoints.
It is not an operating-system sandbox and does not establish network isolation
of native libraries or the separate Ollama server. Every fresh run should
inspect its own recorded network events and server configuration.

`answers.json` preserves answers, cited references, retrieved source text and
model summaries separately. `summary.json` records execution completion only;
`human_review` remains `not_run`. `network-events.json` records the Python
network operations observed by the hook. A nonempty answer and a model's own
success flag are not proof of correct reasoning or citation support.

## Source review and editable notebook

For each factual question, compare the answer's proposition and qualifiers with
the named source passage, then check whether its actual citation supports it.
For the unsupported question, distinguish a justified insufficient-information
answer from an invented split. Keep incorrect answers, empty outputs, truncation,
refusals and execution errors. Do not regenerate until a favourable answer appears.

The five questions are teaching cases from two supplied documents, not five
independent scientific samples. No aggregate benchmark score is computed. The
bilingual notebooks expose indexing, question answering, source inspection and
an independent exercise as separate editable cells. Fresh inference is explicitly
opt-in and needs an already prepared local server; no model is installed or
called by the default lesson. The observed five-question batch used `run_smoke.py`,
not the notebook's live branch. An altered copy of a real evidence chunk is
rejected in the notebook test; this tests copy fidelity, not semantic reasoning.

To rebuild the two editions after an editorial change, run
`python labs/paperqa_local/build_notebooks.py` with `nbformat` available. The builder
uses only the curated example and shared source-visible helpers, not private run
folders. Both editions have identical executable cells and distinct translated prose.
