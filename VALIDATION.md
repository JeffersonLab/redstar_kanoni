# Input validation, 2026-10-28

The immutable public Kanoni v1 dataset and the installed macOS Apple Clang/libomp
stack were used. The toolchain independently observed OpenMP teams of one and four;
these input runs requested four. Source revisions, original tested input hashes, counts and
per-case limits are recorded in [validation-reference.json](test_inputs/validation-reference.json).
The source-tree C++ code was unchanged. Local full logs and failed attempts remain
under `runs/validation-*`; the compact JSON is the versioned record.

## Later data-directory migration

The original full-sweep record above is historical. Actual SDBs now live as regular
files in `data/`; tracked numerical XMLs use `../data/` and runners generate relative
paths from fresh run directories. Payload checksums and every non-database-path
XML field were preserved. Original run inputs/reports and their tested hashes
remain unchanged. [data-layout-validation.json](test_inputs/data-layout-validation.json)
maps those hashes to current path-only edits and records the fresh numerical checks.
The full-sweep pass counts below are not a claim that the resource-limited a1 case
was rerun or that missing data became available.

## Redstar numerical inputs

| Input | Result | Keys | Graphs | Times |
| --- | --- | ---: | ---: | ---: |
| 1pt.xml | real data passed | 3 | 13 | 16 |
| 33.xml | real data passed | 1 | 4446 | 16 |
| 3pi.xml | real data passed | 3 | 6775 | 16 |
| a0.d3.xml | real data passed | 324 | 15988 | 4 |
| a1.000_T1pM.xml | resource limited; unvalidated | — | — | 16 |
| a1_rhopi.xml | real data passed | 1 | 66 | 16 |
| d.xml | real data passed | 1 | 144 | 16 |
| da_3pt.xml | needs additional SDB keys | 1 | 2 | 7 |
| delta_J1o2m.xml | real data passed | 1 | 6 | 16 |
| eta8eta8_F8.xml | real data passed | 1 | 2 | 16 |
| eta_eta_3pt.xml | exact zero control | 1 | 0 | 16 |
| ff_3pt.xml | real data passed | 1 | 2 | 16 |
| fsq_3pt.xml | real data passed | 2 | 3 | 16 |
| glue.xml | real data passed | 1 | 2 | 16 |
| h8.xml | real data passed | 4 | 3504 | 16 |
| hard.1_tslice.ini.xml | real data passed | 529 | 3969 | 4 |
| kpi_3pt.xml | needs additional SDB keys | 3 | 18 | 7 |
| nuc.p100.xml | real data passed | 2 | 4 | 7 |
| nuc.xml | real data passed | 1 | 2 | 16 |
| nuc_gA.xml | real data passed | 1 | 6 | 7 |
| nuc_nuc_3pt.xml | real data passed | 1 | 9 | 7 |
| nuc_nuc_ax_3pt.xml | real data passed | 4 | 24 | 7 |
| nuc_nuc_proj_3pt.xml | real data passed | 1 | 6 | 7 |
| nucnuc_small.xml | real data passed | 2 | 8804 | 4 |
| nucpi.xml | real data passed | 1 | 10 | 16 |
| nucpi_I3o2.xml | real data passed | 1 | 208 | 16 |
| nucpi_J1o2m.xml | real data passed | 1 | 6 | 16 |
| nucpi_nucpi_J1o2m.xml | real data passed | 2 | 75 | 16 |
| pi.xml | real data passed | 1 | 1 | 16 |
| pi_pi_3pt.xml | real data passed | 1 | 2 | 6 |
| pion.xml | real data passed | 3 | 1 | 16 |
| pion_3pt.xml | real data passed | 1 | 2 | 7 |
| pion_DA.xml | fake data only | 1 | 1 | 7 |
| pion_pdf_3pt.xml | fake data only | 1 | 2 | 6 |
| pipi_i1.xml | real data passed | 1 | 4 | 16 |
| psi.xml | real data passed | 2 | 2 | 16 |
| rho.xml | real data passed | 3 | 3 | 16 |
| rho_rho_3pt.xml | real data passed | 27 | 20829 | 7 |
| tetra_F27_S2.xml | real data passed | 3 | 4 | 16 |

The full a1 attempt was stopped for resource use after a sampled memory footprint
of about 37 GB on this 32 GiB Mac, with about 11.5 GiB of system swap in use.
It was actively expanding and combining Wick diagrams. The original 121-correlator
selection is preserved. This case has **no completed graph/numerical/readback
validation**; use a larger-memory host or first validate a strategy for splitting
the work. Both the earlier timeout and this resource-limited attempt are retained.


The eta–eta endpoints are isosinglets and the insertion has I=1. This input
correctly gives no graphs and one identically zero correlator; it is recorded
as a negative selection control. `pion_DA.xml` and `pion_pdf_3pt.xml` deliberately
retain their original fake-data mode. They do not establish real-data coverage.

The user chose to preserve both missing-data inputs and document the limits:

- **da_3pt.xml:** Required backward genprop has t_sink=6, t_source=0, t_slice=0, g=4, displacement=-3, mom=(0,0,-1), mass=U0.05. No displacement -3 keys exist in the pinned genprop database; forward endpoint (0,6) is absent too.
- **kpi_3pt.xml:** Required genprops include mass U0.1 at momentum (+/-1,0,0), g=1, with endpoints (0,6)/(6,0). The pinned genprop database has U0.1 data but no (+/-1,0,0) momenta. Requested physical momenta are preserved.

No new SDB values were invented and fake-data mode was not enabled to hide a
failure. The strict full suite returns nonzero for missing-data cases.

## Deliberate compatibility repairs

- Converted legacy SUN operators through the installed converter, including joint
  rotations of two-constituent momenta. Kept zero phasings, masses, flavor labels,
  creation flags and time settings. Runtime projected weights use v4.
- Replaced unsupported fixed-CG mode in the legacy hard and KPI cases. KPI also
  requires CG rotation from its class representative to its requested physical
  momentum; the physical momentum remains unchanged.
- a1 retained old projected-name aliases and equal nonzero constituent vectors
  in two explicitly zero-total pairs. Factory aliases and back-to-back second
  vectors repair those definitions without changing the intended rest-frame basis.
- ff now selects the modern FSq backend and `gpdf.more.sdb`, which contains its
  existing smearing `1.80` and Lorentz/displacement keys. Its current is unchanged.

All migration attempts save originals and typed-converter output in fresh
`runs/input-migration-*` directories. Large unchanged XML regions retain their
original layout; parsed-tree equality was checked after formatting-only edits.

For `33.xml` and `3pi.xml`, full descriptive dbutil filenames exceed 255 bytes.
dbutil can return zero without writing them. The numbered-file exporter checks
stream errors, records full keys, and validates every complex value; its key set
must equal independent `dbutil keysxml` output.

## Other XML schemas

These are generator inputs or operator maps, not `RedstarNPt` v14 inputs. Their
own schemas were preserved. The self-contained generators were actually run:

| Input | Executable | Raw list | Selected map |
| --- | --- | ---: | ---: |
| 3pi.ini.xml | generate_nonint_spectrum_3ops | 190 | 48 |
| h1.ini.xml | generate_nonint_spectrum_3ops | 124 | 52 |
| h8.ini.xml | generate_all_possible_nonint_spectrum | 260 | 260 |

Three-body raw lists include names excluded by symmetry filtering. Before passing
a generated list downstream, filter it against the generated `OpsList` map; a
successful generator exit is not evidence that every raw list entry is selected.

Three older generator templates are not self-contained and were not claimed as
passing executions:

- `generate_redstar_2pt.ini.xml` lacks its selected `orthog.list`.
- `rho_rho_3pt.ini.xml` lacks `rho.ops.list`, `rho.ops.xml`, and the insertion list/map.
- `3pt.ini.xml` lacks `rho.small2.dat`, rho/insertion maps and `b0.ops.xml`.

Keep their intended bases rather than substitute an unrelated selection. The
complete, runnable compact generators are in Redstar’s
[rho–rho](https://github.com/JeffersonLab/redstar/tree/devel/src/generate_all_3pt_spectrum/rho_rho)
and [a0–omega](https://github.com/JeffersonLab/redstar/tree/devel/src/generate_all_3pt_spectrum/a0_omega)
examples. Both were rerun with the new Kanoni home: 83/16 keys, 5/12 operators,
seven time samples and finite complex values.

## Repeating the checks

Run `python3 scripts/validate_inputs.py --help`, then the commands in the root
[README](README.md). `--timeout` is a per-executable limit, and selected filenames
can follow the options. Keep every attempt in its new output directory. A requested
worker count alone does not demonstrate OpenMP support: use Redstar’s clean builder
and its observed-team checks for the underlying installation.

These one-configuration results validate software/data interfaces, not ensemble
statistics or physical matrix elements. Replica fits belong to matelem_fitter/example.
