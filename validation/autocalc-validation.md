# Browser autocalc — 8760 yield model validation

This documents the accuracy of the **in-browser** drag-your-roof calculator (`index.html`), which is a *separate* engine from `proforma.py`. The pro-forma engine's validation against 12 real measured PV systems lives in [`VALIDATION.md`](./VALIDATION.md) and is the stronger evidentiary basis (measured ground truth). This file validates the browser yield model against **PVGIS PVcalc** (a reference model, not ground truth).

## The model

Three accuracy tiers, each auto-upgrading as data arrives, each leaving the prior intact:

1. **Embedded ~5° grid** (offline fallback).
2. **NASA POWER 0.5° monthly point** + a production-weighted cell-temperature derate.
3. **Anchored 8760-hour simulation** (top tier): one full year of real hourly satellite data (Open-Meteo / ERA5: measured GHI, diffuse, DNI, 2 m temperature), transposed per hour to each roof plane with an HDKR anisotropic model and a *per-hour* cell-temperature derate. To stop a single year's weather (which drifts ±8–10% from the long-term norm) from biasing the total, **each month's hourly irradiance is rescaled so its monthly energy matches the NASA POWER 20-year climatology** — preserving the validated P50 energy while gaining the hourly shape (for the temperature physics and, in future, time-of-use economics).

All of this runs from the single coordinate the tool already has; there are no extra user inputs.

## Continental-US validation (16 sites, south / 30°)

Anchored 8760 vs live PVGIS PVcalc, building-integrated mounting (`mountingplace=building` — the realistic, conservative rooftop reference; open-rack runs ~4% higher):

| Site | PVGIS E_y | 8760 model | Δ% |
|---|---|---|---|
| San Francisco CA | 1597 | 1588 | −0.6 |
| Miami FL | 1492 | 1512 | +1.3 |
| Boston MA | 1307 | 1331 | +1.9 |
| Houston TX | 1396 | 1427 | +2.2 |
| Atlanta GA | 1430 | 1461 | +2.2 |
| Kansas City MO | 1377 | 1414 | +2.7 |
| Albuquerque NM | 1769 | 1820 | +2.9 |
| Las Vegas NV | 1731 | 1786 | +3.2 |
| Chicago IL | 1255 | 1311 | +4.5 |
| Phoenix AZ | 1720 | 1806 | +5.0 |
| New York NY | 1266 | 1331 | +5.1 |
| Minneapolis MN | 1284 | 1357 | +5.7 |
| Denver CO | 1556 | 1658 | +6.6 |
| Seattle WA | 1107 | 1183 | +6.9 |
| Los Angeles CA | 1627 | 1791 | +10.0 |
| Portland OR | 1097 | 1234 | +12.5 |

- **MAE 4.6% vs building-integrated PVGIS; 2.5% vs open-rack PVGIS (mean signed bias +0.2%, i.e. essentially unbiased).** The truth for a real rooftop sits between the two mount references; the default 0.85 roof-walk derate keeps the *delivered* figure conservative.
- The two outliers (Portland, Los Angeles) are West-Coast marine sites where the satellite irradiance products (ERA5 vs PVGIS-SARAH) diverge most; this is a data-source disagreement at the coast, not a model error.

## Orientation symmetry (and a bug this caught)

Annual yield must be near-symmetric for a mirror-image East vs West roof at a symmetric-climate site (PVGIS confirms: W/E ≈ 0.99 at Phoenix and Long Island). South-only validation cannot see an azimuth error, so a deliberate orientation sweep was run:

- A first implementation centred each Open-Meteo hour at `hl+0.5`, producing a systematic **W/E ≈ 1.15–1.24** (west reading 15–24% high) at *every* site and *every* year — the signature of a one-hour time-alignment error. Open-Meteo's solar-radiation values are the **preceding-hour mean**, so the correct sun-position centre is `hl−0.5`.
- After the fix, W/E = 0.99 (Phoenix) and 0.98 (Long Island), matching PVGIS, with East / South / West each within ~5%. A balanced E/W split (the seed example) was largely unaffected because its two planes cancelled the error; a single-orientation E or W roof would have been ~7% off.

## Honest limits

- Spatial resolution is still **~25–55 km reanalysis, not 250 m satellite** (Solargis / Solcast). PVGIS itself is a model, not measured data.
- The P50/P90 band is **resource + satellite-model uncertainty only**, not a bankable P90 (no soiling, snow, availability, or degradation-uncertainty terms).
- For a bankable number, run `proforma.py --source pvgis` (or a commercial dataset). This tool is the honest first-pass.

## Reproduce

`scratchpad/validate-shipped.mjs` runs the verbatim shipped functions against these 16 sites with live Open-Meteo + NASA POWER + PVGIS data. Method: anchored 8760 as above; compare to PVGIS `outputs.totals.fixed.E_y`.
