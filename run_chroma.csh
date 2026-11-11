#!/bin/tcsh
# Standalone saved-field CORR_SUPERB; select REDSTAR_BIN and CHROMA_BIN explicitly.
set script_dir = "$0:h"
if ("$script_dir" == "$0") set script_dir = "."
exec python3 "$script_dir/scripts/run_chroma.py" $argv:q
