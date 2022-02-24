#!/bin/tcsh -x

#source /dist/intel/parallel_studio_xe_2016.3.067/psxevars.sh intel64

if ($#argv != 1) then
  echo "Usage: $0  <redstar xml input file>"
  exit 1
endif

set f=$1

if (! -f $f) then
  echo "redstar input file does not exist: $f"
  exit 1
endif

set g=${f:r}

set exe_red=/Users/edwards/Documents/qcd/git/devel/redstar.devel/build/src

$exe_red/redstar_corr_graph $f out.xml >&! ${g}.corr.out
if ($status != 0) then
  echo "redstar_corr_graph failed"
  exit 1
endif

$exe_red/redstar_npt $f out.xml >&! ${g}.out
if ($status != 0) then
  echo "redstar_npt failed"
  exit 1
endif


