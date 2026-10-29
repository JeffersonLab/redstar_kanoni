#!/bin/tcsh
# Alternate entry point for the precomputed-SDB workflow.
# Pass an explicit XML path, e.g. test_inputs/pipi_i1.xml.
set script_dir = "$0:h"
if ("$script_dir" == "$0") set script_dir = "."
exec python3 "$script_dir/scripts/run_colorvec.py" $argv:q
