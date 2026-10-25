"""The data contract: what the lab reads, what it admits and what it refuses.

The tests that need the real published objects skip when the cache is
absent, so they run on a machine that has fetched them and are skipped on a
machine that has not. The rest run against the synthetic snapshot in
`conftest.py`, which has the same shape as the published files.
"""

from __future__ import annotations

import gzip
from pathlib import Path

import pytest
from aidd_commons.rosetta_cross_modality.data import (
    DataContractError,
    download_and_cache_snapshot,
    load_cached_dataset,
    validate_cached_files,
)
from aidd_commons.rosetta_cross_modality.protocol import (
    ContractError,
    default_contract_path,
    load_contract,
)

from .conftest import build_snapshot, fetcher_for, write_contract

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/rosetta_cross_modality"
CONTRACT_PATH = LAB / "protocol.json"
CACHE_DIR = ROOT / ".cache/rosetta_cross_modality"

REAL_CACHE_PRESENT = all(
    (CACHE_DIR / name).is_file()
    for name in (
        "replicate_level_l1k.csv.gz",
        "replicate_level_cp_normalized_variable_selected.csv.gz",
    )
)
requires_real_cache = pytest.mark.skipif(
    not REAL_CACHE_PRESENT,
    reason="the published objects are not cached; run "
    "'python labs/rosetta_cross_modality/run_lab.py download' to fetch them",
)


def _contract_for(snapshot, root: Path):
    path = write_contract(root / "protocol.json", snapshot.contract_document)
    return load_contract(path)


def test_the_committed_contract_loads_and_describes_the_published_objects() -> None:
    contract = load_contract(CONTRACT_PATH)
    assert contract.protocol_id == "cpg0003-rosetta-luad-cross-modality-v1"
    assert contract.study_id == "cpg0003-rosetta"
    assert contract.batch_id == "LUAD-BBBC041-Caicedo"
    assert contract.transcriptome_file.byte_length == 11448797
    assert contract.imaging_file.byte_length == 15858878
    assert contract.transcriptome_file.s3_etag == "cca1d0129f0a8f94f322d0fded461225"
    assert contract.imaging_file.s3_etag == "c79982a1d6eca9480e707c8d64c50b43"
    assert contract.seed == 20261021
    assert contract.outer_folds == 5
    assert contract.ridge_alphas == (1.0, 10.0, 100.0, 1000.0, 10000.0)


def test_the_default_contract_path_points_at_the_committed_contract() -> None:
    assert default_contract_path() == CONTRACT_PATH


def test_a_missing_contract_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ContractError, match="could not read the contract"):
        load_contract(tmp_path / "absent.json")


def test_the_download_refuses_a_payload_that_does_not_match_the_declared_length(
    tmp_path: Path,
) -> None:
    snapshot = build_snapshot()
    contract = _contract_for(snapshot, tmp_path)
    contract = type(contract)(**{**contract.__dict__, "files": contract.files})
    shortened = contract.files[0]
    from dataclasses import replace

    broken = replace(shortened, byte_length=shortened.byte_length + 1)
    contract = replace(contract, files=(broken, contract.files[1]))
    with pytest.raises(DataContractError, match="the contract declares"):
        download_and_cache_snapshot(tmp_path / "cache", contract, fetch=fetcher_for(snapshot))
    assert not (tmp_path / "cache" / shortened.filename).exists()


def test_the_download_refuses_a_payload_whose_digest_does_not_match(tmp_path: Path) -> None:
    snapshot = build_snapshot()
    contract = _contract_for(snapshot, tmp_path)
    from dataclasses import replace

    broken = replace(contract.files[1], s3_etag="0" * 32)
    contract = replace(contract, files=(contract.files[0], broken))
    with pytest.raises(DataContractError, match="content ETag"):
        download_and_cache_snapshot(tmp_path / "cache", contract, fetch=fetcher_for(snapshot))
    assert not list(tmp_path.rglob("*.part"))


def test_a_valid_cache_is_not_downloaded_again(tmp_path: Path) -> None:
    snapshot = build_snapshot()
    contract = _contract_for(snapshot, tmp_path)
    cache = tmp_path / "cache"
    download_and_cache_snapshot(cache, contract, fetch=fetcher_for(snapshot))
    calls: list[str] = []

    def refuse(url: str, start: int):
        calls.append(url)
        raise AssertionError("a valid cache must not be downloaded again")

    download_and_cache_snapshot(cache, contract, fetch=refuse)
    assert calls == []


def test_an_interrupted_download_resumes_from_the_bytes_on_disk(tmp_path: Path) -> None:
    snapshot = build_snapshot()
    contract = _contract_for(snapshot, tmp_path)
    source = contract.files[0]
    cache = tmp_path / "cache"
    cache.mkdir(parents=True)
    partial = cache / f"{source.filename}.part"
    payload = snapshot.payloads[source.relative_path]
    partial.write_bytes(payload[: len(payload) // 2])
    seen: list[int] = []
    serve = fetcher_for(snapshot)

    def fetch(url: str, start: int):
        seen.append(start)
        return serve(url, start)

    download_and_cache_snapshot(cache, contract, fetch=fetch)
    assert seen[0] == len(payload) // 2
    assert (cache / source.filename).read_bytes() == payload


def test_a_cached_object_of_the_wrong_size_is_refused_on_load(tmp_path: Path) -> None:
    snapshot = build_snapshot()
    contract = _contract_for(snapshot, tmp_path)
    cache = tmp_path / "cache"
    download_and_cache_snapshot(cache, contract, fetch=fetcher_for(snapshot))
    (cache / contract.files[0].filename).write_bytes(b"truncated")
    with pytest.raises(DataContractError, match="does not match the contract"):
        validate_cached_files(cache, contract)


def test_the_admission_rule_joins_the_two_readouts_on_the_perturbation_name(
    tmp_path: Path,
) -> None:
    snapshot = build_snapshot()
    contract = _contract_for(snapshot, tmp_path)
    cache = tmp_path / "cache"
    download_and_cache_snapshot(cache, contract, fetch=fetcher_for(snapshot))
    dataset = load_cached_dataset(cache, contract)
    audit = dataset.audit
    assert audit.transcriptome_input_rows == 26
    assert audit.transcriptome_control_rows == 2
    assert audit.transcriptome_treated_rows == 24
    assert audit.imaging_input_rows == 32
    assert audit.imaging_control_rows == 8
    assert audit.imaging_treated_rows == 24
    assert audit.admitted_perturbations == 24
    assert audit.transcriptome_perturbations == 24
    assert audit.imaging_perturbations == 24
    assert audit.exclusion_counts == {}
    assert audit.batch_pure_perturbations == 24
    assert audit.batch_mixed_perturbations == 0
    assert len(dataset.transcriptome_features) == 4
    assert len(dataset.imaging_features) == 4
    assert all(
        perturbation.transcriptome.shape == (4,) for perturbation in dataset.perturbations
    )
    assert all(
        perturbation.imaging_replicates == 1 for perturbation in dataset.perturbations
    )


def test_a_feature_cell_that_is_not_a_number_stops_the_read(tmp_path: Path) -> None:
    snapshot = build_snapshot()
    contract = _contract_for(snapshot, tmp_path)
    cache = tmp_path / "cache"
    download_and_cache_snapshot(cache, contract, fetch=fetcher_for(snapshot))
    path = cache / contract.imaging_file.filename
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        text = handle.read()
    lines = text.splitlines()
    columns = lines[0].split(",")
    position = columns.index("Cells_AreaShape_Compactness")
    fields = lines[1].split(",")
    fields[position] = "not-a-number"
    lines[1] = ",".join(fields)
    path.write_bytes(gzip.compress("\n".join(lines).encode("utf-8")))
    # The contract's byte length no longer holds, so the file is refused as
    # a contract violation before the cell is even read.
    with pytest.raises(DataContractError, match="does not match the contract"):
        load_cached_dataset(cache, contract)


@requires_real_cache
def test_the_published_objects_carry_the_features_the_contract_declares() -> None:
    contract = load_contract(CONTRACT_PATH)
    dataset = load_cached_dataset(CACHE_DIR, contract)
    assert len(dataset.transcriptome_features) == 978
    assert len(dataset.imaging_features) == 291
    assert dataset.audit.admitted_perturbations == 528
    assert dataset.audit.transcriptome_plates == 16
    assert dataset.audit.imaging_plates == 16
    assert dataset.audit.imaging_batches == 2
    assert dataset.audit.batch_pure_perturbations == 509
    assert dataset.audit.batch_mixed_perturbations == 19
    assert dataset.audit.exclusion_counts == {"imaging_only_perturbation": 65}
