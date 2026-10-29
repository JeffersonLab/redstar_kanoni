#!/bin/tcsh
# Compatibility entry point for the precomputed-SDB workflow.
set script_dir = "$0:h"
if ("$script_dir" == "$0") set script_dir = "."
exec python3 "$script_dir/scripts/run_colorvec.py" $argv:q
