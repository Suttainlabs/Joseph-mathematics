"""Build annual state-level case series for chlamydia and primary & secondary
(P&S) syphilis from public CDC and Census sources.

Sources
-------
* CDC NNDSS weekly tables on data.cdc.gov (Socrata API). Each weekly table
  carries two cumulative columns: the current year to date and the previous
  year through the same week. The current-year column is provisional and runs
  several percent low. This script therefore takes the count for year Y from
  the *previous-year* column in the last week of the year Y+1 table, which
  has had a further twelve months of late reports added.
* U.S. Census Bureau Vintage 2020 and Vintage 2025 state population estimates.

Output: data/sti_state_year.csv with columns
    state, year, disease, cases, population, rate_per_100k, source_table
and data/SOURCES.json recording each dataset id, the week used and the
retrieval time.

These are NNDSS counts as they stood about one year after each reporting
year closed. They are close to, but not identical with, the finalized
figures in CDC's annual STI Surveillance reports.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BASE = "https://data.cdc.gov"

# table year -> dataset id (the table for year Y+1 supplies the count for Y)
CHLAMYDIA_TABLES = {
    2014: "qz8t-eu2e", 2015: "97tt-n3j3", 2016: "n835-hpyp", 2017: "7mbm-jety",
    2018: "5egk-p6rd", 2019: "kx9y-asbg", 2020: "cds4-6y7t", 2021: "hwyy-s2tt",
}
SYPHILIS_TABLES = {
    2014: "fqve-8wzt", 2015: "ekd3-qu3w", 2016: "6jgb-zrsp", 2017: "75b3-73qi",
    2018: "efpc-rr7b", 2019: "b6np-zdqj", 2020: "paqx-33a8", 2021: "6ie8-bpiy",
}
COMBINED = "x9gk-5huc"  # NNDSS Weekly Data, 2022 onward, long format
DISEASES = {
    "chlamydia": ("chlamydia trachomatis infection", CHLAMYDIA_TABLES,
                  "Chlamydia trachomatis infection"),
    "ps_syphilis": ("syphilis, primary and secondary", SYPHILIS_TABLES,
                    "Syphilis, Primary and secondary"),
}

STATES = """ALABAMA ALASKA ARIZONA ARKANSAS CALIFORNIA COLORADO CONNECTICUT DELAWARE
DISTRICT_OF_COLUMBIA FLORIDA GEORGIA HAWAII IDAHO ILLINOIS INDIANA IOWA KANSAS
KENTUCKY LOUISIANA MAINE MARYLAND MASSACHUSETTS MICHIGAN MINNESOTA MISSISSIPPI
MISSOURI MONTANA NEBRASKA NEVADA NEW_HAMPSHIRE NEW_JERSEY NEW_MEXICO NEW_YORK
NORTH_CAROLINA NORTH_DAKOTA OHIO OKLAHOMA OREGON PENNSYLVANIA RHODE_ISLAND
SOUTH_CAROLINA SOUTH_DAKOTA TENNESSEE TEXAS UTAH VERMONT VIRGINIA WASHINGTON
WEST_VIRGINIA WISCONSIN WYOMING""".split()
STATES = [s.replace("_", " ") for s in STATES]


def _fetch(url: str, tries: int = 4) -> bytes:
    """GET with retries; raises RuntimeError naming the URL if all tries fail."""
    last = None
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return r.read()
        except Exception as e:  # network hiccups are common on these servers
            last = e
            time.sleep(2 + 2 * k)
    raise RuntimeError(f"failed to fetch {url}: {last}")


def get_json(url: str):
    try:
        return json.loads(_fetch(url))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"{url} did not return valid JSON: {e}")


def get_text(url: str) -> str:
    return _fetch(url).decode("latin-1")


def canon_area(name: str) -> str | None:
    """Map an NNDSS reporting area to a state name, or None to drop it.
    New York is reported in two parts (New York City and the rest of the
    state); both map to NEW YORK and are summed by the caller."""
    n = re.sub(r"\s+", " ", name.upper().strip())
    n = n.replace("DIST. OF COL.", "DISTRICT OF COLUMBIA")
    if n in ("NEW YORK CITY", "NEW YORK (EXCLUDING NEW YORK CITY)",
             "NEW YORK (UPSTATE)", "UPSTATE NEW YORK", "NEW YORK (EXCL NYC)"):
        return "NEW YORK"
    return n if n in STATES else None


def num(v) -> float | None:
    if v is None:
        return None
    s = str(v).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def from_wide_table(dsid: str, disease_label: str, count_year: int):
    """Read 'Cum <count_year>' for one disease from a per-year wide table."""
    meta = get_json(f"{BASE}/api/views/{dsid}.json")
    want = f"{disease_label}, cum {count_year}"
    field = None
    for c in meta["columns"]:
        nm = c["name"].lower().replace("†", "").replace("  ", " ").strip()
        if nm == want:
            field = c["fieldName"]
    if field is None:
        raise RuntimeError(f"{dsid}: no column named like '{want}'")
    wk = get_json(f"{BASE}/resource/{dsid}.json?$select=max(mmwr_week)")[0]["max_mmwr_week"]
    q = urllib.parse.urlencode({"$select": f"reporting_area,{field}",
                                "$where": f"mmwr_week={wk}", "$limit": 500})
    rows = get_json(f"{BASE}/resource/{dsid}.json?{q}")
    out = {}
    for r in rows:
        st = canon_area(r.get("reporting_area", ""))
        v = num(r.get(field))
        if st is None or v is None:
            continue
        out[st] = out.get(st, 0.0) + v
    return out, {"dataset": dsid, "column": field, "week": int(wk),
                 "url": f"{BASE}/d/{dsid}"}


def from_combined(label: str, table_year: int):
    """Read the previous-year cumulative (m4) from the 2022+ long table."""
    q = urllib.parse.urlencode({"$select": "max(week)",
                                "$where": f"year='{table_year}' AND label='{label}'"})
    wk = get_json(f"{BASE}/resource/{COMBINED}.json?{q}")[0].get("max_week")
    if wk is None or int(wk) < 52:
        return None, None  # that year's table is not complete yet
    q = urllib.parse.urlencode({"$select": "states,m4", "$limit": 500,
                                "$where": f"year='{table_year}' AND week='{wk}' AND label='{label}'"})
    rows = get_json(f"{BASE}/resource/{COMBINED}.json?{q}")
    out = {}
    for r in rows:
        st = canon_area(r.get("states", ""))
        v = num(r.get("m4"))
        if st is None or v is None:
            continue
        out[st] = out.get(st, 0.0) + v
    return out, {"dataset": COMBINED, "column": "m4 (cum previous year)",
                 "week": int(wk), "url": f"{BASE}/d/{COMBINED}"}


def populations():
    """State resident population, 1 July estimates, 2013-2025."""
    pop = {}
    v2020 = get_text("https://www2.census.gov/programs-surveys/popest/datasets/"
                     "2010-2020/state/totals/nst-est2020-alldata.csv")
    for r in csv.DictReader(io.StringIO(v2020)):
        st = r["NAME"].upper()
        if st in STATES:
            for y in range(2013, 2020):
                pop[(st, y)] = int(r[f"POPESTIMATE{y}"])
    v2025 = get_text("https://www2.census.gov/programs-surveys/popest/datasets/"
                     "2020-2025/state/totals/NST-EST2025-ALLDATA.csv")
    for r in csv.DictReader(io.StringIO(v2025)):
        st = r["NAME"].upper()
        if st in STATES:
            for y in range(2020, 2026):
                if f"POPESTIMATE{y}" in r:
                    pop[(st, y)] = int(r[f"POPESTIMATE{y}"])
    return pop


def main():
    pop = populations()
    rows, sources = [], {}
    this_year = datetime.now(timezone.utc).year
    for disease, (label_lc, tables, label) in DISEASES.items():
        for table_year in range(2014, this_year + 1):
            count_year = table_year - 1
            if table_year in tables:
                vals, src = from_wide_table(tables[table_year], label_lc, count_year)
            else:
                vals, src = from_combined(label, table_year)
            if not vals:
                print(f"{disease} {count_year}: no complete table, skipped", file=sys.stderr)
                continue
            sources[f"{disease}_{count_year}"] = src
            for st in STATES:
                if st not in vals:
                    print(f"{disease} {count_year}: {st} missing", file=sys.stderr)
                    continue
                p = pop[(st, count_year)]
                rows.append({"state": st.title().replace(" Of ", " of "), "year": count_year,
                             "disease": disease, "cases": int(vals[st]), "population": p,
                             "rate_per_100k": round(vals[st] / p * 1e5, 2),
                             "source_table": src["dataset"]})
            tot = sum(vals.get(s, 0) for s in STATES)
            print(f"{disease} {count_year}: {len(vals)} areas, 50 states + DC total {tot:,.0f}")
    if not rows:
        sys.exit("no rows were retrieved; nothing written")
    try:
        DATA.mkdir(exist_ok=True)
        with open(DATA / "sti_state_year.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        with open(DATA / "SOURCES.json", "w") as f:
            json.dump({"retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "note": "Count for year Y is the previous-year cumulative column in the "
                               "final week of the NNDSS table for year Y+1.",
                       "tables": sources}, f, indent=1)
    except OSError as e:
        sys.exit(f"could not write output files in {DATA}: {e}")
    print(f"wrote {len(rows)} rows")


if __name__ == "__main__":
    main()
