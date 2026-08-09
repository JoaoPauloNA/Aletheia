"""Suite loading and validation.

A task is a directory under suite/tasks/ with:

    task.json     manifest (id, category, prompt, scope, canary)
    seed/         files the agent sees (including VISIBLE tests)
    oracle/       hidden tests injected only at verification time

The agent never sees oracle/. The canary is a unique string embedded in the
oracle files; if it ever shows up in the agent's workspace before injection,
the task leaked and the episode is invalid.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

SUITE_DIR = Path(__file__).parent.parent / "suite" / "tasks"

REQUIRED_MANIFEST_FIELDS = ("id", "category", "prompt", "scope", "canary")
CATEGORIES = {"basic-correctness", "multi-file-regression", "honesty", "cheat-detection"}


@dataclass
class Task:
    id: str
    category: str
    prompt: str
    scope: list[str]          # path prefixes the agent is allowed to touch
    canary: str
    path: Path
    seed_dir: Path = field(init=False)
    oracle_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.seed_dir = self.path / "seed"
        self.oracle_dir = self.path / "oracle"


def load_task(task_dir: Path) -> Task:
    manifest_path = task_dir / "task.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    missing = [f for f in REQUIRED_MANIFEST_FIELDS if f not in manifest]
    if missing:
        raise ValueError(f"{task_dir.name}: manifest missing fields {missing}")
    task = Task(
        id=manifest["id"],
        category=manifest["category"],
        prompt=manifest["prompt"],
        scope=list(manifest["scope"]),
        canary=manifest["canary"],
        path=task_dir,
    )
    if task.category not in CATEGORIES:
        raise ValueError(f"{task.id}: unknown category '{task.category}'")
    if not task.seed_dir.is_dir():
        raise ValueError(f"{task.id}: missing seed/ directory")
    if not task.oracle_dir.is_dir():
        raise ValueError(f"{task.id}: missing oracle/ directory")
    # The canary must actually exist in the oracle, otherwise leak detection
    # is a no-op and we would never know.
    oracle_text = "".join(p.read_text(encoding="utf-8") for p in task.oracle_dir.rglob("*") if p.is_file())
    if task.canary not in oracle_text:
        raise ValueError(f"{task.id}: canary not found inside oracle/")
    return task


def load_suite(suite_dir: Path | None = None) -> list[Task]:
    root = suite_dir or SUITE_DIR
    tasks = [load_task(d) for d in sorted(root.iterdir()) if d.is_dir()]
    ids = [t.id for t in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate task ids in suite")
    return tasks
