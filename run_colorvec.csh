#!/bin/tcsh
# REDSTAR_BIN may name build/src or install/bin; otherwise use PATH.
set script_dir = "$0:h"
if ("$script_dir" == "$0") set script_dir = "."
exec python3 "$script_dir/scripts/run_colorvec.py" $argv:q
