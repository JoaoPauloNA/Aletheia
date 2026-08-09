import json

import pytest

from loader import load_config


def test_valid_json(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"a": 1}))
    assert load_config(str(p)) == {"a": 1}


def test_invalid_json_raises(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json")
    with pytest.raises(ValueError):
        load_config(str(p))
