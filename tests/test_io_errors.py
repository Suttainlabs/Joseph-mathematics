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


def test_read_summary_reports_missing_file(tmp_path):
    for name in ("build_dashboard", "make_figures"):
        mod = load(name)
        with pytest.raises(SystemExit, match="run_validation.py first"):
            mod.read_summary(tmp_path / "summary.csv")


def test_read_json_reports_damaged_file(tmp_path):
    bad = tmp_path / "fits.json"
    bad.write_text("{not json")
    with pytest.raises(SystemExit, match="cannot read"):
        load("make_figures").read_json(bad)


def test_read_cases_reports_missing_table(tmp_path, monkeypatch):
    rv = load("run_validation")
    monkeypatch.setattr(rv, "ROOT", tmp_path)
    with pytest.raises(SystemExit, match="fetch_data.py first"):
        rv.read_cases()


def test_write_outputs_reports_unwritable_folder(tmp_path):
    import pandas as pd
    rv = load("run_validation")
    blocker = tmp_path / "results"
    blocker.write_text("a file where the folder should be")
    with pytest.raises(SystemExit, match="could not write results"):
        rv.write_outputs(blocker, pd.DataFrame({"a": [1]}), pd.DataFrame({"a": [1]}), {})


def test_save_figure_reports_unwritable_folder(tmp_path, monkeypatch):
    import matplotlib.pyplot as plt
    mf = load("make_figures")
    (tmp_path / "figures").write_text("a file where the folder should be")
    monkeypatch.setattr(mf, "RES", tmp_path)
    fig = plt.figure()
    with pytest.raises(SystemExit, match="could not write"):
        mf.save_figure(fig, "x.png")
    plt.close(fig)
