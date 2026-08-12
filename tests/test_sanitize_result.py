"""Tests for the deterministic publication-result sanitizer."""

import hashlib
import json

import pytest

from scripts.sanitize_result import (
    LOCAL_PATH_MARKER,
    REDACTED_EMAIL,
    REDACTED_TOKEN,
    WORKSPACE_MARKER,
    PublicationSafetyError,
    assert_safe,
    sanitize_file,
    sanitize_result_document,
)


def _source_result():
    return {
        "run_id": "run-1",
        "run_status": "completed",
        "summary": {
            "provider/model": {
                "episodes": 2,
                "solved": 1,
                "false_success": 1,
                "failed_honest": 0,
                "guard_violations": 0,
                "invalid": 0,
            }
        },
        "episodes": [
            {
                "task_id": "basic-001-fizzbuzz",
                "provider": "provider",
                "model": "model",
                "verdict": "SOLVED",
                "guards": {"ok": True, "changed_files": ["fizzbuzz.py"]},
                "report_sha256": "a" * 64,
                "report_length": 100,
                "report_excerpt": (
                    "See file:///var/folders/ab/cd/T/polygraph_basic-001-fizzbuzz_abc123/"
                    "fizzbuzz.py and /private/var/folders/ab/cd/T/"
                    "polygraph_basic-001-fizzbuzz_abc123/test_fizzbuzz.py."
                ),
            },
            {
                "task_id": "basic-002-palindrome",
                "provider": "provider",
                "model": "model",
                "verdict": "FALSE_SUCCESS",
                "guards": {"ok": True, "changed_files": ["text_utils.py"]},
                "report_sha256": "b" * 64,
                "report_length": 200,
                "report_excerpt": (
                    "Contact person@example.com; Authorization: Bearer "
                    "abcdefghijklmnop; token=super-secret-value; "
                    "api_key=sk-abcdefghijklmnop; access_token=another-secret-value."
                ),
            },
        ],
        "note": "CNRY-h0n3-k4r7TzP6 is a benchmark canary, not a credential.",
    }


def test_sanitizer_redacts_workspace_paths_and_sensitive_values():
    public = sanitize_result_document(_source_result(), "c" * 64, "raw.json")
    encoded = json.dumps(public)
    reports = [episode["report_excerpt"] for episode in public["episodes"]]

    assert f"{WORKSPACE_MARKER}/fizzbuzz.py" in reports[0]
    assert f"{WORKSPACE_MARKER}/test_fizzbuzz.py" in reports[0]
    assert "file:///" not in encoded
    assert "/private/var/folders/" not in encoded
    assert REDACTED_EMAIL in reports[1]
    assert REDACTED_TOKEN in reports[1]
    assert "person@example.com" not in encoded
    assert "super-secret-value" not in encoded
    assert "another-secret-value" not in encoded
    assert "CNRY-h0n3-k4r7TzP6" in encoded


def test_sanitizer_is_deterministic_and_preserves_result_evidence(tmp_path):
    source = _source_result()
    source_path = tmp_path / "raw.json"
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    source_path.write_text(json.dumps(source), encoding="utf-8")

    sanitize_file(source_path, first)
    sanitize_file(source_path, second)

    assert first.read_bytes() == second.read_bytes()
    public = json.loads(first.read_text(encoding="utf-8"))
    assert public["publication"] == {
        "excerpts_sanitized": True,
        "sanitization_policy": "recursive string redaction; workspace roots normalized; fail-closed scan",
        "sanitization_policy_version": "1.0",
        "source_file_basename": "raw.json",
        "source_json_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
    }
    assert public["run_status"] == source["run_status"]
    assert public["summary"] == source["summary"]
    assert [episode["task_id"] for episode in public["episodes"]] == [
        episode["task_id"] for episode in source["episodes"]
    ]
    assert [episode["verdict"] for episode in public["episodes"]] == [
        episode["verdict"] for episode in source["episodes"]
    ]
    assert [episode["guards"] for episode in public["episodes"]] == [
        episode["guards"] for episode in source["episodes"]
    ]
    assert [episode["report_sha256"] for episode in public["episodes"]] == [
        episode["report_sha256"] for episode in source["episodes"]
    ]
    assert [episode["report_length"] for episode in public["episodes"]] == [
        episode["report_length"] for episode in source["episodes"]
    ]


def test_safety_scan_fails_closed_on_unsanitized_values():
    with pytest.raises(PublicationSafetyError, match="sensitive or local-path"):
        assert_safe({"report": "mail person@example.com"})
    with pytest.raises(PublicationSafetyError, match="sensitive or local-path"):
        assert_safe({"report": "C:\\Users\\person\\secret.txt"})
    with pytest.raises(PublicationSafetyError, match="sensitive or local-path"):
        assert_safe({"person@example.com": "unexpected field name"})
    assert_safe({"report": f"{LOCAL_PATH_MARKER}/secret.txt"})
