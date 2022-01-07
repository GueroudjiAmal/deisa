#!/bin/bash

## prescript.py  
# sys.argv[1,2] : global_size.height/width
# sys.argv[3,4] : parallelism.height/width
# sys.argv[5] : generation 
# sys.argv[6] : gmax
# sys.argv[7] : nworker
# sys.argv[8] : timeStep

DIR=$PWD

source $WORKDIR/spack/share/spack/setup-env.sh
spack load cmake@3.22.1
spack load intel-mpi@2019.8.254%gcc@9.2.0
spack load pdiplugin-pycall
spack load py-pyyaml

NWORKER=8

PARALLELISM1=2
PARALLELISM2=2

DATASIZE1=1024
DATASIZE2=1024

GENERATION=5
GMAX=100

TIMESTEP=1

mkdir -p $WORKDIR/Deisa
WORKSPACE=$(mktemp -d -p $WORKDIR/Deisa/ Dask-run-XXX)

cd $WORKSPACE
cp $DIR/simulation.yml $DIR/*.py  $DIR/*.sh  $DIR/*.c $DIR/CMakeLists.txt  .
pdirun cmake .
make -B simulation
echo Running $WORKSPACE 
`which python` prescript.py $DATASIZE1 $DATASIZE2 $PARALLELISM1 $PARALLELISM2 $GENERATION $GMAX $NWORKER $TIMESTEP
sbatch Script.sh 
