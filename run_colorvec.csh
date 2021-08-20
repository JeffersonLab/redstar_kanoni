#!/bin/tcsh -x

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


/bin/rm -f hadron_node.xml

#set exe_red=/Users/edwards/Documents/qcd/git/devel/redstar-pdf/build/src
#set exe_col=/Users/edwards/Documents/qcd/git/devel/colorvec-pdf/build/src

#set exe_red=/Users/edwards/Documents/qcd/git/devel/redstar-colorvec/build/src
set exe_red=/Users/edwards/Documents/qcd/git/devel/redstar/build/src
set exe_col=/Users/edwards/Documents/qcd/git/devel/colorvec/build/src

#set exe_red=/Users/edwards/Documents/qcd/git/devel/tmp2/redstar/build/src
#set exe_col=/Users/edwards/Documents/qcd/git/devel/tmp/colorvec/build/src

#set exe_red=/home/edwards/qcd/git/devel/redstar/build/src
#set exe_col=/home/edwards/qcd/git/devel/colorvec/build/src

setenv OMP_NUM_THREADS 1

$exe_red/redstar_corr_graph $f out.xml >&! ${g}.corr.out
if ($status != 0) then
  echo "redstar_corr_graph failed"
  exit 1
endif

$exe_red/redstar_hadron_node $f out.xml >&! ${g}.node.out
if ($status != 0) then
  echo "redstar_hadron_node failed"
  exit 1
endif

$exe_col/hadron_node ./meson_hadron_node.xml out.xml >&! smeared.${f}.out
if ($status != 0) then
  echo "hadron_node failed"
  exit 1
endif

$exe_col/unsmeared_hadron_node ./unsmeared_meson_node.xml out.xml >&! unsmeared.${f}.out
if ($status != 0) then
  echo "colorvec failed"
  exit 1
endif

$exe_col/noneval_graph ./noneval_meson_graph.xml out.xml >&! noneval.${f}.out
if ($status != 0) then
  echo "colorvec failed"
  exit 1
endif

$exe_red/redstar_npt $f out.xml >&! ${g}.out
if ($status != 0) then
  echo "redstar_npt failed"
  exit 1
endif


