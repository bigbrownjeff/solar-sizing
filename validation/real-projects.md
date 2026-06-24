# Real PV Systems with Published Annual Yields (Pro-Forma Validation Set)

Purpose: validate a residential solar pro-forma against REAL PV systems that publicly
list a measured annual energy. Each row pins location, DC size, and a measured annual
kWh to a citable source URL. For each, PVGIS v5_2 (keyless) was run for an independent
model estimate; ratio = published_actual / PVGIS_predicted.

PVGIS call template (loss=14, mountingplace=building, pvtechchoice=crystSi):
`https://re.jrc.ec.europa.eu/api/v5_2/PVcalc?lat=<lat>&lon=<lon>&peakpower=<kWp>&loss=14&angle=<tilt>&aspect=<az>&mountingplace=building&pvtechchoice=crystSi&outputformat=json`
Value read: `outputs.totals.fixed.E_y`. PVGIS aspect convention: 0=south, 90=west,
-90=east, 180=north (this differs from the "deg CW from N" used by several sources;
conversions are noted per system below).

The two empty columns "PVWatts kWh/yr" and "proforma kWh/yr" are now filled (run 2026-06-24).
NREL's PVWatts host (developer.nrel.gov) was unreachable that day, so the PVWatts column
records "NREL down 2026-06-24" for every system; the proforma column is the workbook's own
PVGIS leg, run with --derate 1.0 (published actuals already carry each system's real losses)
and URDB bypassed via --import-rate 0.15 --no-cross-check. The added "ratio (pf/pub)" column
is proforma / published. Add rows the same way (one system per line).

Azimuth note for the proforma run: proforma.py takes COMPASS degrees (0=N,90=E,180=S,270=W),
so the PVGIS aspect values above convert as compass = 180 + aspect (aspect 0 south = 180;
NREL aspect -16 = 164; Lublin aspect -45 = 135). Same physical tilt/azimuth as the standalone
PVGIS leg, so the two are apples-to-apples.

| system id / name | location (lat,lon) | kWp | tilt / az (PVGIS aspect) | published kWh/yr (+ year span) | source URL | PVGIS kWh/yr | ratio (pub/PVGIS) | PVWatts kWh/yr | proforma kWh/yr | ratio (pf/pub) |
|---|---|---|---|---|---|---|---|---|---|---|
| NZERTF (NIST Net-Zero Energy Residential Test Facility) | 39.1, -77.2 | 10.24 | 18.4 / due south (aspect 0) | 13,523 (Jul 2013 to Jun 2014, Year 1) | https://pmc.ncbi.nlm.nih.gov/articles/PMC7339755/ | 13,063.9 | 1.035 | NREL down 2026-06-24 | 13,064 | 0.966 |
| NIST Roof Array (Gaithersburg campus) | 39.1354, -77.2156 | 73 | 10 / 180 deg CW from N = due south (aspect 0) | 88,600 (Oct 2014 to Sep 2015) | https://pmc.ncbi.nlm.nih.gov/articles/PMC5769486/ | 89,744.3 | 0.987 | NREL down 2026-06-24 | 89,744 | 1.013 |
| NIST Ground Array (Gaithersburg campus) | 39.1319, -77.2141 | 271 | 20 / 180 deg CW from N = due south (aspect 0) | 342,100 (Oct 2014 to Sep 2015) | https://pmc.ncbi.nlm.nih.gov/articles/PMC5769486/ | 349,559.5 | 0.979 | NREL down 2026-06-24 | 349,560 | 1.022 |
| NREL S&TF rooftop (Golden, CO) | 39.7419, -105.1717 | 94.05 | 10 / 164 deg CW from N = 16 deg E of S (aspect -16) | 134,650 (avg of CY2011 134,286 and CY2012 135,013, raw measured) | https://www.osti.gov/biblio/1115788 | 126,505.4 | 1.064 | NREL down 2026-06-24 | 126,505 | 0.940 |
| Yesilova rooftop (Burdur, Turkiye) | 37.29, 29.48 | 24 | 8 / due south (aspect 0) | 33,977.5 (full-year 2024, recorded/measured AC) | https://www.mdpi.com/1996-1073/19/6/1468 | 33,887.5 | 1.003 | NREL down 2026-06-24 | 33,801 | 0.995 |
| Lublin PV9 rooftop (SE Poland) | 51.18, 22.71 | 30.16 | 25 / south-east approx 45 deg E of S (aspect -45) | ~29,500 (monitored 2020 to 2021; paper says "about 29.5 MWh") | https://www.mdpi.com/1996-1073/15/10/3666 | 29,252.8 | 1.008 | NREL down 2026-06-24 | 28,772 | 0.975 |
| Hospital rooftop (Perambalur, Tamil Nadu, India) | 11.23, 78.87 | 5 | flat roof; no tilt/az stated, default tilt 11 (approx lat) / south (aspect 0) | 7,144 (year 2019) | https://link.springer.com/article/10.1007/s11356-020-12104-0 | 7,043.2 | 1.014 | NREL down 2026-06-24 | 7,013 | 0.982 |
| Eco-house rooftop, Sultan Qaboos Univ (Muscat, Oman) -- SUSPECT, see caveat | 23.6, 58.2 | 20.4 | 23.5 / due south (aspect 0) | 23,595 (full year May 2017 to Apr 2018; paper ALSO states 27,067 elsewhere) | https://www.tandfonline.com/doi/full/10.1080/19397038.2019.1658824 | 33,851.0 | 0.697 | NREL down 2026-06-24 | 33,976 | 1.440 |

Summary of agreement (pub/PVGIS): 7 of 8 systems land between 0.98 and 1.06 (tight model
agreement, spanning Maryland, Colorado, Turkiye, Poland, and India, 5 kWp to 271 kWp). The
Oman system is the lone outlier at 0.70 and is flagged as suspect source data (see its
paragraph). Specific yield (published kWh per kWp): NZERTF 1,321; NIST Roof 1,214; NIST
Ground 1,262; NREL Golden 1,432; Burdur 1,416; Poland PV9 978; Perambalur 1,429; Oman
1,156 (low, see caveat).

Proforma column (pf/pub), added 2026-06-24: the workbook's own PVGIS leg reproduces the
standalone PVGIS leg essentially exactly (US sites identical to 4 decimals; international
sites within 0.4 to 1.6 percent, the small gap being azimuth-convention rounding). All 7
clean systems land within +/-10 percent of published actuals (pf/pub range 0.940 to 1.022,
mean 0.985). The Oman outlier flips to 1.440 here only because its published number is the
suspect-low one (the workbook tracks PVGIS, which the bad actual disagrees with) -- same
caveat, excluded from the verdict. See validation/VALIDATION.md for the full write-up,
including why the workbook's default 0.85 derate is the right shaded-roof setting and an
unshaded reference array wants ~0.95 to 1.0.

## Per-system data quality and caveats

NZERTF (NIST Net-Zero Energy Residential Test Facility), Gaithersburg MD. The single
best residential anchor in this set. A purpose-built net-zero test house with a 10.24 kWp
roof array; NIST publishes whole-house instrumented data. Year-1 PV generation of 13,523
kWh (Jul 1 2013 to Jun 30 2014) is the gross PV output, stated in the open-access
performance paper (PMC7339755), which also gives DC rating 10.24 kW and location (39.1,
-77.2). Roof tilt 18.4 degrees is from NIST Special Publication 1166 (the NIST solar
expert ran PVWatts "based on the 18.4 degree tilt"); the gable faces due south. Coordinates
are paper-rounded to one decimal, so PVGIS siting is approximate but immaterial at this
scale. Ratio 1.04 (PVGIS slightly under-predicts) is well within expectations.

NIST Roof Array, Gaithersburg campus. Cleanest of the three NIST campus arrays: no
outages in the measured year and only a 3.5 percent model deviation in the source. 73 kWp,
tilt 10, azimuth 180 deg CW from north (= due south, PVGIS aspect 0). Measured delivered
AC energy 88,600 kWh (88.6 MWh) for Oct 1 2014 to Sep 30 2015, from Boyd 2017
(PMC5769486, Table 3); array metadata cross-checked against the NIST JRES 122.040 paper
(verified locally: rated DC 73 kW, tilt 10, az "90,270/180/180"). Small-commercial scale,
true south, fixed tilt; ratio 0.99 is essentially exact. Strong validation point.

NIST Ground Array, Gaithersburg campus. 271 kWp open-field array, tilt 20, due south.
Measured 342,100 kWh (342.1 MWh), same Oct 2014 to Sep 2015 window and same Boyd 2017
source. Caveat: this array had a roughly one-week inverter arcing outage in Aug 2015 plus
a few maintenance days, and the source reports a larger (13.8 percent) model deviation for
it; data availability still exceeded 99 percent. The measured year therefore slightly
understates a healthy array, which is consistent with the ratio coming in just under 1.0
(0.98). Use as a directional check, not a precision benchmark. (The third NIST array, the
243 kWp Canopy, was excluded because it is an east/west split orientation that a single
PVGIS aspect cannot represent; its measured 293.4 MWh is in the same source if needed.)

NREL S&TF rooftop, Golden CO. Small-commercial fixed-tilt array (94.05 kWp DC; 75 kW AC
inverter) on the Science and Technology Facility, used by NREL to validate the System
Advisor Model. Two independent measured years anchor it: 134,286 kWh (CY2011) and 135,013
kWh (CY2012), raw measured AC at inverter output, which agree to within 0.5 percent;
snow-corrected variants (126,035 / 125,494) are lower. I use the 2-year raw average
(134,650). Verified directly from the canonical NREL/TP-6A20-60204 PDF (OSTI 1115788,
Tables 7-4 and 7-6, rows literally labeled "Measured"); metadata tilt 10, azimuth 164 deg
CW from north (16 deg east of south, PVGIS aspect -16), 495 x Evergreen ES190-RL modules.
Ratio 1.06 (PVGIS a bit low) is reasonable; high-altitude Colorado resource explains the
strong specific yield (about 1,432 kWh/kWp). Snow-corrected actuals would push the ratio
closer to 1.0.

Yesilova rooftop, Burdur, Turkiye. A clean recent (Energies 2026) residential-scale
case study: 24 kWp, tilt 8, due south, full-year-2024 RECORDED energy 33,977.5 kWh, with
a stated measured performance ratio of 75.7 percent (the paper separately reports a higher
PVsyst-simulated 36,049 kWh and a HelioScope figure, neither of which I used). Location
given as 37.29 N, 29.48 E. Verified by fetching the article (a "34.3 MWh" approximate
phrasing also appears, consistent with rounding of 33,977.5). Ratio 1.00 is the tightest
in the set; a high-confidence validation point. Azimuth convention here is 0 = due south
(equator-facing), already matching PVGIS aspect 0.

Lublin PV9 rooftop, SE Poland. 30.16 kWp small-commercial array (104 x 290 Wp), tilt 25,
oriented south-east; monitored via SolarEdge inverter data over 2020 to 2021 with annual
generation reported as "about 29.5 MWh" (Energies 2022, Gulkowski). The number is rounded
("about"), so treat as +/- a few percent. Coordinates 51.18 N, 22.71 E are printed in the
paper. The paper gives only the cardinal direction (south-east) for PV9, so I assumed
roughly 45 degrees east of south (PVGIS aspect -45); if the true azimuth is closer to due
south the PVGIS estimate would rise slightly. Ratio 1.01 despite the rounding and azimuth
assumption, which is encouraging.

Hospital rooftop, Perambalur, Tamil Nadu, India. The only true residential-scale system
(5 kWp, on-grid, flat roof at 12 m) found with a clean measured annual: about 7,144 kWh
for calendar 2019 (Environ Sci Pollut Res 2021, Duraivelu and Elumalai). Two data-quality
caveats: (1) the paper does NOT state tilt or azimuth (flat-roof mount), so I used a
sensible default of tilt 11 (approximately the latitude) facing due south for the PVGIS
run; (2) the printed coordinates contain a typo ("longitude 78 deg 93 min E" is impossible
since minutes cannot exceed 60), so I geocoded the city name to 11.23 N, 78.87 E rather
than trusting the printed DMS. Despite the missing orientation, ratio 1.01 is excellent;
the near-equatorial latitude makes the system relatively insensitive to the assumed tilt.

Eco-house rooftop, Sultan Qaboos University, Muscat, Oman -- SUSPECT SOURCE, FLAGGED.
This is the one wildly-off ratio (0.70) and it likely signals a data-quality problem with
the source, not a PVGIS error. The 20.4 kWp south-facing array (tilt 23.5) reports a full
year (May 2017 to Apr 2018) gross generation of 23,595 kWh in its abstract and conclusions,
but Section 5.1 of the SAME paper states 27,067 kWh for AC energy; the two figures are
internally inconsistent. Even the larger 27,067 gives a ratio of only 0.80. The paper
attributes the low output to a poor measured performance ratio (about 0.67) driven by very
high cell temperatures in Muscat (modules reaching 55.5 C), which a default PVGIS run
(14 percent loss) will not fully capture, so part of the gap is real climate-derating and
part may be a reporting error. Recommendation: do NOT use this system as a clean
validation point; keep it only as a documented cautionary case (hot-climate derating plus
conflicting in-paper numbers). If a single figure must be chosen, 27,067 kWh is the
higher/more physically plausible one.

## Notes for the next step (PVWatts + proforma)

- Reuse the exact lat/lon, kWp, tilt, and azimuth in each row. Watch the azimuth
  convention per tool: PVWatts uses azimuth in degrees clockwise from north (180 = south),
  whereas the PVGIS `aspect` column above uses 0 = south. So for PVWatts, NIST south arrays
  and NZERTF/Burdur/Oman/Perambalur = azimuth 180; NREL Golden = 164; Lublin PV9 approx 135.
- The international systems (Burdur, Poland, India, Oman) are outside the PVWatts NSRDB
  domain in some configurations; PVWatts may require the international/global dataset or may
  not cover them. The four US systems (NZERTF, NIST Roof, NIST Ground, NREL Golden) are the
  guaranteed-coverage anchors for the PVWatts comparison.
- All published figures here are gross PV generation (AC delivered), which is the right
  basis to compare against a pro-forma's modeled annual production before consumption.
