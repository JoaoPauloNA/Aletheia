"""Cross-repo INT-ALE-0 integration: real Athena package + synthetic CLI."""

from __future__ import annotations

import json
import os
import shutil
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest
from athena.config_loader import ConfigLoadError, build_manifest, write_snapshot

import athena_compat
from polygraph.runner import run_episode
from polygraph.suite import load_suite


def _write_minimal_config(config_dir: Path, *, command: str, provider_id: str = "synthetic") -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    providers = {
        provider_id: {
            "mode": "agent_cli",
            "runtime_class": "local",
            "command": command,
            "enabled": True,
            "approved": True,
        }
    }
    (config_dir / "providers.json").write_text(json.dumps(providers), encoding="utf-8")
    (config_dir / "functions.json").write_text("{}", encoding="utf-8")
    write_snapshot(config_dir, build_manifest(config_dir))


def _write_synthetic_cli(path: Path, *, sleep_s: float = 0.0) -> None:
    path.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env python3
            import json
            import sys
            import time

            print("agent report: all tests pass", flush=True)
            print(json.dumps(sys.argv[1:]), file=sys.stderr, flush=True)
            sleep_s = {sleep_s!r}
            if sleep_s:
                time.sleep(sleep_s)
            """
        ),
        encoding="utf-8",
    )
    path.chmod(0o755)


def _block_bridge_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("bridge must not execute")

    monkeypatch.setattr(athena_compat.LocalBridgeRunner, "run", _fail)


@pytest.fixture()
def athena_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    config_dir = tmp_path / ".athena"
    monkeypatch.setattr(athena_compat, "_config_dir", lambda: config_dir)
    return config_dir


def test_ask_provider_returns_structured_result(
    tmp_path: Path, athena_config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cli = tmp_path / "synthetic_cli.py"
    _write_synthetic_cli(cli)
    _write_minimal_config(athena_config, command=str(cli))
    workdir = tmp_path / "work"
    workdir.mkdir()

    result = athena_compat.ask_provider(
        "synthetic",
        "implement feature",
        working_directory=str(workdir),
        skip_permissions=True,
    )

    assert hasattr(result, "stdout")
    assert hasattr(result, "stderr")
    assert hasattr(result, "error")
    assert hasattr(result, "timed_out")
    assert result.stdout.strip() == "agent report: all tests pass"
    assert "implement feature" in result.stderr
    assert result.timed_out is False
    assert result.error is None


def test_ask_provider_passes_model_as_separate_argv(
    tmp_path: Path, athena_config: Path,
) -> None:
    cli = tmp_path / "synthetic_cli.py"
    _write_synthetic_cli(cli)
    _write_minimal_config(athena_config, command=str(cli))
    workdir = tmp_path / "work"
    workdir.mkdir()

    result = athena_compat.ask_provider(
        "synthetic",
        "task prompt",
        model="probe-model-7",
        working_directory=str(workdir),
        skip_permissions=True,
    )

    argv = json.loads(result.stderr.strip())
    model_index = argv.index("--model")
    assert argv[model_index + 1] == "probe-model-7"
    assert "-p" in argv
    assert argv[argv.index("-p") + 1] == "task prompt"


def test_ask_provider_timeout_surfaces_timed_out_with_streams(
    tmp_path: Path, athena_config: Path,
) -> None:
    cli = tmp_path / "synthetic_cli.py"
    _write_synthetic_cli(cli, sleep_s=2.0)
    _write_minimal_config(athena_config, command=str(cli))
    workdir = tmp_path / "work"
    workdir.mkdir()

    result = athena_compat.ask_provider(
        "synthetic",
        "slow task",
        timeout=0.3,
        working_directory=str(workdir),
        skip_permissions=True,
    )

    assert result.timed_out is True
    assert result.error
    assert isinstance(result.stdout, str)
    assert isinstance(result.stderr, str)


@pytest.mark.parametrize(
    "invalid_model",
    ["", "   ", "\x00model", True, 123, "x" * 129],
)
def test_invalid_model_rejected_before_execution(
    tmp_path: Path,
    athena_config: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_model: object,
) -> None:
    cli = tmp_path / "synthetic_cli.py"
    _write_synthetic_cli(cli)
    _write_minimal_config(athena_config, command=str(cli))
    _block_bridge_execution(monkeypatch)

    with pytest.raises(ValueError, match="model"):
        athena_compat.ask_provider(
            "synthetic",
            "prompt",
            model=invalid_model,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "invalid_timeout",
    [True, False, 0, -1, float("inf"), float("nan"), 100_000],
)
def test_invalid_timeout_rejected_before_execution(
    tmp_path: Path,
    athena_config: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_timeout: object,
) -> None:
    cli = tmp_path / "synthetic_cli.py"
    _write_synthetic_cli(cli)
    _write_minimal_config(athena_config, command=str(cli))
    _block_bridge_execution(monkeypatch)

    with pytest.raises(ValueError, match="timeout"):
        athena_compat.ask_provider(
            "synthetic",
            "prompt",
            timeout=invalid_timeout,  # type: ignore[arg-type]
        )


def test_corrupt_snapshot_fails_closed_without_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_dir = tmp_path / ".athena"
    config_dir.mkdir()
    (config_dir / "snapshot.json").write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr(athena_compat, "_config_dir", lambda: config_dir)
    _block_bridge_execution(monkeypatch)

    with pytest.raises(ConfigLoadError):
        athena_compat.ask_provider("synthetic", "prompt")


def test_broken_snapshot_symlink_fails_closed_without_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_dir = tmp_path / ".athena"
    config_dir.mkdir()
    os.symlink(str(tmp_path / "missing-snapshot-target"), config_dir / "snapshot.json")
    monkeypatch.setattr(athena_compat, "_config_dir", lambda: config_dir)
    _block_bridge_execution(monkeypatch)

    with pytest.raises(ConfigLoadError):
        athena_compat.ask_provider("synthetic", "prompt")


def test_broken_config_dir_symlink_fails_closed_without_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broken_config = tmp_path / "broken-athena"
    os.symlink(str(tmp_path / "missing-config-target"), broken_config)
    monkeypatch.setattr(athena_compat, "_config_dir", lambda: broken_config)
    _block_bridge_execution(monkeypatch)

    with pytest.raises(ConfigLoadError):
        athena_compat.ask_provider("synthetic", "prompt")


def test_malformed_config_path_fails_closed_without_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / ".athena"
    config_path.write_text("not-a-directory", encoding="utf-8")
    monkeypatch.setattr(athena_compat, "_config_dir", lambda: config_path)
    _block_bridge_execution(monkeypatch)

    with pytest.raises(ConfigLoadError):
        athena_compat.ask_provider("synthetic", "prompt")


def test_missing_provider_fails_closed_without_execution(
    tmp_path: Path,
    athena_config: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli = tmp_path / "synthetic_cli.py"
    _write_synthetic_cli(cli)
    _write_minimal_config(athena_config, command=str(cli))
    _block_bridge_execution(monkeypatch)

    with pytest.raises(ValueError, match="not declared"):
        athena_compat.ask_provider("missing-provider", "prompt")


def test_absent_snapshot_allows_non_authoritative_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli = tmp_path / "synthetic_cli.py"
    _write_synthetic_cli(cli)
    missing_config = tmp_path / "missing-athena"
    monkeypatch.setattr(athena_compat, "_config_dir", lambda: missing_config)
    workdir = tmp_path / "work"
    workdir.mkdir()

    result = athena_compat.ask_provider(
        str(cli),
        "fallback prompt",
        working_directory=str(workdir),
        skip_permissions=True,
    )

    assert result.stdout.strip() == "agent report: all tests pass"


def test_run_episode_timeout_path(
    tmp_path: Path, athena_config: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli = tmp_path / "synthetic_cli.py"
    _write_synthetic_cli(cli, sleep_s=2.0)
    _write_minimal_config(athena_config, command=str(cli), provider_id="synthetic")

    task = load_suite()[0]
    workdir = tmp_path / "work"
    shutil.copytree(task.seed_dir, workdir)
    monkeypatch.setattr("polygraph.runner._prepare_workspace", lambda _: str(workdir))

    episode = run_episode(task, "synthetic", timeout=1)

    assert episode.verdict == "HARNESS_ERROR"
    assert "timed out" in episode.error


def test_run_episode_honest_failure_with_real_provider_shape(
    tmp_path: Path, athena_config: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli = tmp_path / "synthetic_cli.py"
    cli.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            print("I could not complete the task; tests still failing.", flush=True)
            """
        ),
        encoding="utf-8",
    )
    cli.chmod(0o755)
    _write_minimal_config(athena_config, command=str(cli))
    monkeypatch.setattr(
        athena_compat,
        "run_command",
        lambda *args, **kwargs: SimpleNamespace(exit_code=1, ok=False),
    )

    task = load_suite()[0]
    workdir = tmp_path / "work"
    shutil.copytree(task.seed_dir, workdir)
    monkeypatch.setattr("polygraph.runner._prepare_workspace", lambda _: str(workdir))

    episode = run_episode(task, "synthetic", timeout=30)

    assert episode.verdict == "FAILED_HONEST"
    assert not episode.claimed_done
    assert "could not complete" in episode.report
