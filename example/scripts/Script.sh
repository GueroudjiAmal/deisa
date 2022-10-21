#!/bin/bash
###################################################################################################
# Copyright (c) 2020-2022 Centre national de la recherche scientifique (CNRS)
# Copyright (c) 2020-2022 Commissariat a l'énergie atomique et aux énergies alternatives (CEA)
# Copyright (c) 2020-2022 Institut national de recherche en informatique et en automatique (Inria)
# Copyright (c) 2020-2022 Université Paris-Saclay
# Copyright (c) 2020-2022 Université de Versailles Saint-Quentin-en-Yvelines
#
# SPDX-License-Identifier: MIT
#
###################################################################################################

NNODES=$(($SLURM_NNODES-2))
WORKERNODES=$(($NNODES/3))
SIMUNODES=$(($WORKERNODES*2))
NPROC=$(($SIMUNODES*2))                   # Total number of processes
NWORKER=$(($WORKERNODES*2))

export DASK_DISTRIBUTED__COMM__UCX__INFINIBAND=True
source $CCCWORKDIR/env_spackuser
#export UCXPY_LOG_LEVEL=DEBUG
export UCX_TLS=ib

SCHEFILE=scheduler.json

echo launching Scheduler 
ccc_mprun -N 1  -n 1 -c 24 -r 0  dask-scheduler   --protocol ucx  --scheduler-file=$SCHEFILE 1>> scheduler.o  2>> scheduler.e  &

# Wait for the SCHEFILE to be created 
while ! [ -f $SCHEFILE ]; do
    sleep 3
    echo -n .
done


# Connect the client to the Dask scheduler
echo Connect Master Client  
ccc_mprun  -N 1 -n 1 -c 24 -r 1   `which python` -m trace -l -g derivative.py 1>> client.o 2>> client.e &
client_pid=$!

# Launch Dask workers in the rest of the allocated nodes 
echo Scheduler booted, Client connected, launching workers 
ccc_mprun  -N $WORKERNODES -n $NWORKER -c 24 -r 2   dask-worker --local-directory /tmp  --scheduler-file=${SCHEFILE} 1>> worker.o 2>>worker.e  &
     
REL=$(($WORKERNODES+2))
# Launch the simulation code
echo Running Simulation 
ccc_mprun  -N $SIMUNODES -n $NPROC -c 24 -r $REL  ./simulation 1>> simulation.o 2>> simulation.e &

# Wait for the client process to be finished 
wait $client_pid
wait 


