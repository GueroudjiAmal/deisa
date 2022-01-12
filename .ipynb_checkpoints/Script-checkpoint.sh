#!/bin/bash

#SBATCH -J dask-cluster
#SBATCH -A dask_coupling
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --partition=cpu_med
#SBATCH --exclusive

NPROC=4                           # Total number of processes
NPROCPNODE=4                      # Number of processes per node
NWORKERPNODE=4                    # Number of Dask workers per node

SCHEFILE=scheduler.json

source $WORKDIR/spack/share/spack/setup-env.sh
spack load intel-mpi@2019.8.254%gcc@9.2.0 pdiplugin-pycall
spack load py-pyyaml
spack load py-dask
spack load py-distributed 
spack load py-bokeh 


# Launch Dask Scheduler in a 1 Node and save the connection information in $SCHEFILE
echo launching Scheduler 
srun --cpu-bind=verbose --ntasks=1 -l \
    --output=scheduler.log \
    dask-scheduler \
    --interface ib0 \
    --scheduler-file=$SCHEFILE   &

# Wait for the SCHEFILE to be created 
while ! [ -f $SCHEFILE ]; do
    sleep 3
    echo -n .
done

# Connect the client to the Dask scheduler
echo Connect Master Client  
`which python` client.py &
client_pid=$!

# Launch Dask workers in the rest of the allocated nodes 
echo Scheduler booted, Client connected, launching workers 
srun --nodes=$NWORKER  --cpu-bind=verbose  -l \
     --output=worker-%t.log \
     dask-worker \
     --interface ib0 \
     --local-directory /tmp \
     --nprocs $NWORKERPNODE \
     --scheduler-file=${SCHEFILE} &
     
# Launch the simulation code
echo Running Simulation 
pdirun srun  --ntasks=$NPROC --ntasks-per-node=$NPROCPNODE  -l ./simulation  &

# Wait for the client process to be finished 
wait $client_pid
