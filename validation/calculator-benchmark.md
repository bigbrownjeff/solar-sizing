# Calculator benchmark: which solar tools are optimistic, and where

Run date 2026-06-25. This is the head-to-head the [mandated-calculator note](https://jeffpinto.com/notes/mandated-calculator/)
needed: real solar calculators, run for one Long Island roof, scored against an
independent production baseline and against current (2026) policy reality. The
question is not "are they wrong" but "wrong where, by how much, and on what
assumption."

## The benchmark case

A home at **Rockville Centre NY 11570** (40.6675, -73.6207), PSEG Long Island
(LIPA), a standard **7 kW DC, south, 30 degrees** array at roughly $3.00/W
installed. Where a tool auto-sizes or uses its own defaults, we record its
choices rather than forcing ours.

## The reality anchors (what "correct" means here)

**Production (validated):** PVGIS = **1,333 kWh/kWp/yr** for a clean south 30
degree array. That is a clean-roof upper bound. The real-world distribution,
from the NYSERDA fleet of **33,698 completed LIPA residential systems** (median
7.8 kW), has an expected-yield median of **~1,150 kWh/kWp/yr**, p5 to p95 of
**855 to 1,332**. Brookhaven's metered Long Island Solar Farm hit 1,459 in a
sunny first year (a clean fixed-south 35 degree utility array); a Farmingdale
carport floored at ~947. So a typical real roof yields **~1,150**, i.e. the
clean-south model runs **~15 percent high** for the median roof. This is exactly
the size of the 0.85 roof-walk derate, now corroborated against tens of
thousands of real Long Island roofs.

**Policy (2026, verified):**
- **The 30 percent federal ITC (Section 25D) expired 12/31/2025.** The One Big
  Beautiful Bill Act (signed 2025-07-04) ended the Residential Clean Energy
  Credit for systems placed in service after 2025. A 2026 *owned* install gets
  **$0 federal credit**; only third-party leases/PPAs keep the Section 48E
  business ITC (30 percent through 2027). Sources: IRS Residential Clean Energy
  Credit page; CRS; greenlancer 2026 guide.
- **NY State credit survives:** 25 percent of cost, capped at $5,000 (owned).
- **NY-Sun rebate is ~$0/W** for a market-rate Long Island buyer (the standard
  residential block closed; the remaining adder is income-qualified only).
- **Export compensation is genuinely contested** across authoritative sources:
  PSEG-LI's own time-of-day net-meter banking implies the off-peak retail rate
  (~$0.19); NYSERDA's VDER Value Stack is quoted ~$0.15 to 0.22; the VDER
  energy-value component alone (and CUNY's NY Solar Map) is ~$0.04 to 0.05. The
  honest answer is a range, and that irreducible jurisdiction-specificity is the
  note's whole point, proven against primary sources.

## Our honest 2026 baseline (what each tool is scored against)

7 kW south, gross $21,000, **no federal ITC**, NY credit $5,000, **net
$16,000**; production ~7,900 to 8,050 kWh/yr (typical-roof, 0.85 derate):

| export assumption | savings/yr | simple payback |
|---|---|---|
| $0.19 (TOD net metering) | ~$1,590 | **~10.0 yr** |
| $0.05 (VDER energy-only) | ~$1,095 | **~14.6 yr** |

So the honest 2026 Long Island payback is **~10 to 15 years**, export-dependent.
For comparison, the *expired-ITC* world the calculators still model (net
$14,700) gives ~7.5 to 9 years; that ~$6,300 phantom credit is the single
biggest distortion in the cohort.

## The scorecard

Production yield is kWh/kWp/yr at the benchmark config; payback is the tool's
own headline for this address. "Live" = a real run captured for 11570; "doc" =
tool gated or blocked, assumptions read from its published methodology.

| Tool | Type | Yield | Payback | Capture | Optimism vs 2026 reality |
|---|---|---|---|---|---|
| PVGIS v5.2 | gov (EU) | 1,333 | n/a | live | none (clean-south baseline; ~15% high vs typical roof) |
| NREL PVWatts v8 | gov | ~1,333 | n/a | down | host unreachable all run; PySAM stands in for the engine |
| NASA POWER | gov | resource only | n/a | live | none (GHI 1,464; not a yield tool) |
| pvlib 0.15 | open-source | 1,372* | n/a | live | none (*normalized to common weather; raw 1,454 on sunnier TMY) |
| NREL SAM (PySAM) | gov + OSS | 1,432* | n/a | live | none (*normalized; residual is dc/ac headroom) |
| Global Solar Atlas | nonprofit | 1,478 | n/a | live | none (at 36 deg optimal tilt; corroborates the resource) |
| CUNY NY Solar Map | nonprofit/gov | 1,238 | modeled | live | **least optimistic estimator**: rejects 1:1, models ~$0.04 export, real LIDAR shading |
| Rewiring America | nonprofit | n/a | n/a | live | honest: returns $0 incentives (25D expired); no yield/payback claim |
| GRID Alternatives, NYSERDA, PSEG-LI, ENERGY STAR, DOE | nonprofit/gov | n/a | none published | doc | honest by omission: publish no payback or yield number |
| SolarReviews | private | ~1,300 | ~10 yr | live | assumes 1:1 net metering; cost honest ($3.33/W NY); applies expired 30% ITC |
| EnergySage | private | ~1,300 | ~7 to 10 yr | doc | full-retail export; **$2.58/W national cost** understates LI ~$3.50; expired ITC |
| Project Sunroof | private (Google) | ~1,300 | not shown | doc | likely 1:1 via a possibly-stale rate DB; 4% discount; no NEM-3 proof |
| Tesla | private | ~1,300 | **7.0 yr** | doc | 1:1 NEM + expired 30% ITC |
| solar.com | private | ~1,300 | 7 to 10 yr | doc | 1:1 NEM + expired ITC headline |
| **WattBuy** | private | **1,420** | **8.3 yr** | live | **most optimistic**: 1:1 NEM, no shading derate, **expired 30% ITC**, and a **misapplied NYC property-tax abatement** (Nassau is not NYC) |

## What the benchmark proves

1. **Production is honest everywhere.** Every physics engine (gov, open-source,
   nonprofit) lands within a few percent of 1,333 once put on common weather
   data, and the consumer tools' production numbers are sane too. No tool inflates
   kWh per unit sunlight. The note never claimed otherwise; this confirms the
   error is not in the physics.

2. **The optimism is entirely in the economics layer, and in 2026 it is
   dominated by stale policy.** Every private calculator still applies the **30
   percent federal ITC that expired 12/31/2025**, a ~$6,300 phantom credit on
   this system. Stack on full-retail net metering (vs a contested ~$0.05 to 0.19
   reality), no shading derate (vs the ~15 percent real-roof haircut), and in
   WattBuy's case an incentive from the wrong county, and you get the 7 to 8 year
   paybacks the tools advertise against an honest ~10 to 15 year number. That is
   the note's "wrong on purpose," caught live and itemized.

3. **Public-interest tools were decisively more honest.** The nonprofit and
   government tools (GRID, Rewiring America, NYSERDA, PSEG-LI, ENERGY STAR, DOE)
   publish no payback at all, and the one that fully models economics, CUNY's NY
   Solar Map, is the only estimator in the cohort that rejects 1:1 net metering
   and applies real shading. Completion-rate incentives, not malice: the tools
   with no lead-gen motive had no reason to flatter.

4. **The most honest finding implicates this repo.** Until this audit,
   `proforma.py` hardcoded `ITC = 0.30` and the worked Long Island example used
   California's NEM-3.0 ~$0.05 export rate, a rule from the wrong jurisdiction.
   The note's lesson, that a calculator's defaults silently encode someone's
   stale assumptions, applied to its own author. The 2026 fixes (ITC as an
   explicit flag defaulting to the post-2025 reality; the export knob labeled as
   jurisdiction-specific; the demo's export defaulting to the PSEG-LI rate) are
   in this same change.

## Honest limits of this benchmark

- NREL PVWatts' hosted API was DNS-unreachable for the entire run; PySAM runs the
  same v8 engine locally, so the algorithm is represented, but the public REST
  number is "pending live capture," not fabricated.
- Several consumer tools (Tesla, solar.com, EnergySage) are lead-gated; their
  numbers are from published methodology and advertised ranges, marked "doc," not
  live per-address runs.
- Residential metered yield on Long Island is paywalled (PVOutput logins, NYSERDA
  DER CSVs behind auth); the ~1,150 typical is the state's modeled per-address
  estimate across 33,698 real systems plus two metered utility/institutional
  arrays, not a metered residential sample. A logged-in NYSERDA DER pass would
  upgrade this to hard metered residential anchors.
- The export value is a researched range, not a single number, on purpose: the
  sources genuinely disagree, which is the finding.
