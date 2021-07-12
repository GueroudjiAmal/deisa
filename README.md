# DEISA : Dask-Enabled In Situ Analytics :

Deisa is a tool that couples MPI simulation to Dask analytics in situ. The generated data by the simulation is sent to Dask to be processed. In this Repo there is an example of a 2D heat solver 
that generates a 2D array at each time step. This 2D array is sent to the dask workers and processed 
using an Incremental PCA. 

To run the example : `bash Coupling.sh`

## Pre-requirement : 

- Conda environment with needed libraries (Dask distributed ...)
- Install PDI with pycall and python support, use the python interpret of your conda env  (https://pdi.julien-bigot.fr/master/ , something like -DPython3_EXECUTABLE=${WORKDIR}/.conda/envs/YourEnv/bin/python in your cmake configuration while building pdi) 

## Some pointers :

- Coupling.sh and Script.sh lauch the experiments
- client.py contains the analytics code 
- simulation.yml contains the pdi configuration, here we use pycall that calls some functions form dask_interface.py

