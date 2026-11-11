#!/bin/tcsh
# Pass an explicit XML path, e.g. test_inputs/pipi_i1.xml.
# Select an absolute REDSTAR_BIN directory or --redstar-bin; --tools accepts bin directories.
# Combined XML is a development convenience; production uses separate inputs.
set script_dir = "$0:h"
if ("$script_dir" == "$0") set script_dir = "."
exec python3 "$script_dir/scripts/run_colorvec.py" $argv:q
