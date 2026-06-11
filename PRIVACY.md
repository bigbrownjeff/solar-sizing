# Privacy & data provenance

**Short version: everything committed in this folder is public-source or invented for illustration. Nothing here is a real customer, a real roof, a real quote, or a real utility bill. The live mode talks to exactly two federal-data endpoints, only when you run it, with inputs you typed.**

## What the data is

- **The San Jose scenario** (`demo.html`, FIG.1 tab) is the worked example published in the source note: a 14,000 kWh/yr household (including an EV) with a south-facing roof and a mature redwood on the west side. The household is invented. No address, no roof, no person.
- **The model inputs are public figures, used as the note cites them:** NREL NSRDB irradiance for San Jose, PG&E's published E-TOU-C time-of-use tariff structure, the NEM-3.0 export-credit regime (~$0.05/kWh vs. ~$0.38/kWh on-peak import), the NREL Q4 2025 residential installed-cost benchmark ($3.00/Wp), and the 30% federal ITC.
- **The calibrated constants are derived from the note's own table, and the demo says so in its comments:** the 1,586 kWh/kWp/yr pre-shading yield basis and the $0.313/kWh tariff-weighted displaced-import rate are back-derived from FIG.1's published rows, not taken from any customer's bill.
- **The FIG.1 tab is deterministic and fully offline.** No PRNG, no runtime data generation, no network calls, no storage. The only state is two slider positions; reset returns the exact boot state — which reproduces the note's FIG.1 honest column.
- **`fixtures/` is doc-sourced, not captured.** `pvwatts-sample.json` reproduces the example response printed in the PVWatts v8 documentation (retrieved 2026-06-10); `urdb-sample.json` is built by hand to the URDB API's documented `detail=full` schema with illustrative rates. Each file carries a `_fixture_note` saying exactly this. `examples/` is the committed output of running `proforma.py --fixtures` on them — zero network.

## The live mode (demo.html "Live data" tab, and proforma.py)

- **Two endpoints, total:** `developer.nrel.gov/api/pvwatts/v8.json` (NREL PVWatts — production simulation) and `api.openei.org/utility_rates` (OpenEI Utility Rate Database — filed tariffs). There is no third endpoint, no telemetry, no analytics, anywhere in this repo.
- **What gets sent, and when:** your coordinates (and optional street address, tariff lookup only), system size/tilt/azimuth, and your API key — only when you click Fetch in the browser or run the CLI. The browser page makes **zero requests until you click**; loading it sends nothing.
- **The API key** comes from the input field, `--api-key`, the `NREL_API_KEY` env var, or the public `DEMO_KEY` fallback. It lives in page/process memory only — never localStorage, never cookies, never disk, never logs. Error messages redact the key from URLs before printing. Reload the page and it's gone.
- **A street address is location data.** If you type your real address or your roof's exact coordinates, those go to the two federal endpoints above (that's the tool's whole job) and nowhere else. Nothing is stored anywhere when the run ends; the CSV download is assembled inside the page and never touches a server.
- **What comes back is shown as received:** PVWatts' station/dataset metadata and URDB's tariff list render verbatim (HTML-escaped), including URDB's freshness caveats. The tool links each tariff's public filing so you can verify it.

## What this folder deliberately does NOT contain

- No customer data: no addresses, utility bills, interval data, installer quotes, or site surveys — from any homeowner, CRE owner, developer, or anyone else.
- No real project pro formas, lender models, or PPA terms from SkyPower-era or any later work.
- No personal data, no PII, no names of installers, configurator vendors, or utilities' customers.
- No secrets, API keys, tokens, credentials, or internal endpoints — `DEMO_KEY` is api.data.gov's public shared demo key, not a credential.
- No captured API responses. The fixtures are documentation examples and schema reconstructions, labeled as such.
- No proprietary numbers. Every committed figure traces to the published source note, which in turn cites public sources (NREL, PG&E tariff schedules, DSIRE).

## Grounding vs. reproduction

The tool is *grounded in* real practice — residential sizing fieldwork at SkyPower (2007–08) and the PV-systems material from a Loughborough MSc in Renewable Energy — in the sense that the **method** is what was actually practised: size from irradiance and a walked shading derate, weight savings by the tariff schedule, stop at the self-consumption sweet spot. It does **not reproduce** any real site assessment, quote, or customer outcome. The live mode runs that method on federal datasets and your inputs; it stores nothing and claims nothing about your roof beyond the arithmetic it prints. The page says it plainly: not a quote, and not sizing advice — walk the roof.

## If you fork or adapt this

Keep the committed side synthetic until it's private. The intended use on a real decision involves a real utility bill, a real quote, and a real roof walk — personal financial data. Run that version locally; don't commit a filled-in `proforma.csv` for a real address to a public repo, and don't paste quote PDFs into anything that leaves your machine. If you wire in more endpoints, update this file and the page disclosures first — the disclosure *is* part of the tool.

---

Questions about honest sizing or commercial pro formas: https://jeffpinto.com/engage/
