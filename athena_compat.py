"""Compatibilidade Aletheia ↔ núcleo Athena-MCP (CFG-4).

Fornece `ask_provider` e `run_command` com as assinaturas históricas do
Aletheia, implementadas sobre o pacote publicado do Athena-MCP — sem
dependência de diretórios locais fora do controle de versão.

- `run_command(cmd, workdir)` → oráculo pytest no workspace (subprocesso
  isolado, exigência do protocolo de episódio).
- `ask_provider(provider_id, prompt, ...)` → resolve o provider declarado
  via `athena.execution_modes` e executa pelo bridge governado.
"""

from __future__ import annotations

import math
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from athena.bridge import LocalBridgeRunner, RunResult
from athena.config_loader import load_config
from athena.execution import ExecutionDeadlines, ExecutionRecord, ExecutionState
from athena.execution_modes import resolve_execution_command
from athena.lease import DirectoryLeaseManager

_MAX_CAPTURE = 20_000
_MAX_MODEL_LEN = 128
_MAX_TIMEOUT_S = 86_400.0


@dataclass
class CommandResult:
    exit_code: int | None
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


@dataclass
class ProviderResult:
    """Resultado estruturado consumível por `polygraph.runner.run_episode`."""

    stdout: str = ""
    stderr: str = ""
    error: str | None = None
    timed_out: bool = False

    @property
    def output(self) -> str:
        return self.stdout + self.stderr


def run_command(cmd: str, workdir: str) -> CommandResult:
    """Oráculo: executar pytest dentro do workdir do episódio."""
    proc = subprocess.run(shlex.split(cmd), cwd=workdir,
                          capture_output=True, text=True, timeout=120)
    return CommandResult(exit_code=proc.returncode,
                         stdout=proc.stdout[-2000:], stderr=proc.stderr[-2000:])


def _config_dir() -> Path:
    return Path("~/.athena").expanduser()


def _path_exists_lstat(path: Path) -> bool:
    """Return whether ``path`` exists without following symlinks."""
    try:
        os.lstat(path)
    except FileNotFoundError:
        return False
    except OSError:
        return True
    else:
        return True


def _snapshot_absent(config_dir: Path) -> bool:
    """True only when both config dir and snapshot path are genuinely absent."""
    snapshot_path = config_dir / "snapshot.json"
    return not _path_exists_lstat(config_dir) and not _path_exists_lstat(snapshot_path)


def _load_providers() -> tuple[bool, dict[str, Any]]:
    """Return whether a valid snapshot loaded and the declared provider map."""
    config_dir = _config_dir()
    if _snapshot_absent(config_dir):
        return False, {}
    cfg = load_config(config_dir)
    return True, cfg["providers"]


def _validate_model(model: object) -> str:
    if not isinstance(model, str):
        raise ValueError("model must be a non-empty string")
    normalized = model.strip()
    if not normalized or len(normalized) > _MAX_MODEL_LEN:
        raise ValueError("model must be a non-empty string")
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise ValueError("model contains control characters")
    return normalized


def _validate_timeout(timeout: object) -> float:
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise ValueError("timeout must be a positive finite number")
    value = float(timeout)
    if not math.isfinite(value) or value <= 0 or value > _MAX_TIMEOUT_S:
        raise ValueError("timeout must be a positive finite number")
    return value


def _resolve_provider_spec(provider_id: str) -> dict[str, Any]:
    config_available, providers = _load_providers()
    spec = providers.get(provider_id)
    if spec is not None:
        if not spec.get("enabled") or not spec.get("approved"):
            raise ValueError(f"provider {provider_id!r} is not eligible")
        return spec
    if config_available:
        raise ValueError(f"provider {provider_id!r} is not declared in Athena config")
    # Fallback não autoritativo apenas quando não há snapshot presente.
    return {
        "mode": "agent_cli",
        "command": provider_id.split(":")[0],
    }


def _provider_result(result: RunResult) -> ProviderResult:
    timed_out = result.timed_out
    error = result.error
    if timed_out and not error:
        error = (
            result.expired_deadline.value
            if result.expired_deadline is not None
            else ExecutionState.TIMED_OUT.value
        )
    return ProviderResult(
        stdout=(result.stdout or "")[:_MAX_CAPTURE],
        stderr=(result.stderr or "")[:_MAX_CAPTURE],
        error=error,
        timed_out=timed_out,
    )


def ask_provider(provider_id: str, prompt: str, **kwargs: Any) -> ProviderResult:
    """Executar prompt em provider declarado (agent_cli), via bridge governado."""
    for legacy in ("use_default_role", "with_contract", "role"):
        kwargs.pop(legacy, None)
    working_directory = kwargs.pop("working_directory", None) or "/tmp"
    model = kwargs.pop("model", None)
    skip_permissions = bool(kwargs.pop("skip_permissions", False))
    timeout = kwargs.pop("timeout", None)
    if kwargs:
        unexpected = ", ".join(sorted(kwargs))
        raise TypeError(f"ask_provider() got unexpected keyword arguments: {unexpected}")

    validated_model = _validate_model(model) if model is not None else None
    validated_timeout = _validate_timeout(timeout) if timeout is not None else None

    spec = _resolve_provider_spec(provider_id)
    rr = resolve_execution_command(
        spec,
        prompt,
        unattended=skip_permissions,
        cwd=str(working_directory),
        model=validated_model,
    )
    deadlines = (
        ExecutionDeadlines(absolute_timeout_s=validated_timeout)
        if validated_timeout is not None
        else None
    )
    result = LocalBridgeRunner().run(
        rr,
        ExecutionRecord(f"aletheia-{provider_id}", deadlines=deadlines),
        DirectoryLeaseManager(),
    )
    return _provider_result(result)
