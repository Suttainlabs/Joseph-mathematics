"""Error paths of the data and dashboard scripts."""
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_fetch_raises_after_retries(monkeypatch):
    fd = load("fetch_data")
    calls = []

    def boom(url, timeout=0):
        calls.append(url)
        raise OSError("network down")

    monkeypatch.setattr(fd.urllib.request, "urlopen", boom)
    monkeypatch.setattr(fd.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError, match="failed to fetch https://example.invalid/x"):
        fd.get_text("https://example.invalid/x")
    assert len(calls) == 4


def test_read_json_reports_missing_file(tmp_path):
    bd = load("build_dashboard")
    with pytest.raises(SystemExit, match="run the earlier pipeline steps"):
        bd.read_json(tmp_path / "missing.json")


def test_canon_area_merges_new_york_and_drops_regions():
    fd = load("fetch_data")
    assert fd.canon_area("New York City") == "NEW YORK"
    assert fd.canon_area("NEW YORK (excluding New York City)") == "NEW YORK"
    assert fd.canon_area("NEW ENGLAND") is None
    assert fd.canon_area("Texas") == "TEXAS"
