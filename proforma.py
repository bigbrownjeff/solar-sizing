#!/usr/bin/env python3
"""proforma.py — the honest 20-row solar pro forma, on live federal data.

Pipeline (same as demo.html's "Live address" tab, server-side):

  1. NREL PVWatts v8  (https://developer.nrel.gov/api/pvwatts/v8.json)
     -> production for your coordinates, hourly or monthly, from NSRDB TMY data.
  2. OpenEI URDB      (https://api.openei.org/utility_rates?version=latest)
     -> real filed utility tariffs at your location; you pick one.
  3. The source note's honest arithmetic on those numbers: production-weighted
     tariff rate, roof-walk shading derate, NEM-3.0-style export credit,
     self-consumption split, ITC, simple payback, 25-yr NPV, and the
     marginal-next-kWp number no configurator shows you.

Outputs proforma.csv (20 rows + provenance + sensitivity) and a terminal summary.

Location: PVWatts v8 takes coordinates only — the street-address parameter was
retired after v6 — so production needs --lat/--lon (long-press your roof in any
maps app). --address works for the tariff lookup alone (URDB geocodes it
server-side) and for --list-tariffs.

API key: --api-key flag, else NREL_API_KEY env var, else DEMO_KEY. DEMO_KEY is
rate-limited by api.data.gov to 30 requests/IP/hour and 50/day; a free
registered key (https://developer.nrel.gov/signup/) gets 1,000/hour and works
on both endpoints. The key is sent to those two endpoints and nowhere else;
it is never written to disk or logged.

Offline check (no network, used by CI and by the author):
  python3 proforma.py --fixtures
runs the identical parsing + arithmetic against bundled doc-sourced fixtures
(fixtures/pvwatts-sample.json — the PVWatts v8 docs' own example response;
fixtures/urdb-sample.json — schema-built from the URDB docs, illustrative rates).

Stdlib only. No pip install. Python 3.11+.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---- model constants (mirrored by demo.html's live tab) ------------------------
ITC = 0.30                 # federal investment tax credit
DISCOUNT = 0.05            # NPV discount rate (the note's FIG.1 uses 5%)
DEGRADATION = 0.005        # panel output degradation per year (industry-standard 0.5%)
NPV_YEARS = 25
PVWATTS_LOSSES = 14.0      # PVWatts v8 default system losses, %; includes a generic
                           # ~3% shading allowance — the roof-walk derate stacks on top
ARRAY_TYPE = 1             # fixed, roof-mounted
MODULE_TYPE = 0            # standard crystalline
WEEKDAY_FRAC = 5.0 / 7.0   # blend weekday/weekend tariff schedules; TMY data has no
                           # real calendar, so we weight rather than invent one
SOLAR_WINDOW = (9, 17)     # monthly fallback only: spread each month's kWh evenly
                           # across 09:00-16:59 to weight the tariff. The hourly path
                           # (default) uses PVWatts' own 8760-hour profile instead.
DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
MARGINAL_KWP = 1.0         # the "next kWp" of the note's reason-to-buy-less row

PVWATTS_URL = "https://developer.nrel.gov/api/pvwatts/v8.json"
URDB_URL = "https://api.openei.org/utility_rates"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def fail(msg: str) -> "NoReturn":  # noqa: F821 — 3.11 has typing.NoReturn; string ann is fine
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


# ---- HTTP (the only two endpoints this script can call) -------------------------
def get_json(base: str, params: dict) -> dict:
    url = base + "?" + urllib.parse.urlencode(params)
    redacted = url.replace(params.get("api_key", "\x00"), "***")
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:600]
        except Exception:
            pass
        hint = ""
        if e.code in (401, 403):
            hint = ("\nhint: if you're on DEMO_KEY, this endpoint may have exhausted its "
                    "30/hour-per-IP allowance or may require a registered key — free at "
                    "https://developer.nrel.gov/signup/ (one key works on both endpoints).")
        elif e.code == 422:
            hint = "\nhint: a parameter failed validation; the API's own message above says which."
        fail(f"HTTP {e.code} from {redacted}\n{body}{hint}")
    except urllib.error.URLError as e:
        fail(f"could not reach {base} — {e.reason}. Check the network, or run "
             f"--fixtures for the offline check.")


def fetch_pvwatts(key: str, lat: float, lon: float, kw: float, tilt: float,
                  azimuth: float, timeframe: str) -> dict:
    data = get_json(PVWATTS_URL, {
        "api_key": key, "lat": lat, "lon": lon, "system_capacity": kw,
        "tilt": tilt, "azimuth": azimuth, "array_type": ARRAY_TYPE,
        "module_type": MODULE_TYPE, "losses": PVWATTS_LOSSES,
        "timeframe": timeframe,
    })
    if data.get("errors"):
        fail("PVWatts returned errors: " + "; ".join(map(str, data["errors"])))
    if "outputs" not in data:
        fail("PVWatts response has no 'outputs' object — cannot continue.")
    return data


def fetch_urdb(key: str, lat: float | None, lon: float | None,
               address: str | None, sector: str) -> dict:
    params = {"version": "latest", "format": "json", "api_key": key,
              "sector": sector, "detail": "full", "approved": "true", "limit": 20}
    if address:
        params["address"] = address
    else:
        params["lat"], params["lon"] = lat, lon
    return get_json(URDB_URL, params)


# ---- parsing: PVWatts -> month x hour production matrix -------------------------
def production_matrix(outputs: dict) -> tuple[list[list[float]], float, str]:
    """Return (P[12][24] kWh, annual kWh pre-derate, which path was used).

    Hourly path: PVWatts 'ac' is 8760 hourly Wac values in TMY order; one value
    per hour makes Wh, /1000 makes kWh. Exact production weighting. PVWatts
    hourly output is station local standard time — the same clock URDB
    schedules use, so the month x hour buckets line up without a shift.
    Monthly fallback (e.g. the doc-sourced fixture): spread ac_monthly evenly
    across the 09:00-16:59 window — coarser, and the CSV says so.
    """
    P = [[0.0] * 24 for _ in range(12)]
    ac = outputs.get("ac")
    if isinstance(ac, list) and len(ac) == 8760:
        i = 0
        for m, days in enumerate(DAYS_IN_MONTH):
            for _ in range(days):
                for h in range(24):
                    P[m][h] += float(ac[i]) / 1000.0
                    i += 1
        # element-wise accumulation, same order as the demo's JS mirror — keeps the
        # two implementations bit-identical at rounding boundaries
        annual = 0.0
        for m in range(12):
            for h in range(24):
                annual += P[m][h]
        return P, annual, "hourly (PVWatts 8760-hour profile)"
    monthly = outputs.get("ac_monthly")
    if not (isinstance(monthly, list) and len(monthly) == 12):
        fail("PVWatts outputs carry neither 'ac' (8760) nor 'ac_monthly' (12) — "
             "cannot build a production profile.")
    lo, hi = SOLAR_WINDOW
    for m in range(12):
        share = float(monthly[m]) / (hi - lo)
        for h in range(lo, hi):
            P[m][h] = share
    annual = float(sum(monthly))
    return P, annual, f"monthly fallback (kWh spread across {lo}:00–{hi}:00)"


# ---- parsing: URDB tariff -> month x hour first-tier rate matrix ----------------
def usable_tariffs(items: list) -> tuple[list, int]:
    """Tariffs with an energy-rate structure and both schedules; count skipped."""
    keep = []
    for t in items:
        if (t.get("energyratestructure") and t.get("energyweekdayschedule")
                and t.get("energyweekendschedule")):
            keep.append(t)
    return keep, len(items) - len(keep)


def first_tier_rates(tariff: dict) -> tuple[list[float], bool]:
    """Per-period first-tier $/kWh (rate + adj); flag if any period is tiered."""
    rates, tiered = [], False
    for period in tariff["energyratestructure"]:
        if not period:
            rates.append(0.0)
            continue
        tier0 = period[0]
        rates.append(float(tier0.get("rate", 0.0)) + float(tier0.get("adj", 0.0)))
        if len(period) > 1:
            tiered = True
    return rates, tiered


def rate_matrix(tariff: dict) -> tuple[list[list[float]], bool]:
    """R[12][24]: weekday/weekend-blended first-tier $/kWh by month and hour."""
    rates, tiered = first_tier_rates(tariff)
    wd, we = tariff["energyweekdayschedule"], tariff["energyweekendschedule"]
    if (len(wd) != 12 or len(we) != 12
            or any(not isinstance(r, list) or len(r) != 24 for r in wd + we)):
        fail(f"tariff '{tariff.get('name')}' has a malformed 12x24 schedule — "
             "pick another with --tariff N (see --list-tariffs).")
    R = [[0.0] * 24 for _ in range(12)]
    for m in range(12):
        for h in range(24):
            pw, pe = int(wd[m][h]), int(we[m][h])
            if pw >= len(rates) or pe >= len(rates):
                fail(f"tariff '{tariff.get('name')}' schedule points at a period "
                     "its rate structure doesn't define — pick another tariff.")
            R[m][h] = WEEKDAY_FRAC * rates[pw] + (1 - WEEKDAY_FRAC) * rates[pe]
    return R, tiered


def tariff_weighted_rate(P: list[list[float]], R: list[list[float]]) -> float:
    """$/kWh the grid would have charged for the energy the panels make instead.

    Element-wise accumulation in m-major/h-minor order, matching the demo's JS
    mirror exactly — different summation order flips rounding boundaries.
    """
    num = den = 0.0
    for m in range(12):
        for h in range(24):
            num += P[m][h] * R[m][h]
            den += P[m][h]
    if den <= 0:
        fail("PVWatts reports zero annual production — nothing to weight. "
             "Check tilt/azimuth/system size.")
    return num / den


# ---- the pro forma itself --------------------------------------------------------
def npv(savings_y1: float, net_cost: float) -> float:
    # iterated products, not ** — libm pow differs by an ulp from JS engines' Math.pow;
    # multiplication is IEEE-exact everywhere, so the demo's JS mirror lands bit-identical
    flows, deg, disc = 0.0, 1.0, 1.0
    for _ in range(NPV_YEARS):
        disc *= 1 + DISCOUNT                   # (1+r)^t
        flows += savings_y1 * deg / disc       # deg = (1-d)^(t-1)
        deg *= 1 - DEGRADATION
    return flows - net_cost


def build_proforma(args, pv: dict, tariff: dict, prod_path: str,
                   P: list[list[float]], annual_raw: float) -> dict:
    R, tiered = rate_matrix(tariff)
    r_tw = tariff_weighted_rate(P, R)

    gen = annual_raw * args.derate                      # year-1 kWh after roof-walk derate
    yield_kwp = gen / args.kw
    self_kwh = gen * args.self_consumption
    export_kwh = gen - self_kwh
    self_val = self_kwh * r_tw
    export_val = export_kwh * args.export_rate
    savings = self_val + export_val
    cost = args.kw * 1000.0 * args.cost_per_watt
    itc = cost * ITC
    net = cost - itc
    payback = net / savings if savings > 0 else float("inf")

    # the reason to buy less: the next kWp past real-time self-consumption is
    # mostly exported, so value it at the export rate alone (the note's lower bound)
    marg_gen = yield_kwp * MARGINAL_KWP
    marg_val = marg_gen * args.export_rate
    marg_net = MARGINAL_KWP * 1000.0 * args.cost_per_watt * (1 - ITC)
    marg_payback = marg_net / marg_val if marg_val > 0 else float("inf")

    # parity point rounded with JS Math.round semantics (floor(x+0.5)), not Python's
    # half-even round() — keeps the demo mirror exact even at a .5 rounding boundary
    parity_er = math.floor(r_tw * 1e4 + 0.5) / 1e4
    sens = []
    for er in sorted({0.0, 0.05, 0.10, parity_er}):
        s = self_val + export_kwh * er
        sens.append((er, s, net / s if s > 0 else float("inf")))

    st = pv.get("station_info", {})
    station = " ".join(str(x) for x in [st.get("weather_data_source", "?"),
                                        st.get("solar_resource_file", "")] if x)
    return {
        "r_tw": r_tw, "tiered": tiered, "gen": gen, "yield_kwp": yield_kwp,
        "self_kwh": self_kwh, "export_kwh": export_kwh, "self_val": self_val,
        "export_val": export_val, "savings": savings, "cost": cost, "itc": itc,
        "net": net, "payback": payback, "marg_val": marg_val,
        "marg_payback": marg_payback, "npv": npv(savings, net), "sens": sens,
        "station": station, "prod_path": prod_path,
    }


def yrs(v: float) -> str:
    return "never" if v == float("inf") else f"{v:.1f}"


def proforma_rows(args, m: dict, tariff: dict, site: str) -> list[list]:
    tariff_name = f"{tariff.get('utility', '?')} — {tariff.get('name', '?')}"
    tier_note = "first-tier rates; tiered usage allowances not modeled" if m["tiered"] else ""
    return [
        [1, "Site", site, "lat, lon", ""],
        [2, "Weather data", m["station"], "", "NREL NSRDB TMY via PVWatts v8 — typical year, not your weather"],
        [3, "System size", f"{args.kw:g}", "kWp DC", "yours to vary; see marginal row"],
        [4, "Tilt / azimuth", f"{args.tilt:g} / {args.azimuth:g}", "degrees", ""],
        [5, "PVWatts system losses", f"{PVWATTS_LOSSES:g}", "%", "v8 default; includes ~3% generic shading"],
        [6, "Shading derate — roof walk", f"{args.derate:g}", "x", "walk the roof; satellites miss the 4pm tree"],
        [7, "Specific yield (after derate)", f"{m['yield_kwp']:.0f}", "kWh/kWp/yr", m["prod_path"]],
        [8, "Year-1 generation", f"{m['gen']:.0f}", "kWh/yr", ""],
        [9, "Tariff", tariff_name, "", f"URDB label {tariff.get('label', '?')}"],
        [10, "Tariff-weighted import rate", f"{m['r_tw']:.4f}", "$/kWh", "weighted by WHEN the panels produce; " + (tier_note or "first-tier rates")],
        [11, "Export credit", f"{args.export_rate:g}", "$/kWh", "set by you — URDB rarely encodes post-NEM-3.0 export schedules"],
        [12, "Self-consumption ratio", f"{args.self_consumption:g}", "x", "napkin knob; replace with interval-data analysis for a lender"],
        [13, "Self-consumed energy", f"{m['self_kwh']:.0f}", "kWh/yr", f"${m['self_val']:.0f}/yr at the weighted import rate"],
        [14, "Exported energy", f"{m['export_kwh']:.0f}", "kWh/yr", f"${m['export_val']:.0f}/yr at the export credit"],
        [15, "Annual savings, year 1", f"{m['savings']:.0f}", "$/yr", ""],
        [16, "Installed cost", f"{m['cost']:.0f}", "$", f"@ ${args.cost_per_watt:.2f}/Wp"],
        [17, "Federal ITC (30%)", f"-{m['itc']:.0f}", "$", ""],
        [18, "Net cost", f"{m['net']:.0f}", "$", ""],
        [19, "Simple payback", yrs(m["payback"]), "yr", "net cost / year-1 savings; no escalation on purpose"],
        [20, f"25-yr NPV @ {DISCOUNT:.0%}", f"{m['npv']:.0f}", "$", f"{DEGRADATION:.1%}/yr panel degradation, flat tariff"],
    ]


def write_csv(path: Path, args, m: dict, tariff: dict, site: str, source_line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
        w.writerow([f"# solar-sizing honest pro forma — proforma.py, {now}"])
        w.writerow([f"# data: {source_line}"])
        w.writerow(["# not a quote, not sizing advice; the note's first instruction is to walk the roof"])
        w.writerow(["row", "item", "value", "unit", "note"])
        w.writerows(proforma_rows(args, m, tariff, site))
        w.writerow(["M1", "Marginal next-kWp payback", yrs(m["marg_payback"]), "yr",
                    f"the next kWp earns ~${m['marg_val']:.0f}/yr at the export credit "
                    f"against ${MARGINAL_KWP * 1000 * args.cost_per_watt * (1 - ITC):.0f} net — "
                    "the number no configurator shows you"])
        for i, (er, s, pb) in enumerate(m["sens"], 1):
            w.writerow([f"S{i}", "Sensitivity — export credit", f"{er:.4f}", "$/kWh",
                        f"savings ${s:.0f}/yr, payback {yrs(pb)} yr"])


def print_summary(args, m: dict, tariff: dict) -> None:
    print(f"\n  {args.kw:g} kWp · {m['gen']:.0f} kWh/yr after a {args.derate:g} roof-walk derate")
    print(f"  tariff: {tariff.get('utility', '?')} — {tariff.get('name', '?')}")
    print(f"  tariff-weighted import rate ${m['r_tw']:.3f}/kWh · export credit ${args.export_rate:g}/kWh")
    print(f"  net cost ${m['net']:,.0f} after ITC · savings ${m['savings']:,.0f}/yr"
          f" · simple payback {yrs(m['payback'])} yr · 25-yr NPV ${m['npv']:,.0f}")
    print(f"  the reason to buy less: the marginal kWp pays back in {yrs(m['marg_payback'])} yr "
          f"at your export credit\n")


# ---- CLI -------------------------------------------------------------------------
def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="proforma.py",
        description="Honest 20-row solar pro forma on live federal data "
                    "(NREL PVWatts v8 production + OpenEI URDB tariffs).",
        epilog="Examples:\n"
               "  python3 proforma.py --lat 37.3382 --lon -121.8863 --kw 7.2\n"
               "  python3 proforma.py --address '200 E Santa Clara St, San Jose CA' --list-tariffs\n"
               "  python3 proforma.py --lat 37.34 --lon -121.89 --kw 7.2 --tariff 2 --export-rate 0.05\n"
               "  python3 proforma.py --fixtures   # offline parse check, no network\n\n"
               "Key: --api-key > NREL_API_KEY env > DEMO_KEY (30 req/IP/hr, 50/day — api.data.gov limits).",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lat", type=float, help="site latitude (PVWatts v8 requires coordinates)")
    p.add_argument("--lon", type=float, help="site longitude")
    p.add_argument("--address", help="street address — tariff lookup only; PVWatts v8 "
                                     "retired the address parameter, so production still needs --lat/--lon")
    p.add_argument("--kw", type=float, help="system size, kWp DC (e.g. the size on your quote)")
    p.add_argument("--tilt", type=float, default=20.0, help="array tilt, degrees (default 20)")
    p.add_argument("--azimuth", type=float, default=180.0, help="array azimuth, degrees (default 180 = south)")
    p.add_argument("--derate", type=float, default=0.85,
                   help="roof-walk shading derate (default 0.85 — the note's honest default; 1.0 = clear sky)")
    p.add_argument("--self-consumption", type=float, default=0.55,
                   help="fraction of generation used in real time (default 0.55)")
    p.add_argument("--export-rate", type=float, default=0.05,
                   help="$/kWh credited for exports (default 0.05, NEM-3.0-ish; set yours)")
    p.add_argument("--cost-per-watt", type=float, default=3.00,
                   help="installed $/Wp (default 3.00 — NREL Q4 2025 residential benchmark)")
    p.add_argument("--sector", default="Residential",
                   choices=["Residential", "Commercial", "Industrial", "Lighting"])
    p.add_argument("--tariff", type=int, default=0, metavar="N",
                   help="index of the URDB tariff to use (default 0; see --list-tariffs)")
    p.add_argument("--list-tariffs", action="store_true",
                   help="fetch and print the tariffs URDB returns for the location, then exit")
    p.add_argument("--timeframe", default="hourly", choices=["hourly", "monthly"],
                   help="PVWatts resolution (default hourly — exact production weighting)")
    p.add_argument("--out", default="proforma.csv", help="output CSV path (default proforma.csv)")
    p.add_argument("--api-key", help="NREL/data.gov API key (else NREL_API_KEY env, else DEMO_KEY)")
    p.add_argument("--fixtures", action="store_true",
                   help="run the pipeline on the bundled doc-sourced fixtures — no network")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    if args.fixtures:
        print("fixtures run — parsing the bundled doc-sourced samples; zero network calls.")
        try:
            pv = json.loads((FIXTURES_DIR / "pvwatts-sample.json").read_text())
            urdb = json.loads((FIXTURES_DIR / "urdb-sample.json").read_text())
        except FileNotFoundError as e:
            fail(f"fixture missing: {e.filename} — fixtures/ ships with the repo.")
        if args.kw is None:
            args.kw = float(pv["inputs"]["system_capacity"])  # the doc example's 4 kW
        site = f"{pv['inputs']['lat']}, {pv['inputs']['lon']} (doc example)"
        source = ("DOC-SOURCED FIXTURES — PVWatts v8 docs example response + "
                  "schema-built URDB sample; illustrative, no live API was called")
    else:
        key = args.api_key or os.environ.get("NREL_API_KEY") or "DEMO_KEY"
        if key == "DEMO_KEY":
            print("using DEMO_KEY — api.data.gov caps it at 30 requests/IP/hour, 50/day; "
                  "free registered keys (https://developer.nrel.gov/signup/) get 1,000/hour.")
        if args.list_tariffs:
            if args.lat is None and not args.address:
                fail("--list-tariffs needs --lat/--lon or --address.")
            urdb = fetch_urdb(key, args.lat, args.lon, args.address, args.sector)
            tariffs, skipped = usable_tariffs(urdb.get("items", []))
            if not tariffs:
                fail("URDB returned no tariffs with an energy-rate schedule for that "
                     "location/sector — try --sector Commercial, or check the address.")
            print(f"\n  {len(tariffs)} usable tariff(s)"
                  + (f" ({skipped} skipped — no energy-rate schedule)" if skipped else "") + ":")
            for i, t in enumerate(tariffs):
                start = datetime.fromtimestamp(t["startdate"], tz=timezone.utc).strftime("%Y-%m-%d") \
                    if t.get("startdate") else "?"
                print(f"  [{i}] {t.get('utility', '?')} — {t.get('name', '?')} (effective {start})")
            print("\n  pick one with --tariff N. URDB is community-maintained; open the rate's "
                  "URI and check effective dates before trusting it for a signature.")
            return 0
        if args.kw is None:
            fail("--kw is required (the size on your quote, in kWp DC).")
        if args.lat is None or args.lon is None:
            if args.address:
                fail("PVWatts v8 takes coordinates only (the address parameter was retired "
                     "after v6). Long-press your roof in a maps app and pass --lat/--lon; "
                     "your --address still drives the tariff lookup.")
            fail("need --lat and --lon (or --fixtures for the offline check).")
        pv = fetch_pvwatts(key, args.lat, args.lon, args.kw, args.tilt,
                           args.azimuth, args.timeframe)
        urdb = fetch_urdb(key, args.lat, args.lon, args.address, args.sector)
        site = f"{args.lat}, {args.lon}"
        st = pv.get("station_info", {})
        source = (f"NREL PVWatts v8 ({st.get('weather_data_source', '?')}) + OpenEI URDB "
                  f"version=latest, fetched {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")

    if args.kw <= 0:
        fail("--kw must be positive.")
    if not 0 < args.derate <= 1:
        fail("--derate must be in (0, 1].")
    if not 0 <= args.self_consumption <= 1:
        fail("--self-consumption must be in [0, 1].")
    if args.export_rate < 0:
        fail("--export-rate must be >= 0 (it's a $/kWh credit, not a charge).")
    if args.cost_per_watt <= 0:
        fail("--cost-per-watt must be positive ($/Wp installed).")

    tariffs, skipped = usable_tariffs(urdb.get("items", []))
    if not tariffs:
        fail("URDB returned no tariffs with an energy-rate schedule here — "
             "try --sector Commercial or a corrected location.")
    if not 0 <= args.tariff < len(tariffs):
        fail(f"--tariff {args.tariff} is out of range; {len(tariffs)} usable tariff(s) "
             "returned — run --list-tariffs to see them.")
    tariff = tariffs[args.tariff]
    if skipped:
        print(f"note: {skipped} tariff(s) skipped — no energy-rate schedule (demand-only riders etc.)")
    if args.tariff == 0 and len(tariffs) > 1:
        print(f"note: using tariff [0] of {len(tariffs)} — run --list-tariffs and pick "
              "yours with --tariff N; the default is whatever URDB listed first, not 'best'.")

    P, annual_raw, prod_path = production_matrix(pv["outputs"])
    m = build_proforma(args, pv, tariff, prod_path, P, annual_raw)
    print_summary(args, m, tariff)
    out = Path(args.out)
    write_csv(out, args, m, tariff, site, source)
    print(f"wrote {out} — 20 rows + marginal + export-rate sensitivity, provenance in the header.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
