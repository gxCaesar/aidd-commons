"""Prepare licensed text, then run a bounded local-document PaperQA smoke test.

Preparation uses the internet. Inference permits Python socket operations only
to the loopback Ollama endpoint. This guard is not an operating-system sandbox.
Reference answers never enter a model call; human review is separate.
"""

import argparse
import asyncio
import copy
import importlib.metadata
import json
import os
import resource
import signal
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/agents"))
from check_local_profile import load_profile, validate_profile  # noqa: E402

CORPUS = Path(__file__).with_name("corpus.json")
PROFILE = ROOT / "configs/scientific-agents/paperqa-local.json"


def article_text(xml: str, doc: dict) -> str:
    tree = ET.fromstring(xml)
    text = lambda element: " ".join("".join(element.itertext()).split())  # noqa: E731
    title = tree.find("./front/article-meta/title-group/article-title")
    pmcids = {
        "PMC" + (item.text or "").removeprefix("PMC")
        for item in tree.findall("./front/article-meta/article-id")
        if item.get("pub-id-type") in {"pmc", "pmcid"}
    }
    if title is None or text(title) != doc["title"] or doc["pmcid"] not in pmcids:
        raise ValueError("Article identity does not match the selected corpus.")
    licenses = {
        value.replace("http://", "https://").rstrip("/")
        for item in tree.findall("./front/article-meta/permissions/license//*")
        for value in item.attrib.values()
        if "creativecommons.org/licenses/" in value
    }
    expected = doc["license_url"].rstrip("/")
    allowed = {
        "https://creativecommons.org/licenses/by/2.0",
        "https://creativecommons.org/licenses/by/4.0",
    }
    if expected not in allowed or expected not in licenses:
        raise ValueError("Article license does not match the approved CC BY corpus.")
    sections = tree.findall("./front/article-meta/abstract") + tree.findall("./body")
    paragraphs = [
        text(item) for section in sections for item in section.iter() if item.tag in {"title", "p"}
    ]
    return "\n\n".join([doc["title"], doc["citation"], doc["license_url"], *paragraphs]) + "\n"


def inference_questions(questions: list[dict]) -> list[tuple[str, str]]:
    return [(item["id"], item["question"]) for item in questions]


def smoke_settings(profile: dict) -> dict:
    validate_profile(profile)
    settings = copy.deepcopy(profile["settings"])
    # Use the documented Ollama chat transport for explicit thinking control.
    roles = [
        (settings, "llm"),
        (settings, "summary_llm"),
        (settings["agent"], "agent_llm"),
        (settings["parsing"], "enrichment_llm"),
    ]
    for section, key in roles:
        model = section[key].replace("ollama/", "ollama_chat/", 1)
        section[key] = model
        entry = section[key + "_config"]["model_list"][0]
        entry["model_name"] = model
        entry["litellm_params"].update(model=model, temperature=0, max_tokens=1024, think=False)
    settings["answer"].update(evidence_k=4, answer_max_sources=3)
    return settings


def install_network_guard(events: list[dict]) -> None:
    def audit(event, args):
        if event == "socket.getaddrinfo":
            address = args[:2]
        elif event == "socket.connect":
            address = args[1]
        elif event == "socket.sendto":
            address = args[-1]
        else:
            return
        allowed = (
            isinstance(address, tuple)
            and len(address) >= 2
            and address[0] in {"127.0.0.1", "localhost", "::1"}
            and str(address[1]) == "11434"
        )
        events.append({"event": event, "address": str(address), "allowed": allowed})
        if not allowed:
            raise PermissionError("External network operation refused during local inference.")

    sys.addaudithook(audit)


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def prepare(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    corpus = json.loads(CORPUS.read_text())
    for doc in corpus["documents"]:
        with urllib.request.urlopen(doc["url"], timeout=60) as response:
            xml = response.read(5_000_001)
        if len(xml) > 5_000_000:
            raise ValueError("Unexpectedly large article response.")
        extracted = article_text(xml.decode("utf-8"), doc)
        for question in corpus["questions"]:
            if question["source_quote"] and doc["id"] in question["expected_document_ids"]:
                if question["source_quote"] not in extracted:
                    raise ValueError(f"Source anchor missing for {question['id']}")
        (destination / f"{doc['id']}.xml").write_bytes(xml)
        (destination / f"{doc['id']}.txt").write_text(extracted, encoding="utf-8")
        print(f"PREPARED {doc['id']}: {len(extracted)} characters; {doc['license']}", flush=True)


async def run(data: Path, output: Path) -> None:
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    profile = load_profile(PROFILE)
    corpus = json.loads(CORPUS.read_text())
    for doc in corpus["documents"]:
        if not (data / f"{doc['id']}.txt").is_file():
            raise FileNotFoundError(f"Prepared text missing: {doc['id']}")
    if importlib.metadata.version("paper-qa") != profile["paperqa_version"]:
        raise ValueError("Installed paper-qa version does not match the selected profile.")
    output.mkdir(parents=True, exist_ok=False)
    os.environ.update(
        LITELLM_LOCAL_MODEL_COST_MAP="True",
        NO_PROXY="127.0.0.1,localhost,::1",
        no_proxy="127.0.0.1,localhost,::1",
        HF_HUB_OFFLINE="1",
    )
    events, answers = [], []
    started = time.monotonic()
    effective = smoke_settings(profile)
    write_json(output / "effective-settings.json", effective)
    install_network_guard(events)
    try:
        from lmi import LiteLLMEmbeddingModel
        from paperqa import Docs, Settings

        settings = Settings(**effective)
        embedding = LiteLLMEmbeddingModel(
            name=settings.embedding, ndim=768, config=settings.embedding_config
        )
        llm, summary = settings.get_llm(), settings.get_summary_llm()
        docs = Docs()
        for doc in corpus["documents"]:
            added = await asyncio.wait_for(
                docs.aadd(
                    data / f"{doc['id']}.txt",
                    citation=doc["citation"],
                    docname=doc["id"],
                    dockey=doc["id"],
                    title=doc["title"],
                    settings=settings,
                    llm_model=llm,
                    embedding_model=embedding,
                ),
                timeout=150,
            )
            if added is None:
                raise RuntimeError(f"Document was not indexed: {doc['id']}")
            print(f"INDEXED {doc['id']}", flush=True)
        for question_id, question in inference_questions(corpus["questions"]):
            question_start = time.monotonic()
            session = await asyncio.wait_for(
                docs.aquery(
                    question,
                    settings=settings,
                    llm_model=llm,
                    summary_llm_model=summary,
                    embedding_model=embedding,
                ),
                timeout=600,
            )
            row = {
                "id": question_id,
                "question": question,
                "answer": session.answer,
                "references": session.references,
                "model_reported_success": session.has_successful_answer,
                "elapsed_seconds": round(time.monotonic() - question_start, 3),
                "contexts": [
                    {
                        "document_id": context.text.doc.dockey,
                        "chunk_name": context.text.name,
                        "source_text": context.text.text,
                        "summary": context.context,
                        "relevance": context.score,
                        "cited": context.id in session.used_contexts,
                    }
                    for context in session.contexts
                ],
                "human_review": "not_run",
            }
            answers.append(row)
            write_json(output / "answers.json", answers)
            print(f"ANSWER {question_id}: {session.answer}", flush=True)
        if any(not event["allowed"] for event in events):
            raise RuntimeError(
                "External network attempts were blocked; inspect network-events.json."
            )
        write_json(
            output / "summary.json",
            {
                "execution": "completed",
                "question_count": len(answers),
                "human_review": "not_run",
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "python_peak_rss_mb": round(
                    resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                    * (1 if sys.platform == "darwin" else 1024)
                    / 1_000_000,
                    1,
                ),
                "memory_scope": "Linux Python process only; excludes Ollama and GPU",
            },
        )
    except BaseException as exc:
        write_json(
            output / "summary.json",
            {
                "execution": "failed",
                "question_count": len(answers),
                "human_review": "not_run",
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
        raise
    finally:
        write_json(output / "network-events.json", events)


def terminate_run(signum, frame) -> None:
    raise TimeoutError("Inference received SIGTERM; preserve partial outputs and stop.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("--data", type=Path, default=ROOT / "tmp/paperqa-data")
    parser.add_argument("--output", type=Path, default=ROOT / "tmp/paperqa-results")
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.data)
    else:
        signal.signal(signal.SIGTERM, terminate_run)
        asyncio.run(run(args.data, args.output))


if __name__ == "__main__":
    main()
