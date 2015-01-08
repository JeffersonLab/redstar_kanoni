#!/bin/tcsh -x

if ($#argv != 1) then
  echo "Usage: $0  <redstar xml input file>"
  exit 1
endif

set t="meson_hadron_node.xml"
set f=$1

if (! -f $t) then
  echo "meson_hadron_node template file does not exist: $t"
  exit 1
endif

if (! -f $f) then
  echo "redstar input file does not exist: $f"
  exit 1
endif

set g=${f:r}


/bin/rm -f hadron_node.xml

set exe_red=/Users/edwards/Documents/qcd/git/devel/redstar/build/src
set exe_col=/Users/edwards/Documents/qcd/git/devel/colorvec/build/src
set exe_har=/Users/edwards/Documents/qcd/git/devel/harom/scalar-Nd3/mainprogs/main

#set exe_red=/home/edwards/qcd/git/devel/redstar/build/src
#set exe_col=/home/edwards/qcd/git/devel/colorvec/build/src
#set exe_har=/home/edwards/qcd/git/devel/harom/scalar-Nd3/mainprogs/main

setenv OMP_NUM_THREADS 4

$exe_red/redstar_gen_graph $f out.xml >&! ${g}.gen.out
if ($status != 0) then
  echo "redstar_gen_graph failed"
  exit 1
endif

$exe_col/hadron_node ${t} out.xml >&! had.${f}.out
if ($status != 0) then
  echo "hadron_node failed"
  exit 1
endif

$exe_har/harom -i ./harom_hadron_node.xml -o out.xml >&! harom.${f}.out
if ($status != 0) then
  echo "harom failed"
  exit 1
endif

$exe_red/redstar_npt $f out.xml >&! ${g}.out
if ($status != 0) then
  echo "redstar_npt failed"
  exit 1
endif


