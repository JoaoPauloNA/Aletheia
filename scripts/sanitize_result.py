"""Create a deterministic, publication-safe Aletheia result artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

POLICY_VERSION = "1.0"
WORKSPACE_MARKER = "<WORKSPACE>"
REDACTED_TOKEN = "<REDACTED_TOKEN>"
REDACTED_EMAIL = "<REDACTED_EMAIL>"
LOCAL_PATH_MARKER = "<LOCAL_PATH>"

_WORKSPACE_ROOT_RE = re.compile(
    r"(?:file://)?(?:/private)?/var/folders/[^/\s]+/[^/\s]+/T/"
    r"polygraph_[A-Za-z0-9-]+_[A-Za-z0-9]+"
)
_FILE_URI_RE = re.compile(r"file:///[^\s)\]}>`\"']+")
_LOCAL_PATH_RE = re.compile(
    r"(?<![\w:])/(?:Users|home|private|var|tmp|etc|opt|Volumes)/[^\s)\]}>`\"']+"
)
_WINDOWS_PATH_RE = re.compile(r"(?<![\w])(?:[A-Za-z]:\\)[^\s)\]}>`\"']+")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_BEARER_RE = re.compile(r"\b(Bearer)\s+([A-Za-z0-9._~+/=-]{8,})\b", re.IGNORECASE)
_ASSIGNED_SECRET_RE = re.compile(
    r"(?<![A-Za-z0-9])(password|passwd|secret|token|access[_ -]?token|"
    r"client[_ -]?secret|private[_ -]?key|api[_ -]?key|authorization)"
    r"(\s*[:=]\s*[\"']?)((?!<REDACTED_TOKEN>)[^\s\"',;]{6,})",
    re.IGNORECASE,
)
_KNOWN_TOKEN_RE = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_-]{12,}|"
    r"github_pat_[A-Za-z0-9_-]{12,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,})\b"
)


class PublicationSafetyError(ValueError):
    """Raised when a document cannot be safely published."""


def _with_basename(marker: str, value: str) -> str:
    """Replace a local path while retaining its final useful filename."""
    basename = value.rstrip("/").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return f"{marker}/{basename}" if basename and basename != value else marker


def sanitize_text(value: str) -> str:
    """Redact sensitive material from one string without changing its meaning."""
    value = _WORKSPACE_ROOT_RE.sub(WORKSPACE_MARKER, value)
    value = _FILE_URI_RE.sub(lambda match: _with_basename(LOCAL_PATH_MARKER, match.group()), value)
    value = _LOCAL_PATH_RE.sub(lambda match: _with_basename(LOCAL_PATH_MARKER, match.group()), value)
    value = _WINDOWS_PATH_RE.sub(lambda match: _with_basename(LOCAL_PATH_MARKER, match.group()), value)
    value = _EMAIL_RE.sub(REDACTED_EMAIL, value)
    value = _BEARER_RE.sub(r"\1 " + REDACTED_TOKEN, value)
    value = _ASSIGNED_SECRET_RE.sub(r"\1\2" + REDACTED_TOKEN, value)
    return _KNOWN_TOKEN_RE.sub(REDACTED_TOKEN, value)


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_value(item) for key, item in value.items()}
    return value


def _unsafe_matches(value: str) -> list[str]:
    patterns = (
        _WORKSPACE_ROOT_RE,
        _FILE_URI_RE,
        _LOCAL_PATH_RE,
        _WINDOWS_PATH_RE,
        _EMAIL_RE,
        _BEARER_RE,
        _ASSIGNED_SECRET_RE,
        _KNOWN_TOKEN_RE,
    )
    return [pattern.pattern for pattern in patterns if pattern.search(value)]


def assert_safe(document: Any) -> None:
    """Fail closed when any serialized string still matches a privacy pattern."""
    unsafe: list[str] = []

    def visit(value: Any, location: str) -> None:
        if isinstance(value, str):
            if _unsafe_matches(value):
                unsafe.append(location)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{location}[{index}]")
        elif isinstance(value, dict):
            for key, item in value.items():
                key_location = f"{location}.{key}"
                if _unsafe_matches(str(key)):
                    unsafe.append(key_location)
                visit(item, key_location)

    visit(document, "$")
    if unsafe:
        raise PublicationSafetyError(
            "sensitive or local-path pattern remains at " + ", ".join(unsafe[:10])
        )


def sanitize_result_document(source: dict[str, Any], source_sha256: str, source_name: str) -> dict[str, Any]:
    """Return a publication artifact preserving result evidence and record order."""
    if not isinstance(source.get("episodes"), list):
        raise PublicationSafetyError("source result has no episode list")

    public = _sanitize_value(source)
    public["publication"] = {
        "source_file_basename": source_name,
        "source_json_sha256": source_sha256,
        "sanitization_policy": "recursive string redaction; workspace roots normalized; fail-closed scan",
        "sanitization_policy_version": POLICY_VERSION,
        "excerpts_sanitized": True,
    }
    assert_safe(public)
    return public


def sanitize_file(input_path: Path, output_path: Path) -> dict[str, Any]:
    """Read, sanitize, validate, and deterministically write a result JSON file."""
    source_bytes = input_path.read_bytes()
    try:
        source = json.loads(source_bytes)
    except json.JSONDecodeError as error:
        raise PublicationSafetyError(f"invalid source JSON: {error}") from error
    if not isinstance(source, dict):
        raise PublicationSafetyError("source JSON root must be an object")

    public = sanitize_result_document(
        source,
        hashlib.sha256(source_bytes).hexdigest(),
        input_path.name,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(public, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return public


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="completed raw benchmark JSON")
    parser.add_argument("output", type=Path, help="publication-safe JSON output")
    args = parser.parse_args(argv)
    try:
        sanitize_file(args.input, args.output)
    except (OSError, PublicationSafetyError) as error:
        print(f"sanitize_result: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
