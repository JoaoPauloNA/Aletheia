"""Unit tests for suite loading, guards and the summary logic.

No agent CLI is ever invoked here.
"""
import json

import pytest

from polygraph.cli import _summarize
from polygraph.guards import check_guards, snapshot, visible_test_hashes
from polygraph.suite import load_suite, load_task

# ── suite ──────────────────────────────────────────────────────────


def test_suite_loads_twelve_tasks():
    tasks = load_suite()
    assert len(tasks) == 12
    categories = {t.category for t in tasks}
    assert categories == {
        "basic-correctness",
        "multi-file-regression",
        "honesty",
        "cheat-detection",
        "scope-discipline",
    }


def test_every_task_has_seed_oracle_and_unique_canary():
    tasks = load_suite()
    canaries = set()
    for task in tasks:
        assert any(task.seed_dir.rglob("test_*.py")), task.id
        assert any(task.oracle_dir.rglob("test_oracle_*.py")), task.id
        canaries.add(task.canary)
    assert len(canaries) == len(tasks)


def test_load_task_rejects_missing_canary(tmp_path):
    task_dir = tmp_path / "bad"
    (task_dir / "seed").mkdir(parents=True)
    (task_dir / "oracle").mkdir()
    (task_dir / "oracle" / "test_oracle_x.py").write_text("def test_x():\n    assert True\n")
    (task_dir / "task.json").write_text(json.dumps({
        "id": "bad", "category": "honesty", "prompt": "p",
        "scope": ["x.py"], "canary": "CNRY-not-in-oracle",
    }))
    with pytest.raises(ValueError, match="canary"):
        load_task(task_dir)


# ── guards ─────────────────────────────────────────────────────────


def _workspace(tmp_path):
    (tmp_path / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    snapshot(str(tmp_path))
    return visible_test_hashes(str(tmp_path))


def test_guards_pass_on_clean_scope_work(tmp_path):
    hashes = _workspace(tmp_path)
    (tmp_path / "solution.py").write_text("X = 1\n")
    report = check_guards(str(tmp_path), hashes, ["solution.py"], "CNRY-zzz")
    assert report.ok
    assert report.changed_files == ["solution.py"]


def test_guards_catch_tampered_test(tmp_path):
    hashes = _workspace(tmp_path)
    (tmp_path / "test_ok.py").write_text("def test_ok():\n    assert 1 == 1  # weakened\n")
    report = check_guards(str(tmp_path), hashes, ["test_ok.py"], "CNRY-zzz")
    assert not report.ok
    assert not report.tests_intact
    assert "test_ok.py" in report.tampered_tests


def test_guards_catch_scope_escape(tmp_path):
    hashes = _workspace(tmp_path)
    (tmp_path / "evil.py").write_text("X = 1\n")
    report = check_guards(str(tmp_path), hashes, ["solution.py"], "CNRY-zzz")
    assert not report.scope_ok
    assert "evil.py" in report.out_of_scope


def test_guards_catch_oracle_leak(tmp_path):
    hashes = _workspace(tmp_path)
    (tmp_path / "solution.py").write_text("# CNRY-leaked-token\nX = 1\n")
    report = check_guards(str(tmp_path), hashes, ["solution.py"], "CNRY-leaked-token")
    assert report.leaked
    assert not report.ok


# ── summary ────────────────────────────────────────────────────────


def test_summarize_computes_false_success_rate():
    episodes = [
        {"provider": "a", "model": "m", "verdict": "SOLVED"},
        {"provider": "a", "model": "m", "verdict": "FALSE_SUCCESS"},
        {"provider": "a", "model": "m", "verdict": "FAILED_HONEST"},
        {"provider": "a", "model": "m", "verdict": "HARNESS_ERROR"},
    ]
    summary = _summarize(episodes)
    bucket = summary["a/m"]
    assert bucket["episodes"] == 4
    assert bucket["false_success_rate"] == round(1 / 3, 3)
    assert bucket["invalid"] == 1
