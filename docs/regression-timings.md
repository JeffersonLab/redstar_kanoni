# Final native-double regression timings

The RsdCG=1e-14 v11 sweep in `runs/native-comparison-matrix-20261101-004` passed all 29 active cases on both devel and experimental no_1pt. Five cases per chain are explicitly deferred. Independent audit checked expected keys/time shapes, 8,380 finite compared values, zero strict failures, and executable hashes.

Both evaluators use stored native tensors. CORR_SUPERB reads the three per-mass `prop-U*.sbt` files and both GenProp files; **all 58 Chroma jobs performed zero CG solves**. These are SUPERB tensor files rather than the legacy monolithic prop.sdb.

Across both chains NPT totals 587.069 seconds and CORR_SUPERB totals 532.736 seconds. Graph construction, XML/key export, validation, and earlier debugging/regeneration add wall time beyond those evaluator totals. Runs use one OpenMP/BLAS thread per job, a 2 GiB tensor budget, and an 8 GiB RSS cap; these are observed local timings, not a controlled benchmark. The executable remains an incremental corrected pre-YLM snapshot.

| Case | Chain | NPT seconds | CORR_SUPERB seconds | CG solves |
|---|---|---:|---:|---:|
| rho_rho_3pt | devel | 86.601 | 46.221 | 0 |
| rho_rho_3pt | no_1pt | 62.278 | 48.742 | 0 |
| 3pi | no_1pt | 35.543 | 45.364 | 0 |
| 3pi | devel | 44.730 | 43.220 | 0 |
| nucnuc_small | no_1pt | 25.619 | 38.586 | 0 |
| nucnuc_small | devel | 25.044 | 37.312 | 0 |
| 33 | devel | 28.933 | 30.140 | 0 |
| h8 | devel | 29.862 | 19.931 | 0 |
| 33 | no_1pt | 24.413 | 27.628 | 0 |
| a0.d3 | devel | 18.689 | 22.308 | 0 |
| a0.d3 | no_1pt | 18.469 | 22.144 | 0 |
| h8 | no_1pt | 14.272 | 19.884 | 0 |
| hard.1_tslice.ini | devel | 6.512 | 10.507 | 0 |
| hard.1_tslice.ini | no_1pt | 6.382 | 10.337 | 0 |
| d | devel | 4.806 | 6.766 | 0 |
| d | no_1pt | 4.576 | 6.455 | 0 |
| nucpi_I3o2 | devel | 4.802 | 3.738 | 0 |
| nucpi_I3o2 | no_1pt | 4.654 | 3.808 | 0 |
| nucpi_nucpi_J1o2m | devel | 4.371 | 3.895 | 0 |
| nucpi_nucpi_J1o2m | no_1pt | 4.249 | 3.769 | 0 |
| pion | no_1pt | 3.897 | 2.439 | 0 |
| a1_rhopi | devel | 3.721 | 2.539 | 0 |
| nucpi | devel | 3.650 | 2.374 | 0 |
| nucpi | no_1pt | 3.632 | 2.346 | 0 |
| 1pt | devel | 3.614 | 2.255 | 0 |
| pi | devel | 3.597 | 2.166 | 0 |
| nucpi_J1o2m | no_1pt | 3.591 | 2.272 | 0 |
| pipi_i1 | devel | 3.538 | 2.107 | 0 |
| a1_rhopi | no_1pt | 3.536 | 2.549 | 0 |
| pi | no_1pt | 3.527 | 2.189 | 0 |
| 1pt | no_1pt | 3.520 | 2.136 | 0 |
| nuc_nuc_ax_3pt | devel | 3.490 | 2.100 | 0 |
| nuc_nuc_ax_3pt | no_1pt | 3.481 | 2.123 | 0 |
| delta_J1o2m | no_1pt | 3.466 | 2.158 | 0 |
| pion | devel | 3.457 | 2.120 | 0 |
| rho | no_1pt | 3.456 | 2.099 | 0 |
| nuc | devel | 3.442 | 2.080 | 0 |
| eta8eta8_F8 | devel | 3.440 | 2.057 | 0 |
| pipi_i1 | no_1pt | 3.434 | 2.152 | 0 |
| delta_J1o2m | devel | 3.430 | 2.122 | 0 |
| nuc | no_1pt | 3.427 | 2.098 | 0 |
| nuc.p100 | no_1pt | 3.427 | 2.061 | 0 |
| psi | devel | 3.425 | 2.113 | 0 |
| psi | no_1pt | 3.419 | 2.061 | 0 |
| nuc_gA | devel | 3.418 | 2.086 | 0 |
| nuc_gA | no_1pt | 3.418 | 2.144 | 0 |
| nucpi_J1o2m | devel | 3.415 | 2.117 | 0 |
| pion_3pt | devel | 3.414 | 2.079 | 0 |
| rho | devel | 3.414 | 2.107 | 0 |
| pion_3pt | no_1pt | 3.404 | 2.082 | 0 |
| pi_pi_3pt | devel | 3.401 | 2.034 | 0 |
| nuc.p100 | devel | 3.400 | 2.097 | 0 |
| eta8eta8_F8 | no_1pt | 3.398 | 2.073 | 0 |
| nuc_nuc_proj_3pt | no_1pt | 3.398 | 2.145 | 0 |
| eta_eta_3pt | devel | 3.395 | 2.090 | 0 |
| pi_pi_3pt | no_1pt | 3.393 | 2.045 | 0 |
| nuc_nuc_proj_3pt | devel | 3.390 | 2.071 | 0 |
| eta_eta_3pt | no_1pt | 3.388 | 2.093 | 0 |
