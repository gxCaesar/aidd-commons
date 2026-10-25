"""Check the narrow PaperQA local teaching profile without importing its SDK.

This is configuration validation, not a network sandbox or inference test.
Only the documented profile is supported; unknown overrides are rejected.
"""

import argparse
import json
import sys
from pathlib import Path


def router(model: str) -> dict:
    return {
        "model_list": [
            {
                "model_name": model,
                "litellm_params": {"model": model, "api_base": "http://127.0.0.1:11434"},
            }
        ]
    }


def validate_profile(profile: dict) -> None:
    """Reject missing roles, unknown keys, cloud routes and incompatible shapes."""
    if not isinstance(profile, dict) or not isinstance(profile.get("settings"), dict):
        raise ValueError("Expected a profile object containing settings.")
    chat = profile["settings"].get("llm")
    if chat not in ("ollama/qwen3:8b", "ollama/qwen3:14b"):
        raise ValueError("Only local qwen3:8b and qwen3:14b teaching profiles are supported.")
    embedding = "ollama/nomic-embed-text:v1.5"
    expected = {
        "paperqa_version": "2026.8.12",
        "embedding_ndim": 768,
        "settings": {
            "llm": chat,
            "llm_config": router(chat),
            "summary_llm": chat,
            "summary_llm_config": router(chat),
            "embedding": embedding,
            "embedding_config": router(embedding),
            "agent": {"agent_llm": chat, "agent_llm_config": router(chat)},
            "parsing": {
                "use_doc_details": False,
                "multimodal": False,
                "enrichment_llm": chat,
                "enrichment_llm_config": router(chat),
            },
            "answer": {
                "evidence_retrieval": True,
                "evidence_skip_summary": False,
                "get_evidence_if_no_contexts": True,
                "max_concurrent_requests": 1,
            },
        },
    }
    # JSON comparison distinguishes booleans from numbers as well as extra keys.
    if json.dumps(profile, sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise ValueError(
            "Profile differs from the supported local-only shape. Check every model role, "
            "loopback endpoint, parser flag and dimension; overrides/fallbacks are not allowed."
        )


def load_profile(path: str | Path) -> dict:
    profile = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_profile(profile)
    return profile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--settings", action="store_true", help="Print checked SDK settings JSON.")
    args = parser.parse_args()
    try:
        profile = load_profile(args.profile)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if args.settings:
        print(json.dumps(profile["settings"], indent=2))
    else:
        print("PASS: supported local-only configuration; SDK validation and inference not run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
