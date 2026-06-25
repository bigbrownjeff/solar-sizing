# solar-sizing

**The honest solar pro forma, on live data — with no single point of failure.** Type your roof's coordinates and the size on your quote; `proforma.py` pulls real hourly production from **whichever source answers** — NREL PVWatts v8 (US, needs a key) **or** EU PVGIS v5.2 (global, *keyless*) — and real filed tariffs from the OpenEI Utility Rate Database, then runs a twenty-row pro forma that weights savings by *when* the panels produce — not by the annual %-offset number configurators sell on. A NREL outage no longer breaks the tool: `--source auto` falls back to PVGIS automatically. `demo.html` does the same thing in the browser, beside a fully offline worked example, and **`index.html`** puts it on a live satellite map — drag your roof's panels, resize them, set tilt and azimuth, and the pro forma recomputes as you go.

The keyless path means you can run a complete pro forma with **zero signup** anywhere on Earth; the US key only buys you NREL's NSRDB TMY as the primary source.

From Jeff Pinto's note *[First-principles residential solar sizing](https://jeffpinto.com/notes/solar-sizing/)*: a twenty-row spreadsheet beats every online configurator, because the configurator has a structural incentive not to be honest — the installer is paid per watt installed, the configurator per lead generated. This repo is that spreadsheet showing its work against live public data — US federal (NREL, NASA) and EU (PVGIS) alike.

---

## 60-second quickstart — no signup needed

```bash
# US, default auto: PVWatts if reachable (DEMO_KEY), else PVGIS
python3 proforma.py --lat 37.3382 --lon -121.8863 --kw 7.2

# anywhere on Earth, no key, no signup — force the keyless EU source
python3 proforma.py --lat 37.3382 --lon -121.8863 --kw 7.2 --source pvgis

# a real split array: E/W roof, two 5 kW planes at 30° tilt, off-cardinal
python3 proforma.py --lat 40.6675 --lon -73.6207 --kw 5,5 --tilt 30,30 --azimuth 123,303
```

Stdlib only — no pip install. The keyless PVGIS path needs nothing at all. PVWatts with no key falls back to `DEMO_KEY`, which api.data.gov caps at **30 requests/IP/hour, 50/day** (a run here is 2–4 requests). A free registered key — https://api.data.gov/signup/, the same key drives both NREL endpoints — gets 1,000/hour:

```bash
export NREL_API_KEY=your-key-here
```

What you get: a terminal summary and `proforma.csv` — 20 rows (site, production source, tariff, tariff-weighted import rate, self-consumption split, ITC, net cost, simple payback, 25-yr NPV), plus the marginal-next-kWp row, a multi-source **cross-check** block, and an export-rate sensitivity block, with provenance in the header.

> Stuck on your own utility or a missing rate? Two escape hatches keep the tool from dead-ending — `--utility "<exact name>"` and `--import-rate <$/kWh>`, both covered under [Picking your actual tariff](#picking-your-actual-tariff).

## Production source — two models, no single point of failure

This is why the tool was rewritten. Production used to come from PVWatts alone, so a NREL outage or a missing key was a hard stop. Now there are two independent backends and `--source` chooses between them:

| `--source` | Backend | Coverage | Key? |
|---|---|---|---|
| `auto` *(default)* | PVWatts, **falling back to PVGIS** if NREL is unreachable or no key is set | US primary, global fallback | optional |
| `pvwatts` | NREL PVWatts v8 — NSRDB TMY hourly | US (and NSRDB's footprint) | **required** |
| `pvgis` | EU PVGIS v5.2 — `seriescalc` hourly, 2005–2015 averaged | **global** | **none** |

Either way you get a full 8760-hour profile, and PVGIS is given the *same* system-loss input as PVWatts so the two are compared on equal footing. The practical upshot: a registered NREL key buys you NSRDB TMY as the primary US source, but you never *need* it — `--source pvgis` runs a complete pro forma anywhere on Earth with no signup.

### Split arrays (multi-plane roofs)

`--kw`, `--tilt`, and `--azimuth` each accept a comma-list with **one entry per roof plane**, so an off-cardinal or split roof models honestly instead of being averaged into one fictional plane. The per-plane production matrices sum, and the pro forma runs on the combined array:

```bash
# a real E/W roof: 5 kW facing ~ESE (123°) + 5 kW facing ~WNW (303°), both at 30°
python3 proforma.py --lat 40.6675 --lon -73.6207 --kw 5,5 --tilt 30,30 --azimuth 123,303
```

A single value for `--tilt` or `--azimuth` is broadcast to every plane; otherwise the three lists must be the same length.

## Picking your actual tariff

URDB usually returns several tariffs for a location. The default is index 0 — whatever URDB listed first, not "best". List and pick:

```bash
python3 proforma.py --address '200 E Santa Clara St, San Jose CA' --list-tariffs
python3 proforma.py --lat 37.3382 --lon -121.8863 --kw 7.2 --tariff 2
```

**When URDB doesn't geocode your utility** — and it doesn't always; PSEG Long Island is a real example URDB returns nothing for by lat/lon — fall back to the utility *name*, which finds the filed tariffs anyway:

```bash
python3 proforma.py --lat 40.667 --lon -73.621 --kw 7 --utility "Long Island Power Authority"
```

**When URDB has no rate for you at all**, skip it entirely with a manual flat import rate:

```bash
python3 proforma.py --lat 40.667 --lon -73.621 --kw 7 --import-rate 0.24   # $/kWh, URDB bypassed
```

Between the lat/lon match, the `--utility` name lookup, and `--import-rate`, the tool no longer dead-ends on your own utility.

Note the asymmetry, stated honestly: **PVWatts v8 takes coordinates only** (its street-address parameter was retired after v6), so production always needs `--lat/--lon` — long-press your roof in any maps app. `--address` drives the tariff lookup alone; URDB geocodes it server-side.

## The honest knobs

```bash
python3 proforma.py --lat 37.34 --lon -121.89 --kw 7.2 \
  --derate 0.85 --self-consumption 0.55 --export-rate 0.05 --cost-per-watt 3.00
```

- `--derate` — the roof-walk shading derate (default 0.85). PVWatts' 14% system-loss default includes only a generic ~3% shading allowance; the redwood that shades your west face at 4pm is yours to count. Satellites miss it. Walk the roof. **Validated regime:** 0.85 fits a typical *shaded* roof; a genuinely unshaded, well-sited array wants ~0.95–1.0 — using 0.85 there under-predicts annual production by ~15% (see [`validation/`](./validation/VALIDATION.md)).
- `--export-rate` — $/kWh for exported energy (default $0.05, NEM-3.0-ish — California's worst case). **This is the single most jurisdiction-specific knob, and the easiest one to get wrong by importing another state's rule.** NY's PSEG-LI time-of-day net metering, by contrast, banks most solar near the ~$0.19 off-peak rate, nearly 4x higher (see [`validation/calculator-benchmark.md`](./validation/calculator-benchmark.md)). URDB rarely encodes post-NEM-3.0 export schedules, so this stays explicit and yours — and the CSV carries a sensitivity block across $0.00 / $0.05 / $0.10 / import-parity so you can see exactly what the export-rate assumption is worth.
- `--self-consumption` — fraction used in real time (default 0.55). The napkin knob: a lender-grade version replaces it with interval-data analysis.
- `--itc` / `--state-credit` — **the federal ITC now defaults to 0.** Section 25D (the 30% residential credit) expired 12/31/2025 for *owned* installs placed in service in 2026; third-party leases keep the §48E business ITC at 30% through 2027 (`--itc 0.30` models a lease or a pre-2026 install). State/local credits go in `--state-credit` as dollars (e.g. NY's 25%, capped at $5,000). Every consumer calculator benchmarked in [`validation/calculator-benchmark.md`](./validation/calculator-benchmark.md) still bakes in the expired 30% credit; this one doesn't.

## The 2026 model: battery, EV, and the export-rate squeeze

With the federal residential ITC gone and post-NEM-3.0 export credits at pennies, the 2026 question isn't "how big a system" — it's "what do you do with the kWh you can no longer sell back profitably." Three flags model that, and the first two are deliberately **separate worksheets** (they fold into total savings, but each prints its own line so you can see whether *it* pencils, not just the bundle):

```bash
python3 proforma.py --lat 40.6675 --lon -73.6207 --kw 7 --source pvgis \
  --import-rate 0.21 --export-rate 0.05 --battery-kwh 13.5 --ev-kwh 4000
```

- `--battery-kwh` / `--battery-cost` — a battery's whole residential value here is **arbitraging the export→import spread**: it stores solar you'd otherwise export at `--export-rate` and discharges it in the evening, displacing imports at the (higher) tariff rate. The model is honest-simple: `shifted_kWh = min(annual export, battery_kWh × 365 × 0.9)` (0.9 round-trip, ~one cycle/day), and `benefit/yr = shifted_kWh × (import − export rate)`. `--battery-cost` is **$/kWh installed** (default $1,000); there is **no federal ITC on the battery by default in 2026** — a third-party lease keeps the §48E business credit, noted in the code. The CSV gets its own B1–B5 block (capacity, cost, kWh shifted, benefit/yr, marginal simple-payback) and the terminal prints a one-line **verdict**. The honest punchline: a battery **pencils mainly when `--export-rate` is far below your import rate** — and it pencils *harder the lower the export rate goes*, because the spread it arbitrages widens. At export/import parity the battery is worth nothing. This is a daily-energy-arbitrage estimate only; it doesn't price demand charges, backup/resilience value, TOU peak-shaving beyond the flat spread, or degradation.
- `--ev-kwh` / `--ev-solar-fraction` — an EV is a **load**, not a generator, but a load that (if charged in daylight) soaks up solar you'd otherwise export. `extra self-consumed = min(remaining export, ev_kWh × ev_solar_fraction)`, valued at the import rate. Default fraction 0.6; typical annual EV draw is 3,000–6,000 kWh. The CSV's E1/E2 rows show the load and the self-consumption lift — and because the EV raises your useful self-consumption, **it can justify a larger array** than a no-EV household would size.
- **Export-rate sensitivity, now with the battery interaction.** The CSV's sensitivity block sweeps `--export-rate` across $0.00 / $0.05 / $0.10 / import-parity as before, but when a battery is modeled each row now shows **solar-only savings beside battery-augmented savings** — making the 2026 point visible in one table: as the export rate falls, the solar-only line drops, but the battery line holds, because the battery pulls those kWh back up to import value. The battery is the hedge against a shrinking export credit.
- **`--tou` — real time-of-use billing.** The flat `--self-consumption` fraction is a napkin knob; with `--tou`, savings are computed by **real hourly netting** instead. The `P[month][hour]` production matrix (already shifted to local-standard time, the same buckets the URDB schedule uses) is netted against a typical residential load shape, self-consumption valued at each hour's TOU rate (`--peak-rate` default $0.36 weekday 3-7pm, `--overnight-rate` $0.13, off-peak = `--import-rate`), plus a daily battery peak-shave that only discharges where the rate beats the export credit. `--annual-load` (default 10,800 kWh) scales the load shape. The honest reveals: real self-consumption is usually **~45-50%, below the flat 55% guess** (load peaks after solar), and a battery **barely pencils under a high export credit but works far harder under NEM-3.0's $0.05**. This mirrors the in-browser tool's hourly model; the load shape is a typical-home proxy (real numbers need your interval data).

All of these flags default to off/zero, so every pre-existing run (without `--tou`) produces byte-identical output.

## Validated against real systems

The production engine isn't asserted, it's checked. `proforma.py`'s keyless PVGIS leg was run against **12 real PV systems with published annual yields** — NIST's net-zero house and campus arrays, NREL's Golden array, and field studies across eight countries and both hemispheres (5 → 271 kWp). **9 of the 12 land within ±10%** of measured annual energy; on the clean mid-latitude reference set the mean ratio is **0.985**, and it reproduces the standalone PVGIS legs essentially exactly. The three misses are each *diagnosed, not hidden*: contradictory published data (Oman), a single sunny year beating a 16-year average (South Africa), and PVGIS over-reading a sub-polar coastal site by ~30% (Patagonia, 53°S — the honest edge of the envelope, where NASA POWER is the better cross-check). Full method, per-system tables, sources, and the derate caveat live in [`validation/VALIDATION.md`](./validation/VALIDATION.md).

## What's in here

| File | What it is |
|---|---|
| `index.html` | **The map calculator** (headline). Your roof on Esri satellite imagery with the two estimated panel planes drawn at the building's real orientation; drag to move, drag a corner to resize, set tilt/azimuth, and every number recomputes live in three auto-upgrading tiers: an embedded grid offline → **live NASA POWER 0.5° point** → a genuine **anchored 8760-hour simulation** (Open-Meteo hourly, rescaled to the NASA 20-year climatology) with a **P50/P90 band**. Validated vs PVGIS across **16 continental-US sites** (~2.5% MAE open-rack, symmetric across orientations — [`validation/autocalc-validation.md`](./validation/autocalc-validation.md)). Only a coordinate is sent to public APIs, never your address; self-contained, no build step. Built-in panels list finer free/paid data sources and an honest "vs commercial tools" scorecard. |
| `proforma.py` | **The pipeline.** PVWatts v8 **or** PVGIS v5.2 (hourly production) + URDB (filed tariffs) → 20-row pro forma CSV + a multi-source cross-check + summary. Stdlib only; loud, actionable errors. |
| `demo.html` | Two tabs. **FIG.1** — the note's worked San Jose arithmetic, fully offline. **Live data** — the pro-forma pipeline in the browser: your coordinates, your key (DEMO_KEY default), pick a returned tariff, download the CSV. The live tab's JS mirrors `proforma.py`'s pro-forma constants. |
| `fixtures/` | Doc-sourced samples — the PVWatts v8 docs' own example response, and a URDB sample built to the documented schema with illustrative rates. **Not live captures**; each says so in a `_fixture_note`. |
| `examples/` | Committed output of `proforma.py --fixtures` — the offline parse check's CSV and transcript. |
| `validation/` | The receipts: the PVGIS leg vs **12 real PV systems** with published yields (NIST, NREL, eight countries, both hemispheres) plus the verdict — 9 within ±10%, the 3 misses each diagnosed (including an honest PVGIS over-read at 53°S). |
| `note.md` / `note.html` | The source note. `one-pager.html` is the engagement sheet. |

## Offline check (what CI would run)

```bash
python3 proforma.py --fixtures
```

Runs the identical parsing + arithmetic against the bundled fixtures — zero network. The browser mirror was verified against the same fixtures: identical numbers to the last rounding boundary (summation order and all).

## What this is — and isn't

- **Production is a typical year, not your weather.** PVWatts simulates against NSRDB TMY data; PVGIS averages hourly 2005–2015. Either way it's a representative year, not yours — a real pro forma cites that and carries P50/P90 context. The CSV's row 2 names the source that produced the numbers.
- **The cross-check reports agreement; it doesn't manufacture independence.** Every run also pulls the *other* production source's annual figure plus NASA POWER's resource number, and flags a disagreement over ~8%. But be honest about what agreement means: **for US sites PVGIS uses PVGIS-NSRDB — the same NSRDB dataset NREL PVWatts draws on** — so "PVGIS agrees with PVWatts" in the US is *not* two independent models confirming each other. **NASA POWER is a genuinely different dataset**, so it's the real independent check. Pass `--no-cross-check` to skip the extra calls.
- **Tariff math uses first-tier rates.** Tiered usage allowances aren't modeled (the CSV flags it when the tariff is tiered). Weekday/weekend schedules are blended 5/7–2/7 because a TMY year has no real calendar.
- **URDB is community-maintained.** Open the rate's filing link and check effective dates before trusting it for a signature — the tool prints that warning, on purpose.
- **The export credit is an input, not a lookup.** Anyone who tells you their tool knows your export schedule is selling something; post-NEM-3.0 schedules are too jurisdiction-specific to fake. Set it; read the sensitivity block.
- **Not a quote, not sizing advice.** The note's first instruction is to walk the roof. This is the arithmetic you run so the quote has to survive contact with it.

## Network & secrets disclosure

The only network calls in this repo go to the four endpoints the tool exists to query, all carrying just your coordinates/address (and, for NREL only, your key):

- `developer.nrel.gov/api/pvwatts/v8.json` — PVWatts production *(the only endpoint that receives the API key)*
- `re.jrc.ec.europa.eu/api/v5_2/seriescalc` — PVGIS production *(keyless)*
- `power.larc.nasa.gov/api/temporal/climatology/point` — NASA POWER cross-check resource *(keyless)*
- `api.openei.org/utility_rates` — URDB tariffs

No telemetry, no analytics, no other endpoint. The key comes from `--api-key`, `NREL_API_KEY`, or the public `DEMO_KEY` fallback; **it is sent only to the NREL endpoint** (PVGIS and NASA need none), lives in process (or page) memory, is never written to disk, and never appears in logs or error messages (URLs are key-redacted before printing). `demo.html` makes zero requests until you click Fetch; the CSV download is built in the tab. None of these APIs' docs promise CORS, so if a browser call fails you get the error verbatim plus the CLI line that runs the same pipeline. Details in [PRIVACY.md](./PRIVACY.md).

## Grounding

Method from residential sizing fieldwork at SkyPower (2007–08) and a Loughborough MSc in Renewable Energy (Distinction). The worked FIG.1 scenario stays what it always was — public inputs, an invented household. The live mode adds no claims; it adds *your* inputs and the federal datasets, and shows the arithmetic either way.

## License

MIT — see [LICENSE](./LICENSE).

---

**Built by Jeff Pinto — Loughborough MSc Renewable Energy (Distinction), SkyPower field experience.** Advisory on honest sizing and commercial pro formas (50–500 kWp): **https://jeffpinto.com/engage/**

Source note: https://jeffpinto.com/notes/solar-sizing/
