#!/bin/tcsh
# Pass an explicit XML path, e.g. test_inputs/pipi_i1.xml.
# REDSTAR_BIN may name build/src or install/bin; --tools selects executable TOML.
# Combined XML is a development convenience; production uses separate inputs.
set script_dir = "$0:h"
if ("$script_dir" == "$0") set script_dir = "."
exec python3 "$script_dir/scripts/run_colorvec.py" $argv:q
