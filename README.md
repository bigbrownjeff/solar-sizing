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
- `--export-rate` — $/kWh for exported energy (default $0.05, NEM-3.0-ish). URDB rarely encodes post-NEM-3.0 export schedules, so this stays explicit and yours — and the CSV carries a sensitivity block across $0.00 / $0.05 / $0.10 / import-parity so you can see exactly what the export-rate assumption is worth.
- `--self-consumption` — fraction used in real time (default 0.55). The napkin knob: a lender-grade version replaces it with interval-data analysis.

## Validated against real systems

The production engine isn't asserted, it's checked. `proforma.py`'s keyless PVGIS leg was run against **12 real PV systems with published annual yields** — NIST's net-zero house and campus arrays, NREL's Golden array, and field studies across eight countries and both hemispheres (5 → 271 kWp). **9 of the 12 land within ±10%** of measured annual energy; on the clean mid-latitude reference set the mean ratio is **0.985**, and it reproduces the standalone PVGIS legs essentially exactly. The three misses are each *diagnosed, not hidden*: contradictory published data (Oman), a single sunny year beating a 16-year average (South Africa), and PVGIS over-reading a sub-polar coastal site by ~30% (Patagonia, 53°S — the honest edge of the envelope, where NASA POWER is the better cross-check). Full method, per-system tables, sources, and the derate caveat live in [`validation/VALIDATION.md`](./validation/VALIDATION.md).

## What's in here

| File | What it is |
|---|---|
| `index.html` | **The map calculator** (headline). Your roof on Esri satellite imagery with the two estimated panel planes drawn at the building's real orientation; drag to move, drag a corner to resize, set tilt/azimuth, and every number recomputes live from a pre-fetched PVGIS yield surface. No API call about your roof leaves the page; self-contained, no build step. |
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
