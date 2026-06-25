#!/usr/bin/env python3
"""proforma.py — the honest 20-row solar pro forma, on live federal + EU data.

Pipeline (same as demo.html's "Live" tab, server-side):

  1. Production, from whichever source answers (no single point of failure):
       - NREL PVWatts v8  (developer.nrel.gov)  — US, NSRDB TMY, needs an API key.
       - EU PVGIS v5.2    (re.jrc.ec.europa.eu) — global, keyless, hourly 2005-2015.
     --source auto (default) tries PVWatts, then falls back to PVGIS if NREL is
     unreachable or no key is set. Either way you get an 8760-hour profile.
  2. A second source + NASA POWER are pulled as a CROSS-CHECK and the spread is
     reported; >~8% disagreement is flagged. Multi-source agreement, shown.
  3. OpenEI URDB tariffs (api.openei.org), by lat/lon, then by --utility name,
     then a manual --import-rate. URDB's lat/lon match misses some utilities
     (e.g. PSEG Long Island / LIPA); the name lookup and the manual rate are the
     escape hatches so the tool never dead-ends on your own utility.
  4. The source note's honest arithmetic on those numbers: production-weighted
     tariff rate, roof-walk shading derate, NEM-3.0-style export credit,
     self-consumption split, ITC, simple payback, 25-yr NPV, and the
     marginal-next-kWp number no configurator shows you.

Split arrays: --kw, --tilt, --azimuth accept comma lists, one entry per roof
plane (e.g. --kw 5,5 --tilt 30,30 --azimuth 123,303 for a real, off-cardinal
E/W roof). Production matrices sum; the pro forma runs on the combined array.

Outputs proforma.csv (20 rows + provenance + cross-check + sensitivity) and a
terminal summary.

API key (PVWatts only; PVGIS and NASA need none): --api-key flag, else
NREL_API_KEY env, else DEMO_KEY (30 req/IP/hour, 50/day on api.data.gov; a free
registered key https://api.data.gov/signup/ gets 1,000/hour and drives both
NREL endpoints). The key is sent only to the NREL endpoints, never written to
disk or logged (URLs are key-redacted before printing).

Offline check (no network, used by CI and the author):
  python3 proforma.py --fixtures
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
# Federal residential ITC (Section 25D) was 30% through 2025, but the One Big
# Beautiful Bill Act (2025-07-04) ended it for OWNED installs placed in service
# after 2025-12-31. So --itc defaults to 0.0 (2026 owned reality); third-party
# leases keep the Section 48E business ITC (30%) through 2027, and state credits
# (e.g. NY's 25% capped at $5,000) go in --state-credit.
DISCOUNT = 0.05            # NPV discount rate (the note's FIG.1 uses 5%)
DEGRADATION = 0.005        # panel output degradation per year (industry 0.5%)
NPV_YEARS = 25
PVWATTS_LOSSES = 14.0      # system losses, %; includes a generic ~3% shading
                           # allowance — the roof-walk derate stacks on top.
                           # Used as the loss input to BOTH PVWatts and PVGIS so
                           # the two sources are compared on equal footing.
ARRAY_TYPE = 1             # fixed, roof-mounted (PVWatts)
MODULE_TYPE = 0            # standard crystalline (PVWatts)
WEEKDAY_FRAC = 5.0 / 7.0   # blend weekday/weekend tariff schedules; TMY data has
                           # no real calendar, so we weight rather than invent one
SOLAR_WINDOW = (9, 17)     # monthly fallback only: spread each month's kWh evenly
DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
MARGINAL_KWP = 1.0         # the "next kWp" of the note's reason-to-buy-less row
CROSSCHECK_FLAG = 0.08     # flag if two production sources disagree by more

PVWATTS_URL = "https://developer.nrel.gov/api/pvwatts/v8.json"
PVGIS_URL = "https://re.jrc.ec.europa.eu/api/v5_2/seriescalc"
NASA_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"
URDB_URL = "https://api.openei.org/utility_rates"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def fail(msg: str) -> "NoReturn":  # noqa: F821
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"note: {msg}", file=sys.stderr)


# ---- HTTP -----------------------------------------------------------------------
def get_json(base: str, params: dict, *, key: str | None = None, timeout: int = 90) -> dict:
    url = base + "?" + urllib.parse.urlencode(params)
    redacted = url.replace(key, "***") if key else url
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:600]
        except Exception:
            pass
        hint = ""
        if e.code in (401, 403):
            hint = ("\nhint: on DEMO_KEY this endpoint may have exhausted its 30/hour-per-IP "
                    "allowance or may need a registered key — free at https://api.data.gov/signup/.")
        elif e.code == 422:
            hint = "\nhint: a parameter failed validation; the API's own message above says which."
        raise APIError(f"HTTP {e.code} from {redacted}\n{body}{hint}")
    except urllib.error.URLError as e:
        raise APIError(f"could not reach {base} — {e.reason}")


class APIError(Exception):
    pass


def compass_to_pvgis_aspect(azimuth: float) -> float:
    """PVWatts/compass azimuth (0=N,90=E,180=S,270=W) -> PVGIS aspect (0=S,90=W,-90=E)."""
    a = (azimuth - 180.0) % 360.0
    return a - 360.0 if a > 180.0 else a


# ---- production backends: each returns (P[12][24] kWh, annual kWh, path) --------
def production_pvwatts(key: str, lat: float, lon: float, kw: float, tilt: float,
                       azimuth: float) -> tuple[list[list[float]], float, str, dict]:
    data = get_json(PVWATTS_URL, {
        "api_key": key, "lat": lat, "lon": lon, "system_capacity": kw,
        "tilt": tilt, "azimuth": azimuth, "array_type": ARRAY_TYPE,
        "module_type": MODULE_TYPE, "losses": PVWATTS_LOSSES, "timeframe": "hourly",
    }, key=key)
    if data.get("errors"):
        raise APIError("PVWatts returned errors: " + "; ".join(map(str, data["errors"])))
    out = data.get("outputs", {})
    ac = out.get("ac")
    if not (isinstance(ac, list) and len(ac) == 8760):
        raise APIError("PVWatts response carries no 8760-hour 'ac' profile.")
    P = [[0.0] * 24 for _ in range(12)]
    i = 0
    for m, days in enumerate(DAYS_IN_MONTH):
        for _ in range(days):
            for h in range(24):
                P[m][h] += float(ac[i]) / 1000.0
                i += 1
    annual = sum(P[m][h] for m in range(12) for h in range(24))
    st = data.get("station_info", {})
    meta = {"station": " ".join(str(x) for x in [st.get("weather_data_source", "?"),
            st.get("solar_resource_file", "")] if x), "raw": data}
    return P, annual, "PVWatts v8 hourly (NSRDB TMY)", meta


def production_pvgis(lat: float, lon: float, kw: float, tilt: float,
                     azimuth: float) -> tuple[list[list[float]], float, str, dict]:
    aspect = compass_to_pvgis_aspect(azimuth)
    data = get_json(PVGIS_URL, {
        "lat": lat, "lon": lon, "pvcalculation": 1, "peakpower": kw,
        "loss": PVWATTS_LOSSES, "angle": tilt, "aspect": round(aspect, 2),
        "mountingplace": "building", "pvtechchoice": "crystSi", "outputformat": "json",
    })
    rows = data.get("outputs", {}).get("hourly")
    if not isinstance(rows, list) or not rows:
        raise APIError("PVGIS seriescalc returned no hourly rows: " + str(data)[:200])
    # PVGIS time is UTC; shift to local standard time (round(lon/15)) so the
    # month x hour buckets line up with URDB schedules, like PVWatts already does.
    off = int(round(lon / 15.0))
    P = [[0.0] * 24 for _ in range(12)]
    years = set()
    for r in rows:
        t = str(r.get("time", ""))            # "YYYYMMDD:HHMM"
        if len(t) < 11:
            continue
        years.add(t[:4])
        m = int(t[4:6]) - 1
        h = (int(t[9:11]) + off) % 24
        P[m][h] += float(r.get("P", 0.0)) / 1000.0
    ny = max(1, len(years))
    for m in range(12):
        for h in range(24):
            P[m][h] /= ny
    annual = sum(P[m][h] for m in range(12) for h in range(24))
    rd = data.get("inputs", {}).get("meteo_data", {}).get("radiation_db", "PVGIS")
    return P, annual, f"PVGIS v5.2 hourly ({rd}, {ny}-yr avg)", {"station": rd, "raw": data}


def nasa_resource(lat: float, lon: float) -> float | None:
    """Annual GHI (kWh/m2/yr) from NASA POWER — an independent resource cross-check."""
    try:
        d = get_json(NASA_URL, {"parameters": "ALLSKY_SFC_SW_DWN", "community": "RE",
                                "longitude": lon, "latitude": lat, "format": "json"}, timeout=40)
        ann = d["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"].get("ANN")
        return float(ann) * 365.0 if ann is not None else None
    except Exception:
        return None


def get_production(source: str, key: str, lat: float, lon: float, kw: float,
                   tilt: float, azimuth: float) -> tuple[list[list[float]], float, str, dict]:
    """Dispatch one plane to a source; 'auto' tries PVWatts then PVGIS."""
    if source == "pvwatts":
        return production_pvwatts(key, lat, lon, kw, tilt, azimuth)
    if source == "pvgis":
        return production_pvgis(lat, lon, kw, tilt, azimuth)
    # auto
    if key:
        try:
            return production_pvwatts(key, lat, lon, kw, tilt, azimuth)
        except APIError as e:
            warn(f"PVWatts unavailable ({str(e).splitlines()[0]}); falling back to PVGIS.")
    return production_pvgis(lat, lon, kw, tilt, azimuth)


def add_matrix(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    return [[a[m][h] + b[m][h] for h in range(24)] for m in range(12)]


# ---- URDB tariff parsing (unchanged math) --------------------------------------
def fetch_urdb(key: str, lat, lon, address, utility, sector) -> dict:
    params = {"version": "latest", "format": "json", "api_key": key,
              "sector": sector, "detail": "full", "limit": 30}
    if utility:
        params["ratesforutility"] = utility
    elif address:
        params["address"] = address
    else:
        params["lat"], params["lon"] = lat, lon
    return get_json(URDB_URL, params, key=key, timeout=40)


def usable_tariffs(items: list) -> tuple[list, int]:
    keep = [t for t in items if t.get("energyratestructure")
            and t.get("energyweekdayschedule") and t.get("energyweekendschedule")]
    return keep, len(items) - len(keep)


def first_tier_rates(tariff: dict) -> tuple[list[float], bool]:
    rates, tiered = [], False
    for period in tariff["energyratestructure"]:
        if not period:
            rates.append(0.0)
            continue
        t0 = period[0]
        rates.append(float(t0.get("rate", 0.0)) + float(t0.get("adj", 0.0)))
        if len(period) > 1:
            tiered = True
    return rates, tiered


def rate_matrix(tariff: dict) -> tuple[list[list[float]], bool]:
    rates, tiered = first_tier_rates(tariff)
    wd, we = tariff["energyweekdayschedule"], tariff["energyweekendschedule"]
    if (len(wd) != 12 or len(we) != 12
            or any(not isinstance(r, list) or len(r) != 24 for r in wd + we)):
        fail(f"tariff '{tariff.get('name')}' has a malformed 12x24 schedule — pick another with --tariff N.")
    R = [[0.0] * 24 for _ in range(12)]
    for m in range(12):
        for h in range(24):
            pw, pe = int(wd[m][h]), int(we[m][h])
            if pw >= len(rates) or pe >= len(rates):
                fail(f"tariff '{tariff.get('name')}' points at an undefined rate period — pick another.")
            R[m][h] = WEEKDAY_FRAC * rates[pw] + (1 - WEEKDAY_FRAC) * rates[pe]
    return R, tiered


def manual_rate_matrix(rate: float) -> tuple[list[list[float]], bool]:
    return [[rate] * 24 for _ in range(12)], False


def tariff_weighted_rate(P, R) -> float:
    num = den = 0.0
    for m in range(12):
        for h in range(24):
            num += P[m][h] * R[m][h]
            den += P[m][h]
    if den <= 0:
        fail("zero annual production — nothing to weight. Check tilt/azimuth/size.")
    return num / den


# ---- the pro forma (unchanged arithmetic) --------------------------------------
def npv(savings_y1: float, net_cost: float) -> float:
    flows, deg, disc = 0.0, 1.0, 1.0
    for _ in range(NPV_YEARS):
        disc *= 1 + DISCOUNT
        flows += savings_y1 * deg / disc
        deg *= 1 - DEGRADATION
    return flows - net_cost


def build_proforma(args, R, tiered, kw_total, prod_path, P, annual_raw) -> dict:
    r_tw = tariff_weighted_rate(P, R)
    gen = annual_raw * args.derate
    yield_kwp = gen / kw_total
    self_kwh = gen * args.self_consumption
    export_kwh = gen - self_kwh
    self_val = self_kwh * r_tw
    export_val = export_kwh * args.export_rate
    savings = self_val + export_val
    cost = kw_total * 1000.0 * args.cost_per_watt
    itc = cost * args.itc
    net = cost - itc - args.state_credit
    payback = net / savings if savings > 0 else float("inf")
    marg_gen = yield_kwp * MARGINAL_KWP
    marg_val = marg_gen * args.export_rate
    marg_net = MARGINAL_KWP * 1000.0 * args.cost_per_watt * (1 - args.itc)
    marg_payback = marg_net / marg_val if marg_val > 0 else float("inf")
    parity_er = math.floor(r_tw * 1e4 + 0.5) / 1e4
    sens = []
    for er in sorted({0.0, 0.05, 0.10, parity_er}):
        s = self_val + export_kwh * er
        sens.append((er, s, net / s if s > 0 else float("inf")))
    return {"r_tw": r_tw, "tiered": tiered, "gen": gen, "yield_kwp": yield_kwp,
            "self_kwh": self_kwh, "export_kwh": export_kwh, "self_val": self_val,
            "export_val": export_val, "savings": savings, "cost": cost, "itc": itc,
            "state_credit": args.state_credit,
            "net": net, "payback": payback, "marg_val": marg_val,
            "marg_payback": marg_payback, "npv": npv(savings, net), "sens": sens,
            "prod_path": prod_path}


def yrs(v: float) -> str:
    return "never" if v == float("inf") else f"{v:.1f}"


def proforma_rows(args, m, tariff_name, kw_total, planes_desc, site) -> list[list]:
    tier = "first-tier rates; tiered allowances not modeled" if m["tiered"] else "first-tier rates"
    return [
        [1, "Site", site, "lat, lon", ""],
        [2, "Production source", m["prod_path"], "", "auto: PVWatts if reachable, else PVGIS"],
        [3, "System size", f"{kw_total:g}", "kWp DC", planes_desc],
        [4, "Planes (tilt/azimuth)", planes_desc, "deg", "azimuth = compass; 90=E,180=S,270=W"],
        [5, "System losses", f"{PVWATTS_LOSSES:g}", "%", "applied to both sources; includes ~3% generic shading"],
        [6, "Shading derate — roof walk", f"{args.derate:g}", "x", "walk the roof; satellites miss the 4pm tree"],
        [7, "Specific yield (after derate)", f"{m['yield_kwp']:.0f}", "kWh/kWp/yr", m["prod_path"]],
        [8, "Year-1 generation", f"{m['gen']:.0f}", "kWh/yr", ""],
        [9, "Tariff", tariff_name, "", ""],
        [10, "Tariff-weighted import rate", f"{m['r_tw']:.4f}", "$/kWh", "weighted by WHEN the panels produce; " + tier],
        [11, "Export credit", f"{args.export_rate:g}", "$/kWh", "set by you — URDB rarely encodes post-NEM-3.0 exports"],
        [12, "Self-consumption ratio", f"{args.self_consumption:g}", "x", "napkin knob; replace with interval data for a lender"],
        [13, "Self-consumed energy", f"{m['self_kwh']:.0f}", "kWh/yr", f"${m['self_val']:.0f}/yr at the weighted import rate"],
        [14, "Exported energy", f"{m['export_kwh']:.0f}", "kWh/yr", f"${m['export_val']:.0f}/yr at the export credit"],
        [15, "Annual savings, year 1", f"{m['savings']:.0f}", "$/yr", ""],
        [16, "Installed cost", f"{m['cost']:.0f}", "$", f"@ ${args.cost_per_watt:.2f}/Wp"],
        [17, f"Federal ITC ({args.itc:.0%})", f"-{m['itc']:.0f}", "$",
         "Section 25D ended 12/31/2025 for owned installs; default 0 (leases keep 48E to 2027)"],
        [18, "State credit", f"-{m['state_credit']:.0f}", "$", "e.g. NY 25% capped $5,000; set with --state-credit"],
        [19, "Net cost", f"{m['net']:.0f}", "$", ""],
        [20, "Simple payback", yrs(m["payback"]), "yr", "net cost / year-1 savings; no escalation on purpose"],
        [21, f"25-yr NPV @ {DISCOUNT:.0%}", f"{m['npv']:.0f}", "$", f"{DEGRADATION:.1%}/yr degradation, flat tariff"],
    ]


def write_csv(path, args, m, tariff_name, kw_total, planes_desc, site, source_line, cross) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
        w.writerow([f"# solar-sizing honest pro forma — proforma.py, {now}"])
        w.writerow([f"# data: {source_line}"])
        w.writerow(["# not a quote, not sizing advice; the note's first instruction is to walk the roof"])
        w.writerow(["row", "item", "value", "unit", "note"])
        w.writerows(proforma_rows(args, m, tariff_name, kw_total, planes_desc, site))
        w.writerow(["M1", "Marginal next-kWp payback", yrs(m["marg_payback"]), "yr",
                    f"the next kWp earns ~${m['marg_val']:.0f}/yr at the export credit — "
                    "the number no configurator shows you"])
        for tag, label, annual in cross:
            w.writerow([tag, "Cross-check", f"{annual:.0f}", "kWh/yr or kWh/m2/yr", label])
        for i, (er, s, pb) in enumerate(m["sens"], 1):
            w.writerow([f"S{i}", "Sensitivity — export credit", f"{er:.4f}", "$/kWh",
                        f"savings ${s:.0f}/yr, payback {yrs(pb)} yr"])


def print_summary(args, m, tariff_name, kw_total, cross) -> None:
    print(f"\n  {kw_total:g} kWp · {m['gen']:.0f} kWh/yr after a {args.derate:g} roof-walk derate "
          f"· {m['prod_path']}")
    print(f"  tariff: {tariff_name}")
    print(f"  tariff-weighted import rate ${m['r_tw']:.3f}/kWh · export credit ${args.export_rate:g}/kWh")
    print(f"  net cost ${m['net']:,.0f} after credits · savings ${m['savings']:,.0f}/yr"
          f" · simple payback {yrs(m['payback'])} yr · 25-yr NPV ${m['npv']:,.0f}")
    if cross:
        print("  cross-check: " + "; ".join(f"{lab} {a:,.0f}" for _, lab, a in cross))
    print(f"  the reason to buy less: the marginal kWp pays back in {yrs(m['marg_payback'])} yr "
          f"at your export credit\n")


# ---- CLI ------------------------------------------------------------------------
def _floats(s, name):
    try:
        return [float(x) for x in str(s).split(",")]
    except ValueError:
        fail(f"--{name} must be a number or comma list of numbers (got {s!r}).")


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="proforma.py",
        description="Honest 20-row solar pro forma on live data (PVWatts or PVGIS production + URDB tariffs).",
        epilog="Examples:\n"
               "  python3 proforma.py --lat 40.6675 --lon -73.6207 --kw 5,5 --tilt 30,30 --azimuth 123,303\n"
               "  python3 proforma.py --lat 40.67 --lon -73.64 --kw 7 --source pvgis --utility 'Long Island Power Authority'\n"
               "  python3 proforma.py --lat 40.67 --lon -73.64 --kw 7 --import-rate 0.24  # URDB has no rate for you\n"
               "  python3 proforma.py --fixtures   # offline parse check, no network\n",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--address", help="street address — tariff lookup only (URDB geocodes it)")
    p.add_argument("--kw", help="system size kWp DC; comma list = one per roof plane")
    p.add_argument("--tilt", default="20", help="array tilt deg (default 20); comma list per plane")
    p.add_argument("--azimuth", default="180", help="compass azimuth deg (default 180=S); comma list per plane")
    p.add_argument("--source", default="auto", choices=["auto", "pvwatts", "pvgis"],
                   help="production source (default auto: PVWatts if reachable, else PVGIS)")
    p.add_argument("--derate", type=float, default=0.85,
                   help="roof-walk shading derate (default 0.85; 0.85 suits a typical shaded roof, an "
                        "unshaded array wants ~0.95-1.0 — validated against real systems in validation/)")
    p.add_argument("--self-consumption", type=float, default=0.55)
    p.add_argument("--export-rate", type=float, default=0.05,
                   help="$/kWh for exported energy (default 0.05 = California NEM-3.0 worst case; the most "
                        "jurisdiction-specific knob -- e.g. NY PSEG-LI time-of-day net metering banks most solar "
                        "near 0.19, ~4x higher; set yours)")
    p.add_argument("--cost-per-watt", type=float, default=3.00)
    p.add_argument("--itc", type=float, default=0.0,
                   help="federal ITC fraction (default 0.0: Section 25D ended 12/31/2025 for owned 2026 "
                        "installs; was 0.30 through 2025; third-party leases keep Section 48E at 0.30 to 2027)")
    p.add_argument("--state-credit", type=float, default=0.0, metavar="DOLLARS",
                   help="state/local credit in dollars, subtracted from net cost (e.g. NY 25 percent capped $5000)")
    p.add_argument("--sector", default="Residential",
                   choices=["Residential", "Commercial", "Industrial", "Lighting"])
    p.add_argument("--utility", help="URDB utility name (fallback when lat/lon returns no tariff, e.g. 'Long Island Power Authority')")
    p.add_argument("--import-rate", type=float, help="manual flat $/kWh import rate — bypasses URDB entirely")
    p.add_argument("--tariff", type=int, default=0, metavar="N")
    p.add_argument("--list-tariffs", action="store_true")
    p.add_argument("--no-cross-check", action="store_true", help="skip the second-source + NASA cross-check")
    p.add_argument("--out", default="proforma.csv")
    p.add_argument("--api-key", help="NREL/data.gov API key (else NREL_API_KEY env, else DEMO_KEY)")
    p.add_argument("--fixtures", action="store_true")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    key = args.api_key or os.environ.get("NREL_API_KEY") or "DEMO_KEY"

    if args.fixtures:
        return run_fixtures(args)

    if args.lat is None or args.lon is None:
        fail("need --lat and --lon (or --fixtures for the offline check).")

    # tariff: manual rate, or URDB (lat/lon -> utility -> list)
    if args.import_rate is not None:
        if args.import_rate < 0:
            fail("--import-rate must be >= 0.")
        tariff_obj, tariff_name = None, f"manual flat rate ${args.import_rate:.4f}/kWh (URDB bypassed)"
    else:
        urdb = fetch_urdb(key, args.lat, args.lon, args.address, args.utility, args.sector)
        tariffs, skipped = usable_tariffs(urdb.get("items", []))
        if not tariffs and not args.utility:
            fail("URDB returned no usable tariff at these coordinates — some utilities (e.g. PSEG "
                 "Long Island / LIPA) aren't geocoded in URDB. Retry with --utility \"<exact name>\" "
                 "(try --list-tariffs --utility ...), or pass --import-rate <$/kWh>.")
        if args.list_tariffs:
            print(f"\n  {len(tariffs)} usable tariff(s):")
            for i, t in enumerate(tariffs):
                print(f"  [{i}] {t.get('utility','?')} — {t.get('name','?')}")
            print("\n  pick one with --tariff N.")
            return 0
        if not tariffs:
            fail(f"--utility {args.utility!r} returned no usable tariff; check the exact URDB name.")
        if not 0 <= args.tariff < len(tariffs):
            fail(f"--tariff {args.tariff} out of range; {len(tariffs)} usable — run --list-tariffs.")
        tariff_obj = tariffs[args.tariff]
        tariff_name = f"{tariff_obj.get('utility','?')} — {tariff_obj.get('name','?')}"
        if args.tariff == 0 and len(tariffs) > 1:
            warn(f"using tariff [0] of {len(tariffs)} — run --list-tariffs and pick yours with --tariff N.")

    if args.list_tariffs:
        return 0

    # planes
    if args.kw is None:
        fail("--kw is required (kWp DC; comma list for a split array).")
    kws = _floats(args.kw, "kw")
    tilts = _floats(args.tilt, "tilt")
    azs = _floats(args.azimuth, "azimuth")
    n = len(kws)
    if len(tilts) == 1:
        tilts *= n
    if len(azs) == 1:
        azs *= n
    if not (len(tilts) == len(azs) == n):
        fail("--kw, --tilt, --azimuth must have the same number of comma entries (one per plane).")
    if any(k <= 0 for k in kws):
        fail("each --kw must be positive.")
    if not 0 < args.derate <= 1:
        fail("--derate must be in (0, 1].")

    # production: sum planes, on the chosen source
    P = [[0.0] * 24 for _ in range(12)]
    annual = 0.0
    paths = []
    for k, t, a in zip(kws, tilts, azs):
        Pi, ann, path, _ = get_production(args.source, key, args.lat, args.lon, k, t, a)
        P = add_matrix(P, Pi)
        annual += ann
        paths.append(path)
    kw_total = sum(kws)
    prod_path = paths[0]
    planes_desc = "; ".join(f"{k:g}kW@{t:g}/{a:g}" for k, t, a in zip(kws, tilts, azs))

    # rate matrix
    if tariff_obj is None:
        R, tiered = manual_rate_matrix(args.import_rate)
    else:
        R, tiered = rate_matrix(tariff_obj)

    m = build_proforma(args, R, tiered, kw_total, prod_path, P, annual)

    # cross-check: alternate production source + NASA resource
    cross = []
    if not args.no_cross_check:
        alt = "pvgis" if "PVWatts" in prod_path else ("pvwatts" if key else None)
        if alt == "pvwatts":
            try:
                a2 = sum(get_production("pvwatts", key, args.lat, args.lon, k, t, a2_)[1]
                         for k, t, a2_ in zip(kws, tilts, azs))
                cross.append(("X1", "PVWatts annual", a2))
            except APIError:
                pass
        elif alt == "pvgis":
            try:
                a2 = sum(get_production("pvgis", key, args.lat, args.lon, k, t, a2_)[1]
                         for k, t, a2_ in zip(kws, tilts, azs))
                cross.append(("X1", "PVGIS annual", a2))
            except APIError:
                pass
        ghi = nasa_resource(args.lat, args.lon)
        if ghi:
            cross.append(("X2", "NASA POWER GHI (kWh/m2/yr)", ghi))
        if cross and cross[0][0] == "X1":
            spread = abs(cross[0][2] - annual) / annual if annual else 0
            if spread > CROSSCHECK_FLAG:
                warn(f"production sources disagree {spread:.0%} ({prod_path.split()[0]} {annual:.0f} vs "
                     f"{cross[0][1]} {cross[0][2]:.0f}) — check tilt/azimuth, or one source's TMY.")

    print_summary(args, m, tariff_name, kw_total, cross)
    out = Path(args.out)
    source_line = (f"{prod_path}; tariff {tariff_name}; "
                   f"fetched {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
    write_csv(out, args, m, tariff_name, kw_total, planes_desc,
              f"{args.lat}, {args.lon}", source_line, cross)
    print(f"wrote {out} — 20 rows + marginal + cross-check + sensitivity, provenance in the header.")
    return 0


def run_fixtures(args) -> int:
    print("fixtures run — parsing the bundled doc-sourced samples; zero network calls.")
    try:
        pv = json.loads((FIXTURES_DIR / "pvwatts-sample.json").read_text())
        urdb = json.loads((FIXTURES_DIR / "urdb-sample.json").read_text())
    except FileNotFoundError as e:
        fail(f"fixture missing: {e.filename} — fixtures/ ships with the repo.")
    kw = float(pv["inputs"]["system_capacity"])
    out = pv["outputs"]
    P = [[0.0] * 24 for _ in range(12)]
    monthly = out.get("ac_monthly")
    lo, hi = SOLAR_WINDOW
    for mm in range(12):
        share = float(monthly[mm]) / (hi - lo)
        for h in range(lo, hi):
            P[mm][h] = share
    annual = float(sum(monthly))
    tariffs, _ = usable_tariffs(urdb.get("items", []))
    if not tariffs:
        fail("fixture URDB has no usable tariff.")
    R, tiered = rate_matrix(tariffs[0])
    args.kw = str(kw)
    m = build_proforma(args, R, tiered, kw, "monthly fixture (offline)", P, annual)
    name = f"{tariffs[0].get('utility','?')} — {tariffs[0].get('name','?')}"
    print_summary(args, m, name, kw, [])
    write_csv(Path(args.out), args, m, name, kw, f"{kw:g}kW fixture",
              f"{pv['inputs']['lat']}, {pv['inputs']['lon']} (doc example)",
              "DOC-SOURCED FIXTURES — no live API called", [])
    print(f"wrote {args.out} (fixtures).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
