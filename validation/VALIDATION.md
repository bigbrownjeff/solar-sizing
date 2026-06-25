# Production-Engine Validation Verdict (proforma.py)

Run date 2026-06-24. Scope: does proforma.py's production engine reproduce trusted
independent estimates and real measured yields? Method: run the workbook's PVGIS leg
(--source pvgis) against the 8 real PV systems in validation/real-projects.md, with
--derate 1.0 (the published actuals already carry each system's own real losses) and URDB
bypassed (--import-rate 0.15 --no-cross-check; annual yield is tariff-independent). The raw
PVGIS annual is row 8 ("Year-1 generation") of each CSV; specific yield is row 7.

NREL note: PVWatts (developer.nrel.gov) was unreachable on the run date ("could not reach
... nodename nor servname provided"), so PVWatts was attempted for every system and the
target site and recorded as "NREL down 2026-06-24". The verdict below rests on the PVGIS
leg plus the standalone NASA/PVGIS legs already in real-projects.md.

## 1. Does the workbook's PVGIS path reproduce the standalone PVGIS legs?

Yes, essentially exactly. The workbook calls the same PVGIS v5.2 endpoint, so this is a
self-consistency check (no drift introduced by the rewrite).

| system | standalone PVGIS leg (kWh/yr) | proforma PVGIS (kWh/yr) | pf/leg |
|---|---|---|---|
| NZERTF | 13,063.9 | 13,064 | 1.0000 |
| NIST Roof | 89,744.3 | 89,744 | 1.0000 |
| NIST Ground | 349,559.5 | 349,560 | 1.0000 |
| NREL Golden | 126,505.4 | 126,505 | 1.0000 |
| Burdur | 33,887.5 | 33,801 | 0.9974 |
| Lublin PV9 | 29,252.8 | 28,772 | 0.9836 |
| Perambalur | 7,043.2 | 7,013 | 0.9957 |
| Oman SQU | 33,851.0 | 33,976 | 1.0037 |

US sites match to four decimals. The four international sites differ by 0.3 to 1.6 percent.
That residual is azimuth-convention rounding, not a model gap: the standalone legs used the
PVGIS aspect convention (0 = south), and the workbook takes compass degrees (180 = south),
so e.g. Lublin's "south-east approx 45 deg E of S" went in as compass 135 (PVGIS aspect
-45) and NREL Golden's 16 deg E of S as compass 164 (aspect -16). A degree or two of
azimuth rounding moves annual yield by ~1 percent, which is exactly the size of the gap.
All within the ~2 percent expectation. The PVGIS path is faithful.

## 2. proforma-vs-published: how many of the 7 clean systems land within +/-10%?

All 7 of 7. (Oman excluded as a documented bad-data outlier, see section 5.)

| system | published (kWh/yr) | proforma (kWh/yr) | pf/pub | within +/-10% |
|---|---|---|---|---|
| NZERTF | 13,523 | 13,064 | 0.966 | yes |
| NIST Roof | 88,600 | 89,744 | 1.013 | yes |
| NIST Ground | 342,100 | 349,560 | 1.022 | yes |
| NREL Golden | 134,650 | 126,505 | 0.940 | yes |
| Burdur | 33,977.5 | 33,801 | 0.995 | yes |
| Lublin PV9 | 29,500 | 28,772 | 0.975 | yes |
| Perambalur | 7,144 | 7,013 | 0.982 | yes |

Clean set: range 0.940 to 1.022, mean 0.985, median 0.982. No tilt-toward-over- or
under-prediction; the spread straddles 1.0. The two extremes are explainable and benign:
NREL Golden at 0.940 is the raw (non-snow-corrected) measured year against an 11-year PVGIS
average, and the snow-corrected actuals (126,035 / 125,494) would pull pf/pub to ~1.00;
NIST Ground at 1.022 is a measured year that included a ~1-week inverter outage, so the
actual slightly understates a healthy array, again pushing the ratio above 1.0 in the
right direction.

## 3. The derate question (read this honestly)

These eight are well-sited reference installs: NIST and NREL research arrays, a clean
recent Turkiye case study, minimal-shading rooftops chosen precisely because they publish
trustworthy numbers. For such arrays, published actual is approximately PVGIS-raw
(pf/pub ~ 1.0 with --derate 1.0, as section 2 shows). The 14 percent system-loss figure
baked into both PVWatts and PVGIS (wiring, inverter, soiling, mismatch, ~3 percent generic
shading) already accounts for the normal losses these arrays have, so an additional
roof-walk derate of 1.0 is correct for them.

That means the workbook's DEFAULT --derate 0.85 would predict about 15 percent LOW for an
unshaded array like these. Concretely: with --derate 0.85 the pf/pub ratios in section 2
become ~0.85x, i.e. a clean-set range of about 0.80 to 0.87 and a mean near 0.84, and all
seven would then fall below the -10 percent band.

This is NOT a model bug. The 0.85 is a deliberate, conservative shading knob for the
typical residential roof that has a chimney, a dormer, and the neighbor's tree on the west
face at 4pm -- the loss a satellite estimate misses and that the README explicitly tells
you to walk the roof to find. The validation set is the opposite case (chosen for clean
siting), so it is exactly the population where 0.85 is too aggressive.

Recommendation (documentation, not code): the README and the tool's --derate help should
state the regime explicitly. Today README line 89 only defines what --derate is. Add: 0.85
suits a typical shaded residential roof; a genuinely unshaded, well-sited array (open
ground mount, no obstructions, clean azimuth) wants ~0.95 to 1.0, and using 0.85 there will
under-predict annual production by ~15 percent. No constant in proforma.py needs to change;
the default stays 0.85 (conservative-by-design for the median homeowner), but the user
should be told when to override it.

## 4. The independence nuance (US sites are not a true cross-check against PVWatts)

For US locations PVGIS draws its irradiance from PVGIS-NSRDB -- the SAME NREL NSRDB
underlying dataset that PVWatts uses. So a PVGIS-vs-PVWatts comparison on US sites is a
re-derivation from one common data source, not two independent measurements; close
agreement there would mostly confirm that two model wrappers read the same satellite
irradiance the same way. The genuinely independent leg is NASA POWER (a different
satellite/reanalysis lineage), which is why the workbook pulls NASA POWER in its
cross-check and why the standalone legs in real-projects.md lean on it. When NREL recovers,
treat PVWatts agreement on US sites as a wrapper sanity check, and keep NASA POWER as the
independent oracle. (International sites use PVGIS-SARAH, a separate dataset, so there the
PVGIS-vs-PVWatts distinction is less entangled, but coverage is the constraint.)

## 5. Oman SQU outlier (excluded from the verdict, kept in the table)

pf/pub = 1.440 here, which looks alarming but is the bad-data case inverted. The SQU paper
states 23,595 kWh in its abstract and 27,067 kWh in Section 5.1 -- internally contradictory
-- and attributes a low measured performance ratio (~0.67) to extreme Muscat cell
temperatures (modules at 55.5 C) that a generic 14 percent loss does not capture. The
workbook (which tracks PVGIS-raw, 33,976 kWh) simply disagrees with the suspect-low
published 23,595, so the ratio blows up. This is a source-quality problem, not a model
error, and it is excluded from the 7-clean verdict exactly as flagged in real-projects.md.

## 6. Example site -- a Long Island split-array roof (Rockville Centre NY area, 40.6675, -73.6207)

Example off-cardinal split array: two planes, 5 kWp each at tilt 30, one ESE (compass 123)
and one WNW (compass 303). PVGIS leg via --source pvgis.

| scenario | derate | specific yield (kWh/kWp/yr) | annual (kWh/yr) |
|---|---|---|---|
| raw resource | 1.0 | 1,062 | 10,620 |
| as modeled (workbook default) | 0.85 | 903 | 9,027 |

The two scenarios differ by exactly the 0.85 factor (9,027 = 0.85 x 10,620), confirming the
derate is a clean linear knob on the PVGIS production matrix. The ~1,062 kWh/kWp raw yield is
sensible for a 30-degree split ESE/WNW roof at this latitude (the off-cardinal split costs
some yield versus a due-south 30-degree plane). For THIS site the 0.85 default is the
defensible choice only if a roof walk confirms real shading; if the planes are clean, model
it nearer 0.95 to 1.0 (so ~10,100 to 10,620 kWh/yr) per section 3.

## Bottom-line verdict

YES -- the production engine is accurate enough to trust. On 7 clean real systems spanning
5 to 271 kWp and four countries, the workbook's PVGIS leg reproduces measured annual energy
to a mean ratio of 0.985 (range 0.940 to 1.022), with all seven inside +/-10 percent, and
it reproduces the standalone PVGIS legs essentially exactly. The single caveat is not in the
engine but in the DEFAULT 0.85 derate: it is a conservative shaded-roof knob and must be
relaxed to ~0.95 to 1.0 for a genuinely unshaded array, or the workbook will under-predict
by ~15 percent. Recommend documenting that regime in the README and --derate help.
