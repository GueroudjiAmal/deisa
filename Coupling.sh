#!/bin/bash

## prescript.py  
# sys.argv[1,2] : global_size.height/width
# sys.argv[3,4] : parallelism.height/width
# sys.argv[5] : generation 
# sys.argv[6] : gmax
# sys.argv[7] : nworker
# sys.argv[8] : timeStep

source $WORKDIR/spack/share/spack/setup-env.sh
spack load cmake@3.22.1
spack load pdiplugin-pycall

NWORKER=8

PARALLELISM1=2
PARALLELISM2=2

DATASIZE1=66560
DATASIZE2=61440

GENERATION=5
GMAX=100

mkdir -p $WORKDIR/Deisa
WORKSPACE=$(mktemp -d -p $WORKDIR/Deisa/ Dask-run-XXX)

cd $WORKSPACE
cp $DIR/simulation.yml $DIR/*.py  $DIR/Script.sh $DIR/Coupling.sh  $DIR/*.c $DIR/CMakeLists.txt  .
pdirun cmake .
make -B simulation
echo Running $WORKSPACE 
`which python` prescript.py $DATASIZE1 $DATASIZE2 $PARALLELISM1 $PARALLELISM2 $GENERATION $GMAX $NWORKER $TIMESTEP
sbatch Script.sh 
