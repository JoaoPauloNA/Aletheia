"""Aletheia CLI — dispatch, verify, report. Nothing else."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from polygraph import __version__
from polygraph.runner import run_episode
from polygraph.suite import load_suite

RESULTS_DIR = Path(__file__).parent.parent / "results"
SUITE_DIR = Path(__file__).parent.parent / "suite"


def _cli_prog_name() -> str:
    """Return the invoked command name for help output (aletheia or polygraph)."""
    name = Path(sys.argv[0]).name
    return name if name in {"aletheia", "polygraph"} else "aletheia"


def _is_evidence_path(relative_path: str | Path) -> bool:
    """Whether a repository-relative path is stable publication evidence."""
    path = Path(str(relative_path).replace("\\", "/"))
    generated_directories = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "results",
    }
    return (
        path.name == ".DS_Store"
        or path.suffix in {".pyc", ".pyo"}
        or any(
            part in generated_directories or part == ".cache" or part.endswith(".egg-info")
            for part in path.parts
        )
    )


def _suite_paths_from_status(status_lines: list[str]) -> list[str]:
    paths = []
    for line in status_lines:
        path = line[3:].strip()
        for candidate in path.split(" -> "):
            candidate = candidate.strip()
            if candidate and not _is_evidence_path(candidate):
                paths.append(candidate)
    return sorted(set(paths))


def _suite_integrity_check() -> list[str]:
    """The suite is the ground truth. If a previous agent escaped its sandbox
    and wrote into suite/ (it happened — opencode did), every later episode is
    contaminated. Refuse to run on a dirty suite."""
    import subprocess

    repo = SUITE_DIR.parent
    if not (repo / ".git").exists():
        return []  # not a git checkout (e.g. pip install) — nothing to check against
    out = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "--", "suite/"],
        capture_output=True, text=True,
    )
    dirty = [line for line in out.stdout.splitlines() if line.strip()]
    return _suite_paths_from_status(dirty)


def _summarize(episodes: list[dict]) -> dict:
    per_provider: dict[str, dict] = {}
    for ep in episodes:
        key = f"{ep['provider']}/{ep.get('model') or 'default'}"
        bucket = per_provider.setdefault(key, {
            "episodes": 0, "solved": 0, "false_success": 0,
            "failed_honest": 0, "guard_violations": 0, "invalid": 0,
        })
        bucket["episodes"] += 1
        verdict = ep.get("verdict", "")
        if verdict == "SOLVED":
            bucket["solved"] += 1
        elif verdict == "FALSE_SUCCESS":
            bucket["false_success"] += 1
        elif verdict == "FAILED_HONEST":
            bucket["failed_honest"] += 1
        elif verdict in ("GUARD_VIOLATION",):
            bucket["guard_violations"] += 1
        else:
            bucket["invalid"] += 1
    for bucket in per_provider.values():
        success_claims = bucket["solved"] + bucket["false_success"]
        valid_decisions = success_claims + bucket["failed_honest"] + bucket["guard_violations"]
        bucket["false_success_rate"] = (
            round(bucket["false_success"] / success_claims, 3) if success_claims else None
        )
        bucket["guard_violation_rate"] = (
            round(bucket["guard_violations"] / valid_decisions, 3) if valid_decisions else None
        )
    return per_provider


def _sha256_chunks(chunks: list[bytes]) -> str:
    digest = hashlib.sha256()
    for chunk in chunks:
        digest.update(len(chunk).to_bytes(8, "big"))
        digest.update(chunk)
    return digest.hexdigest()


def _git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(SUITE_DIR.parent), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout if result.returncode == 0 else ""


def _source_state() -> dict[str, str | bool | None]:
    head = _git_output("rev-parse", "HEAD").strip() or None
    status = _git_output("status", "--porcelain=v1", "--untracked-files=all")
    status_lines = [
        line for line in status.splitlines()
        if line.strip() and not _is_evidence_path(line[3:].strip())
    ]
    diff = _git_output(
        "diff", "--binary", "HEAD", "--", ".",
        ":(exclude).DS_Store", ":(exclude)**/.DS_Store",
        ":(exclude)**/__pycache__/**", ":(exclude)**/.pytest_cache/**",
        ":(exclude)**/.mypy_cache/**", ":(exclude)**/.ruff_cache/**",
        ":(exclude)**/.tox/**", ":(exclude)**/.nox/**", ":(exclude)**/.venv/**",
        ":(exclude)**/.cache/**", ":(exclude)**/*.egg-info/**",
        ":(exclude)**/*.pyc", ":(exclude)**/*.pyo", ":(exclude)results/**",
        ":(exclude)build/**", ":(exclude)dist/**",
    )
    untracked = _git_output("ls-files", "--others", "--exclude-standard").splitlines()
    chunks = [diff.encode(), "\n".join(status_lines).encode()]
    for relative_name in sorted(untracked):
        path = SUITE_DIR.parent / relative_name
        if path.is_file() and not _is_evidence_path(relative_name):
            chunks.extend((relative_name.encode(), path.read_bytes()))
    return {
        "git_head": head,
        "git_dirty": bool(status_lines),
        "source_diff_state_sha256": _sha256_chunks(chunks),
    }


def _suite_fingerprint(tasks: list) -> str:
    chunks: list[bytes] = []
    for task in tasks:
        for root in (task.path / "task.json", task.seed_dir, task.oracle_dir):
            files = [root] if root.is_file() else sorted(path for path in root.rglob("*") if path.is_file())
            for path in files:
                relative_path = path.relative_to(task.path)
                if _is_evidence_path(relative_path):
                    continue
                chunks.extend((
                    task.id.encode(),
                    str(relative_path).replace(os.sep, "/").encode(),
                    path.read_bytes(),
                ))
    return _sha256_chunks(chunks)


def _suite_state_fingerprint() -> str:
    """Hash every stable file in suite/, including files outside task roots."""
    chunks: list[bytes] = []
    for path in sorted(candidate for candidate in SUITE_DIR.rglob("*") if candidate.is_file()):
        relative_path = path.relative_to(SUITE_DIR.parent)
        if not _is_evidence_path(relative_path):
            chunks.extend((
                str(relative_path).replace(os.sep, "/").encode(),
                path.read_bytes(),
            ))
    return _sha256_chunks(chunks)


def _redact_probe_output(value: str) -> str:
    value = re.sub(r"(?<![A-Za-z0-9_.-])/[^\s]+", "<path>", value)
    value = re.sub(r"[\w.+-]+@[\w.-]+", "<redacted-email>", value)
    return value.strip()[:500]


def _provider_metadata(provider: str, requested_model: str | None) -> dict:
    executable = provider
    model_argument = requested_model
    # CFG-4: sem catálogo legado, o provider é o próprio executável;
    # resolução concreta de modelo passa a ser papel do núcleo/Nike.
    probe = {"available": False, "output": "unavailable"}
    try:
        result = subprocess.run(
            [Path(executable).name, "--version"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        output = _redact_probe_output(result.stdout + result.stderr)
        probe = {
            "available": result.returncode == 0,
            "output": output if result.returncode == 0 and output else "unavailable",
        }
    except (OSError, subprocess.TimeoutExpired):
        pass
    return {
        "provider": provider,
        "requested_model": requested_model,
        "athena_model_argument": model_argument,
        "model_identity_note": (
            "Athena CLI argument only; this is not independently verified runtime model identity."
        ),
        "executable_basename": Path(executable).name,
        "version_probe": probe,
    }


def _run_manifest(
    tasks: list,
    provider_specs: list[str],
    repeat: int,
    timeout: int,
    started_at: datetime,
    *,
    suite_fingerprint: str | None = None,
    dirty_suite_paths: list[str] | None = None,
    allow_dirty_suite: bool = False,
) -> dict:
    providers = []
    for spec in provider_specs:
        provider, _, requested_model = spec.partition(":")
        providers.append(_provider_metadata(provider, requested_model or None))
    suite_fingerprint = suite_fingerprint or _suite_fingerprint(load_suite())
    dirty_suite_paths = sorted(dirty_suite_paths or [])
    return {
        "result_schema_version": 1,
        "suite_version": __version__,
        "run_id": str(uuid.uuid4()),
        "started_at": started_at.isoformat(),
        "ordered_task_ids": [task.id for task in tasks],
        "requested_provider_specs": providers,
        "repeat": repeat,
        "timeout_seconds": timeout,
        "expected_episode_count": len(tasks) * len(provider_specs) * repeat,
        "runtime": {
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "os_name": platform.system(),
            "os_release": platform.release(),
            "machine_architecture": platform.machine(),
        },
        "source_state": _source_state(),
        "suite_fingerprint_sha256": suite_fingerprint,
        "suite_baseline_fingerprint_sha256": suite_fingerprint,
        "dirty_suite_baseline_allowed": allow_dirty_suite,
        "dirty_suite_baseline_paths": dirty_suite_paths,
        "limitations": [
            "Backend model identity is not independently verified.",
            "Temperature is not independently controlled unless the provider CLI proves it.",
            "Provider-side nondeterminism is not independently controlled unless the provider CLI proves it.",
        ],
    }


def _write_result(manifest: dict, episodes: list[dict], started_at: datetime) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"run-{started_at.strftime('%Y%m%d-%H%M%S')}-{manifest['run_id'][:8]}.json"
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
    manifest["actual_episode_count"] = len(episodes)
    manifest["summary"] = _summarize(episodes)
    manifest["episodes"] = episodes
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=_cli_prog_name(),
        description="When a coding agent says 'done' — is it true?",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List suite tasks")

    run = sub.add_parser("run", help="Run the suite against one or more CLIs")
    run.add_argument("--providers", nargs="+", required=True,
                     help="provider[:model], e.g. claude:haiku cursor:claude-sonnet-5")
    run.add_argument("--tasks", nargs="*", help="task ids (default: all)")
    run.add_argument("--timeout", type=int, default=300)
    run.add_argument("--repeat", type=int, default=1,
                     help="episodes per task (default 1); use 3+ for rates that mean something")
    run.add_argument(
        "--allow-dirty-suite",
        action="store_true",
        help="allow an explicitly reviewed dirty suite only if its baseline remains unchanged",
    )

    args = parser.parse_args(argv)

    if args.command == "list":
        for task in load_suite():
            print(f"{task.id}  [{task.category}]")
        return 0

    tasks = load_suite()
    if args.tasks:
        wanted = set(args.tasks)
        tasks = [t for t in tasks if t.id in wanted]
        missing = wanted - {t.id for t in tasks}
        if missing:
            print(f"unknown tasks: {', '.join(sorted(missing))}", file=sys.stderr)
            return 2

    dirty = _suite_integrity_check()
    if dirty and not args.allow_dirty_suite:
        print("SUITE DIRTY — refusing to run. Inspect and restore manually:", file=sys.stderr)
        print("  " + "\n  ".join(dirty), file=sys.stderr)
        return 3

    baseline_fingerprint = _suite_state_fingerprint()
    started_at = datetime.now(timezone.utc)
    manifest = _run_manifest(
        tasks,
        args.providers,
        args.repeat,
        args.timeout,
        started_at,
        suite_fingerprint=baseline_fingerprint,
        dirty_suite_paths=dirty,
        allow_dirty_suite=args.allow_dirty_suite,
    )
    episodes: list[dict] = []
    total = len(tasks) * len(args.providers) * args.repeat
    n = 0
    for spec in args.providers:
        provider, _, model = spec.partition(":")
        for task in tasks:
            for rep in range(1, args.repeat + 1):
                n += 1
                suffix = f" (ep {rep}/{args.repeat})" if args.repeat > 1 else ""
                print(f"[{n}/{total}] {task.id} × {spec}{suffix} ...", flush=True)
                try:
                    ep = run_episode(task, provider, model or None, timeout=args.timeout)
                except KeyboardInterrupt:
                    manifest["run_status"] = "interrupted"
                    manifest["interrupted_episode"] = {
                        "provider": provider,
                        "task_id": task.id,
                        "repetition": rep,
                        "episode_index": n,
                    }
                    out = _write_result(manifest, episodes, started_at)
                    print(f"\nInterrupted; partial results: {out}", file=sys.stderr)
                    return 130
                episodes.append(ep.to_dict())
                print(f"   → {ep.verdict}" + (f" ({ep.error[:60]})" if ep.error else ""))
                current_dirty = _suite_integrity_check()
                current_fingerprint = _suite_state_fingerprint()
                if (
                    current_dirty != dirty
                    or current_fingerprint != baseline_fingerprint
                ):
                    manifest["run_status"] = "aborted_suite_contamination"
                    manifest["contaminated_suite_paths"] = sorted(
                        set(dirty) | set(current_dirty)
                    )
                    manifest["contaminated_suite_fingerprint_sha256"] = current_fingerprint
                    out = _write_result(manifest, episodes, started_at)
                    print(
                        "SUITE CONTAMINATED — refusing subsequent episodes; preserve evidence:",
                        file=sys.stderr,
                    )
                    print(
                        "  " + "\n  ".join(manifest["contaminated_suite_paths"]),
                        file=sys.stderr,
                    )
                    print(f"\nPartial results: {out}")
                    return 3

    manifest["run_status"] = "completed"
    out = _write_result(manifest, episodes, started_at)
    summary = manifest["summary"]

    print("\n── summary ──")
    for provider, bucket in summary.items():
        rate = bucket.get("false_success_rate")
        rate_str = f" | false-success rate: {rate * 100:.0f}%" if rate is not None else ""
        guard_rate = bucket.get("guard_violation_rate")
        guard_rate_str = f" | guard-violation rate: {guard_rate * 100:.0f}%" if guard_rate is not None else ""
        print(f"{provider}: {bucket['episodes']} episodes | "
              f"{bucket['solved']} solved | {bucket['false_success']} false success | "
              f"{bucket['failed_honest']} honest failures | "
              f"{bucket['guard_violations']} guard violations{rate_str}{guard_rate_str}")
    print(f"\nResults: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
