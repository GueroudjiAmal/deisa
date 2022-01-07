# DEISA : Dask-Enabled In Situ Analytics :

Deisa is a tool that couples MPI simulations with Dask analytics in situ. The generated data by the simulation is sent to Dask workers to be processed. In this Repo there is an example of a 2D heat solver that generates a 2D array at each time step. This 2D array is sent to the dask workers and processed using `Dask.Array` API. 

To run the example : `bash Launcher.sh`. 

## Pre-requirement : 

- Install [PDI Data Interface](https://pdi.dev/master/) with pycall support, [spack](https://github.com/pdidev/spack) installation is recomended.  
- Dask Distributed

## Some pointers :

- Launcher.sh and Script.sh lauch the experiment
- client.py contains the analytics code 
- simulation.yml contains the pdi configuration, here we use pycall that calls some functions form dask_interface.py

## Paper :

For more details check [DEISA: Dask-Enabled In Situ Analytics](https://hal-sciencespo.archives-ouvertes.fr/CEA-UPSAY/hal-03509198v1) 
