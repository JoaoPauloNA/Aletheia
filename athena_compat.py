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

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from athena.bridge import LocalBridgeRunner, RunRequest
from athena.config_loader import ConfigLoadError, load_config
from athena.execution import ExecutionRecord
from athena.execution_modes import resolve_execution_command
from athena.lease import DirectoryLeaseManager


@dataclass
class CommandResult:
    exit_code: int | None
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


def run_command(cmd: str, workdir: str) -> CommandResult:
    """Oráculo: executar pytest dentro do workdir do episódio."""
    proc = subprocess.run(shlex.split(cmd), cwd=workdir,
                          capture_output=True, text=True, timeout=120)
    return CommandResult(exit_code=proc.returncode,
                         stdout=proc.stdout[-2000:], stderr=proc.stderr[-2000:])


def _providers_from_config() -> dict[str, Any]:
    try:
        cfg = load_config(Path("~/.athena").expanduser())
        return cfg["parts"]["providers"]
    except (ConfigLoadError, FileNotFoundError):
        return {}


def ask_provider(provider_id: str, prompt: str, **kwargs: Any) -> str:
    """Executar prompt em provider declarado (agent_cli), via bridge governado.

    Aceita a assinatura antiga; parâmetros sem correspondência nova são
    aceitos e ignorados explicitamente para compatibilidade.
    """
    for legacy in ("use_default_role", "with_contract", "role"):
        kwargs.pop(legacy, None)
    working_directory = kwargs.pop("working_directory", None) or "/tmp"
    kwargs.pop("model", None)
    skip_permissions = bool(kwargs.pop("skip_permissions", False))
    kwargs.pop("timeout", None)

    spec = _providers_from_config().get(provider_id) or {
        "mode": "agent_cli",
        "command": provider_id.split(":")[0],
    }
    rr = resolve_execution_command(spec, prompt,
                                   unattended=skip_permissions,
                                   cwd=str(working_directory))

    result = LocalBridgeRunner().run(
        rr,
        ExecutionRecord(f"aletheia-{provider_id}"),
        DirectoryLeaseManager(),
    )
    return str(result.stdout or "")[:20000]
