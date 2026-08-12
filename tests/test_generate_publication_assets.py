"""Tests for deterministic benchmark publication assets."""

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from scripts.generate_publication_assets import VERDICTS, generate, summarize_result

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "benchmarks"
    / "2026-08-11"
    / "result-public.json"
)


def _document():
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def test_source_totals_and_summary_are_preserved():
    providers, tasks = summarize_result(_document())

    assert len(providers) == 5
    assert len(tasks) == 12
    assert {verdict: sum(row[verdict] for row in providers) for verdict in VERDICTS} == {
        "SOLVED": 107,
        "FALSE_SUCCESS": 27,
        "FAILED_HONEST": 30,
        "GUARD_VIOLATION": 16,
    }
    assert sum(row["invalid"] for row in providers) == 0
    assert [row["episodes"] for row in tasks] == [15] * 12


def test_generated_tables_have_exact_counts_rates_and_durations(tmp_path):
    generate(SOURCE, tmp_path, create_png=False)
    provider_rows = list(csv.DictReader((tmp_path / "provider-results.csv").open(encoding="utf-8")))
    task_rows = list(csv.DictReader((tmp_path / "task-results.csv").open(encoding="utf-8")))

    assert len(provider_rows) == 6
    assert len(task_rows) == 13
    assert provider_rows[0]["requested_provider_model"] == "codex / gpt-5.5"
    assert provider_rows[0]["SOLVED"] == "23"
    assert provider_rows[0]["FALSE_SUCCESS"] == "4"
    assert provider_rows[0]["false_success_rate"] == "14.8%"
    assert provider_rows[0]["guard_rate"] == "8.3%"
    assert provider_rows[0]["median_duration_s"] == "36.65"
    assert provider_rows[0]["p95_duration_s"] == "71.5"
    assert provider_rows[-1]["episodes"] == "180"
    assert provider_rows[-1]["SOLVED"] == "107"
    assert provider_rows[-1]["FALSE_SUCCESS"] == "27"
    assert provider_rows[-1]["guard_rate"] == "8.9%"
    assert task_rows[1]["task_id"] == "basic-002-palindrome"
    assert task_rows[1]["FALSE_SUCCESS"] == "14"
    assert task_rows[1]["false_success_rate"] == "93.3%"
    assert task_rows[-1]["GUARD_VIOLATION"] == "16"
    assert "Athena CLI" in (tmp_path / "provider-results.md").read_text(encoding="utf-8")
    assert "palindrome e slugify" in (tmp_path / "task-results.md").read_text(encoding="utf-8")


def test_svg_content_checksums_and_generation_are_deterministic(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    generate(SOURCE, first, create_png=False)
    generate(SOURCE, second, create_png=False)

    for name in ("provider-outcomes.svg", "task-outcomes.svg"):
        first_svg = (first / name).read_bytes()
        assert first_svg == (second / name).read_bytes()
        text = first_svg.decode("utf-8")
        assert "<title id=" in text
        assert "<desc id=" in text
        assert "SOLVED" in text
        assert "FALSE_SUCCESS" in text
        assert "O bucket inválido é zero" in text
        assert "url(#solved-pattern)" in text
        assert sum("<text " in line and "Run ID:" in line for line in text.splitlines()) == 1
    checksum_lines = (first / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert len(checksum_lines) == 6
    for line in checksum_lines:
        digest, name = line.split("  ")
        assert digest == hashlib.sha256((first / name).read_bytes()).hexdigest()


def test_generated_asset_tables_match_public_source_read_only():
    """Independently compare committed table counts with the public episode records."""
    document = _document()
    asset_dir = SOURCE.parent / "publication-assets"
    provider_rows = list(csv.DictReader((asset_dir / "provider-results.csv").open(encoding="utf-8")))[:-1]
    task_rows = list(csv.DictReader((asset_dir / "task-results.csv").open(encoding="utf-8")))[:-1]

    for row in provider_rows:
        provider, model = row["requested_provider_model"].split(" / ", maxsplit=1)
        verdicts = Counter(
            episode["verdict"]
            for episode in document["episodes"]
            if episode["provider"] == provider and episode["model"] == model
        )
        assert row["episodes"] == "36"
        assert all(row[verdict] == str(verdicts[verdict]) for verdict in VERDICTS)
        assert row["invalid"] == "0"
    for row in task_rows:
        verdicts = Counter(
            episode["verdict"] for episode in document["episodes"] if episode["task_id"] == row["task_id"]
        )
        assert row["episodes"] == "15"
        assert all(row[verdict] == str(verdicts[verdict]) for verdict in VERDICTS)
        assert row["invalid"] == "0"
