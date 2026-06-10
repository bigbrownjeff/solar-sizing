# Privacy & data provenance

**Short version: everything in this folder is public-source or invented for illustration. Nothing here is a real customer, a real roof, a real quote, or a real utility bill.**

## What the data is

- **The San Jose scenario** (`demo.html`) is the worked example published in the source note: a 14,000 kWh/yr household (including an EV) with a south-facing roof and a mature redwood on the west side. The household is invented. No address, no roof, no person.
- **The model inputs are public figures, used as the note cites them:** NREL NSRDB irradiance for San Jose, PG&E's published E-TOU-C time-of-use tariff structure, the NEM-3.0 export-credit regime (~$0.05/kWh vs. ~$0.38/kWh on-peak import), the NREL Q4 2025 residential installed-cost benchmark ($3.00/Wp), and the 30% federal ITC.
- **The calibrated constants are derived from the note's own table, and the demo says so in its comments:** the 1,586 kWh/kWp/yr pre-shading yield basis and the $0.313/kWh tariff-weighted displaced-import rate are back-derived from FIG.1's published rows, not taken from any customer's bill.
- **Everything is deterministic.** No PRNG, no runtime data generation, no network calls, no storage. The only state is two slider positions; reset returns the exact boot state — which reproduces the note's FIG.1 honest column.

## What this folder deliberately does NOT contain

- No customer data: no addresses, utility bills, interval data, installer quotes, or site surveys — from any homeowner, CRE owner, developer, or anyone else.
- No real project pro formas, lender models, or PPA terms from SkyPower-era or any later work.
- No personal data, no PII, no names of installers, configurator vendors, or utilities' customers.
- No secrets, API keys, tokens, credentials, or internal endpoints.
- No proprietary numbers. Every figure in the demo traces to the published source note, which in turn cites public sources (NREL, PG&E tariff schedules, DSIRE).

## Grounding vs. reproduction

The demo is *grounded in* real practice — residential sizing fieldwork at SkyPower (2007–08) and the PV-systems material from a Loughborough MSc in Renewable Energy — in the sense that the **method** is what was actually practised: size from irradiance and a walked shading derate, weight savings by the tariff schedule, stop at the self-consumption sweet spot. It does **not reproduce** any real site assessment, quote, or customer outcome. The San Jose household is a stand-in so the arithmetic can be demonstrated anywhere, offline, from a single file. The page says it plainly: not a quote, and not sizing advice for your roof.

## If you fork or adapt this

Keep it synthetic until it's private. The intended use of this arithmetic on a real decision involves a real utility bill, a real quote, and a real roof walk — all of which are personal financial data. Run that version locally; don't commit a filled-in copy with someone's bill or installer quote to a public repo, and don't paste quote PDFs into anything that leaves your machine.

---

Questions about honest sizing or commercial pro formas: https://jeffpinto.com/engage/
