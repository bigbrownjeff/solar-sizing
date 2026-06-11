# solar-sizing

**The honest solar pro forma, on live federal data.** Type your roof's coordinates and the size on your quote; `proforma.py` pulls real production from NREL PVWatts v8 and real filed tariffs from the OpenEI Utility Rate Database, then runs a twenty-row pro forma that weights savings by *when* the panels produce — not by the annual %-offset number configurators sell on. `demo.html` does the same thing in the browser, beside a fully offline worked example.

From Jeff Pinto's note *[First-principles residential solar sizing](https://jeffpinto.com/notes/solar-sizing/)*: a twenty-row spreadsheet beats every online configurator, because the configurator has a structural incentive not to be honest — the installer is paid per watt installed, the configurator per lead generated. This repo is that spreadsheet showing its work against live federal data.

---

## 60-second quickstart — no signup needed

```bash
python3 proforma.py --lat 37.3382 --lon -121.8863 --kw 7.2
```

Stdlib only — no pip install. With no key it falls back to `DEMO_KEY`, which api.data.gov caps at **30 requests/IP/hour, 50/day** (a run here is 2 requests). A free registered key — https://developer.nrel.gov/signup/, works on both endpoints — gets 1,000/hour:

```bash
export NREL_API_KEY=your-key-here
```

What you get: a terminal summary and `proforma.csv` — 20 rows (site, weather station, tariff, tariff-weighted import rate, self-consumption split, ITC, net cost, simple payback, 25-yr NPV), plus the marginal-next-kWp row and an export-rate sensitivity block, with provenance in the header.

## Picking your actual tariff

URDB usually returns several tariffs for a location. The default is index 0 — whatever URDB listed first, not "best". List and pick:

```bash
python3 proforma.py --address '200 E Santa Clara St, San Jose CA' --list-tariffs
python3 proforma.py --lat 37.3382 --lon -121.8863 --kw 7.2 --tariff 2
```

Note the asymmetry, stated honestly: **PVWatts v8 takes coordinates only** (its street-address parameter was retired after v6), so production always needs `--lat/--lon` — long-press your roof in any maps app. `--address` drives the tariff lookup alone; URDB geocodes it server-side.

## The honest knobs

```bash
python3 proforma.py --lat 37.34 --lon -121.89 --kw 7.2 \
  --derate 0.85 --self-consumption 0.55 --export-rate 0.05 --cost-per-watt 3.00
```

- `--derate` — the roof-walk shading derate (default 0.85). PVWatts' 14% system-loss default includes only a generic ~3% shading allowance; the redwood that shades your west face at 4pm is yours to count. Satellites miss it. Walk the roof.
- `--export-rate` — $/kWh for exported energy (default $0.05, NEM-3.0-ish). URDB rarely encodes post-NEM-3.0 export schedules, so this stays explicit and yours — and the CSV carries a sensitivity block across $0.00 / $0.05 / $0.10 / import-parity so you can see exactly what the export-rate assumption is worth.
- `--self-consumption` — fraction used in real time (default 0.55). The napkin knob: a lender-grade version replaces it with interval-data analysis.

## What's in here

| File | What it is |
|---|---|
| `proforma.py` | **The pipeline.** PVWatts v8 (hourly production) + URDB (filed tariffs) → 20-row pro forma CSV + summary. Stdlib only; loud, actionable errors. |
| `demo.html` | Two tabs. **FIG.1** — the note's worked San Jose arithmetic, fully offline. **Live data** — the same pipeline in the browser: your coordinates, your key (DEMO_KEY default), pick a returned tariff, download the CSV. The live tab's JS mirrors `proforma.py` constant-for-constant. |
| `fixtures/` | Doc-sourced samples — the PVWatts v8 docs' own example response, and a URDB sample built to the documented schema with illustrative rates. **Not live captures**; each says so in a `_fixture_note`. |
| `examples/` | Committed output of `proforma.py --fixtures` — the offline parse check's CSV and transcript. |
| `note.md` / `note.html` | The source note. `one-pager.html` is the engagement sheet. |

## Offline check (what CI would run)

```bash
python3 proforma.py --fixtures
```

Runs the identical parsing + arithmetic against the bundled fixtures — zero network. The browser mirror was verified against the same fixtures: identical numbers to the last rounding boundary (summation order and all).

## What this is — and isn't

- **Production is a typical year, not your weather.** PVWatts simulates against NSRDB TMY data; a real pro forma cites that and carries P50/P90 context. The CSV's row 2 names the station and dataset.
- **Tariff math uses first-tier rates.** Tiered usage allowances aren't modeled (the CSV flags it when the tariff is tiered). Weekday/weekend schedules are blended 5/7–2/7 because a TMY year has no real calendar.
- **URDB is community-maintained.** Open the rate's filing link and check effective dates before trusting it for a signature — the tool prints that warning, on purpose.
- **The export credit is an input, not a lookup.** Anyone who tells you their tool knows your export schedule is selling something; post-NEM-3.0 schedules are too jurisdiction-specific to fake. Set it; read the sensitivity block.
- **Not a quote, not sizing advice.** The note's first instruction is to walk the roof. This is the arithmetic you run so the quote has to survive contact with it.

## Network & secrets disclosure

The only network calls in this repo go to the two endpoints the tool exists to query — `developer.nrel.gov/api/pvwatts/v8.json` and `api.openei.org/utility_rates` — carrying your coordinates/address and your API key. No telemetry, no analytics, no other endpoint. The key comes from `--api-key`, `NREL_API_KEY`, or the public `DEMO_KEY` fallback; it lives in process (or page) memory, is never written to disk, and never appears in logs or error messages (URLs are key-redacted before printing). `demo.html` makes zero requests until you click Fetch; the CSV download is built in the tab. Neither API's docs promise CORS, so if a browser call fails you get the error verbatim plus the CLI line that runs the same pipeline. Details in [PRIVACY.md](./PRIVACY.md).

## Grounding

Method from residential sizing fieldwork at SkyPower (2007–08) and a Loughborough MSc in Renewable Energy (Distinction). The worked FIG.1 scenario stays what it always was — public inputs, an invented household. The live mode adds no claims; it adds *your* inputs and the federal datasets, and shows the arithmetic either way.

## License

MIT — see [LICENSE](./LICENSE).

---

**Built by Jeff Pinto — Loughborough MSc Renewable Energy (Distinction), SkyPower field experience.** Advisory on honest sizing and commercial pro formas (50–500 kWp): **https://jeffpinto.com/engage/**

Source note: https://jeffpinto.com/notes/solar-sizing/
