# DEISA: Dask-Enabled In Situ Analytics

_**DEISA**_ is a library that ensures coupling MPI simulation codes with Dask analytics.

**_DEISA_** plugin is built on [PDI Data Interface](https://pdi.dev/master/).

## Requirements

_**DEISA**_ as a PDI plugin requires the [PDI Data Interface](https://pdi.dev/master/) to be installed with python support.

_**DEISA**_ requires Dask and [Dask Distributed deisa verion](https://github.com/GueroudjiAmal/distributed) that has been adapted to work with the new introduced concepts in _**DEISA**_

## Installation

Check [here](https://github.com/pdidev/spack#deisa) for spack installation.

Or it can be  installed on top of PDI by running:

```
  cmake -DCMAKE_INSTALL_PREFIX=$HOME/local/  -DPython3_EXECUTABLE=~/.conda/envs/yourenv/bin/python3.8  ../
  make install
```

## How it works ?

A simulation can be instrumented with PDI to make its internal data available for **_DEISA_** thus **Dask** . At the beginning each simulation process reads the *yaml* configuration file and loads the **_DEISA_** and the **_MPI_** plugins of PDI.

Internally, a **_DEISA Bridge_** is created per MPI process, and they connect to **_Dask_**. The bridge which is associated with the process rank 0, reads the `deisa_virtual_arrays` section in the *yaml* file and send it to the **_DASK_** client.
 Once a piece of data is shared with PDI, the Bridge checks if it is included in the contract then it sends it to a worker that has been chosen in a round-robin fashion with a specific key, else it returns.

**_DEISA_** python library implements a **_DEISA Adaptor_**. This component is used from the **_Dask_**  client-side to create Dask arrays describing the data generated by the simulation. The **_DEISA Adaptor_** waits for contract to be sent from the **_DEISA Bridge_** in MPI rank 0, it selects needed data and sign back the contract. It uses the information containted in the contract to create Dask arrays, that can be retrieved by calling `get_deisa_arrays()` method then select the needed array.

# Example :
An example is included in this repository, it includes the submission scripts that suppose a previous spack installation.
