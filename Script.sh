#!/bin/bash

source ~/.bashrc

echo SLURM_JOB_NODELIST :  $SLURM_JOB_NODELIST  

RATIOSIMUNWORKERN=4
NWORKERPNODE=16
NCOREPPROC=1
NPROCPNODE=32

RATIO=$(($RATIOSIMUNWORKERN + 1 ))

NWORKER=$(($(($SLURM_NNODES - 1 )) / $RATIO))

NDASK=$(($NWORKER + 1 ))

NSIMU=$(($SLURM_NNODES - $NDASK))

NPROC=$(($NSIMU * $NPROCPNODE)) 


# Set OpenMP threads
export OMP_NUM_THREADS=$NCOREPPROC
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

SCHEFILE=scheduler.json
PYTH='/gpfs/workdir/gueroudjia/.conda/envs/PhDEnv/bin/python' 

module purge   
module load cmake/3.16.2/intel-19.0.3.199 gcc/9.2.0/gcc-4.8.5 openmpi/3.1.5/gcc-9.2.0

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/gpfs/workdir/gueroudjia/.conda/envs/PhDEnv/lib/
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/gpfs/workdir/gueroudjia/pdi-ph5_fix-c5d2e5c0a27b2b2de083c72d1412e9d7e4498ccc/build/staging/lib

env 

echo $PYTH
echo Used scheduler `which dask-scheduler`
echo Used python `which python`
echo Launching Scheduler 

# Launch Dask Scheduler in a 1 Node and save the connection information in $SCHEFILE
srun --relative=0  --cpu-bind=verbose --ntasks=1 --nodes=1 -l \
    --output=scheduler.log \
    $PYTH `which dask-scheduler` \
    --interface ib0 \
    --scheduler-file=$SCHEFILE   &


while ! [ -f $SCHEFILE ]; do
    sleep 3
    echo -n .
done

echo Connect Master Client  
$PYTH client.py &
client_pid=$!

echo Scheduler booted, launching workers 

# Launch Dask workers 
srun --relative=1  --nodes=$NWORKER  --cpu-bind=verbose  -l \
     --output=worker-%t.log \
     $PYTH `which dask-worker` \
     --interface ib0 \
     --nprocs $NWORKERPNODE \
     --local-directory /tmp \
     --scheduler-file=${SCHEFILE} &


echo Running Simulation 

${HOME}/local/bin/pdirun srun --distribution=block:block --relative=$NDASK --nodes=$NSIMU --ntasks=$NPROC --ntasks-per-node=$NPROCPNODE --cpus-per-task=$NCOREPPROC  --cpu-bind=verbose -l ./simulation &

wait $client_pid

#Cleaning
$PYTH postscript.py

