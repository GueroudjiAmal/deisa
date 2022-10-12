import sys
import os

import dask
import dask.array as da
from dask.array import Array
from dask.delayed import Delayed
from dask.distributed import Client, Event, get_client, comm, Queue, Future, Variable
import numpy as np
import itertools
import asyncio

from contextlib import redirect_stdout
import json
import yaml

import time
import trace


def Deisa(scheduler_info, config):
    os.environ["DASK_DISTRIBUTED__COMM__UCX__INFINIBAND"]= "True"
    with open(config) as file:
        data = yaml.load(file, Loader=yaml.FullLoader)
        Sworkers = data["workers"]
    return Adaptor(Sworkers, scheduler_info)

def connect(sched_file):
    sched = ''.join(chr(i) for i in sched_file)
    with open(sched[:-1]) as f:
        s = json.load(f)
    adr = s["address"]
    try:
        client  = Client(adr)
    except Exception as e:
        print("retrying ...", flush=True)
        client = Client(adr)
    return client

def init(sched_file, rank, size, arrays, deisa_arrays_dtype):
    os.environ["DASK_DISTRIBUTED__COMM__UCX__INFINIBAND"]= "True"
    client = connect(sched_file)
    return Bridge(client, size, rank, arrays, deisa_arrays_dtype)

class deisa_array:
    """
    Deisa virtual array class
    """

    def __init__(self, name, array, selection="All"):
        self.name = name
        self.array = array
        self.selection = selection

    def normalize_slices(self, ls):
        ls_norm = []
        if isinstance(ls, (tuple, list)):
            for s in ls:
                ls_norm.append(self.normalize(s,ls.index(s)))
            return tuple(ls_norm)

    def normalize_slice(self,s,index):
        if s[0] == None:
            s[0] = 0

        if s[1] == None:
            s[1] = self.array.shape[index]

        if s[2] == None:
            s[2] = 1

        elif s[2] < 0 :
            raise ValueError(
                f"{s} only positive step values are accepted"
            )
        for i in range(2):
            if s[i] < 0:
                s[i] = self.array.shape[index]+ s[i]
        return tuple(s)

    def __getitem__(self, slc):
        selection = []
        default = [None, None, None]
        if isinstance(slc, slice):
            selection.append(self.normalize_slice([slc.start, slc.stop, slc.step], 0))
        elif isinstance(slc, tuple):
            for s in range(len(slc)):
                if isinstance(slc[s], slice):
                    selection.append(self.normalize_slice([slc[s].start, slc[s].stop, slc[s].step], s))
                elif isinstance(slc[s], int):
                    if slc[s]>= 0:
                        selection.append((slc[s], slc[s]+1, 1))
                    else:
                        selection.append((slc[s]+self.array.shape[s], slc[s]+self.array.shape[slc.index(s)]+1, 1))
                elif isinstance(slc[s], type(Ellipsis)):
                    selection.append(self.normalize_slice([0, None, 1], s))
        elif isinstance(slc, int):
            if slc>= 0:
                selection.append((slc, slc+1, 1))
            else:
                selection.append((slc+ self.array.shape[0], slc + self.array.shape[0] + 1, 1))
        elif isinstance(slc, type(Ellipsis)):
            selection.append((0, self.array.shape[0], 1))
        else:
            raise ValueError(
                f"{slc} ints, sclices and Ellipsis only are supported"
            )
        self.selection = selection
        return self.array.__getitem__(slc)


    def get_name(self):
        return self.name

    def get_array(self):
        return self.array

    def set_selection(self, slc):
        self.selection = stc

    def reset_selection(self):
        self.selection = "All"

    def gc(self):
        del self.array

class deisa_arrays:
    """
    Deisa virtual arrays class
    """

    def __init__(self, arrays):
        self.arrays = []
        self.contract = None
        for name, array in arrays.items():
            self.arrays.append(deisa_array(name, array))

    def __getitem__(self, name):
        for dea in self.arrays:
            if dea.get_name() == name:
                return dea
        raise ValueError(
                f"{name} array does not exist in Deisa data store"
            )

    def add_deisa_array(self, deisa_a, name=None):
        if isinstance(deisa_a, deisa_array):
            self.arrays.append(deisa_a)
        elif isinstance(deisa_a, Array) and isinstance(name, str):
            self.arrays.append(deisa_array(deisa_a, name))

    def get_deisa_array(self, name):
        return self.__getitem__(name)

    def drop_arrays(self, names):
        if isinstance(names, str):
            self.arrays[names].set_selection(None)
        elif isinstance(names, list):
            for a in names:
                self.arrays[a].set_selection(None)

    def reset_contract(self):
        for dea in self.arrays:
            dea.reset_selection()

    def check_contract(self):
        if self.contract == None:
            self.generate_contract()
        return self.contract

    def generate_contract(self):
        self.contract = {}
        for a in self.arrays:
            self.contract[a.name] =  a.selection

    def validate_contract(self):
        print("Generated contract", self.contract, flush=True)
        contract = Variable("Contract")
        print("Contract has been signed", flush=True)
        contract.set(self.contract)
        self.gc()

    def gc(self):
        for a in self.arrays:
            a.gc()
        print("Original arrays deleted", flush=True)


class Bridge:
    """
    Deisa Bridge class
    """

    def __init__(self, Client, Ssize, rank, arrays, deisa_arrays_dtype):
        self.client  = Client
        self.rank = rank
        self.contract = None
        listw = Variable("workers").get()
        if Ssize > len(listw): # more processes than workers
            self.workers = [listw[rank%len(listw)]]
        else:
            k = len(listw)//Ssize # more workers than processes
            self.workers = listw[rank*k:rank*k+ k]
        self.arrays = arrays
        for ele in self.arrays:
            self.arrays[ele]["dtype"] = str(deisa_arrays_dtype[ele])
            self.arrays[ele]["timedim"] = self.arrays[ele]["timedim"][0]
            self.position = [self.arrays[ele]["starts"][i]//self.arrays[ele]["subsizes"][i] for i in range(len(np.array(self.arrays[ele]["sizes"])))]
        if rank==0:
            Queue("Arrays").put(self.arrays) # If and only if I have a perfect domain decomposition

    def create_key(self, name):
        position = tuple(self.position)
        return ("deisa-"+name, position)

    def publish_request(self, data_name, timestep):
        try:
            selection = self.contract[data_name]
        except KeyError:
            return False
        self.position[self.arrays[data_name]["timedim"]]= timestep
        if selection == "All":
            return True
        elif selection == None:
            return False
        elif isinstance(selection, (list, tuple)):
            starts = np.array(self.arrays[data_name]["starts"])
            ends = np.array(self.arrays[data_name]["starts"]) + np.array(self.arrays[data_name]["subsizes"])
            sizes = np.array(self.arrays[data_name]["subsizes"])

            if timestep >= selection[0][1] or timestep < selection[0][0] or (timestep - selection[0][0])%selection[0][2] != 0: # if not needed timestep
                return False

            else: # wanted timestep
                for i in range(1,len(selection)):
                    s = selection[i] # i is dim
                    if starts[i] >= s[1] or ends[i] < s[0] or (ends[i] % s[2]) > sizes[i]:
                        return False
                # if there is at least some data for a dim
            return True


    def publish_data(self, data, data_name, timestep):

        if self.contract == None:
            self.contract = Variable("Contract").get()
        publish = self.publish_request(data_name, timestep)
        if publish:
            key = self.create_key(data_name)
            shap = list(data.shape)
            new_shape = tuple(shap[:self.arrays[data_name]["timedim"]]+[1]+shap[self.arrays[data_name]["timedim"]:])
            data.shape = new_shape #TODO will not copy, if not possible raise an error so handle it :p
            ts = time.time()

            tracer = trace.Trace(count=0, trace=0, countfuncs=1, countcallers=1)
            f = self.client.scatter(data, direct = True, workers=self.workers, keys=[key], deisa=True)
            while (f.status != 'finished' or f==None ):
                f = self.client.scatter(data, direct = True, workers=self.workers, keys=[key], deisa=True)
            allstats = "stats_r"+str(self.rank)+".t"+str(timestep)
            debug = "debug_r"+str(self.rank)+".t"+str(timestep)
            callgrind = "callgrind_r"+str(self.rank)+".t"+str(timestep)

            ts = time.time() - ts
            print("scatter et profiling  : ", ts,"secondes" , flush=True )
            data=None
        else:
            #print(data_name, "is not shared from process", self.position, " in timestep", timestep, flush=True)
            pass

class Adaptor:
    """
    Deisa Adaptor Class
    """

    adr = ""
    client = None
    workers = []
    def __init__(self, Sworker, scheduler_info):
        with open(scheduler_info) as f:
            s = json.load(f)
        self.adr = s["address"]
        try:
            self.client  = Client(self.adr)
        except Exception as e:
            print("retrying ...", flush=True)
            self.client = Client(self.adr)

        # Check if client version is compatible with scheduler version
        self.client.get_versions(check=True)
        #dask.config.set({"distributed.deploy.lost-worker-timeout": 60, "distributed.workers.memory.spill":0.97, "distributed.workers.memory.target":0.95, "distributed.workers.memory.terminate":0.99 })
        self.workers =  list(self.client.scheduler_info()["workers"].keys())
        while (len(self.workers)!= Sworker):
            self.workers = list(self.client.scheduler_info()["workers"].keys())
        Variable("workers").set(self.workers)
        print(self.workers, flush=True)

    def get_client(self):
        return self.client

    def create_array(self, name, shape, chunksize, dtype, timedim):
        chunks_in_each_dim = [shape[i]//chunksize[i] for i in range(len(shape))]
        l = list(itertools.product(*[range(i) for i in chunks_in_each_dim]))
        items = []
        for m in l:
            f=Future(key=("deisa-"+name,m), inform=True, deisa=True)
            d = da.from_delayed(dask.delayed(f), shape=chunksize, dtype=dtype)
            items.append([list(m),d])
        ll = self.array_sort(items)
        arrays = da.block(ll)
        return arrays

    def create_array_list(self, name, shape, chunksize, dtype, timedim): # list arrays, one for each time step.
        chunks_in_each_dim = [shape[i]//chunksize[i] for i in range(len(shape))]
        l = list(itertools.product(*[range(i) for i in chunks_in_each_dim]))
        items = []
        for m in l:
            f=Future(key=("deisa-"+name,m), inform=True, deisa=True)
            d = da.from_delayed(dask.delayed(f), shape=chunksize, dtype=dtype)
            items.append([list(m),d])
        ll = self.array_sort(items)
        for i in ll:
            arrays.append(da.block(i))
        return arrays

    def array_sort(self, ListDs):
        if len(ListDs[0][0]) == 0:
            return ListDs[0][1]
        else:
            dico = dict()
            for e in ListDs:
                dico.setdefault(e[0][0],[]).append([e[0][1:], e[1]])
            return [self.array_sort(dico[k]) for k in sorted(dico.keys())]

    def get_dask_arrays(self, as_list=False): #TODO test
        arrays = dict()
        self.arrays_desc = Queue("Arrays").get()
        for name in self.arrays_desc:
            if not as_list:
                arrays[name] = self.create_array(name,self.arrays_desc[name]["sizes"], self.arrays_desc[name]["subsizes"], self.arrays_desc[name]["dtype"], self.arrays_desc[name]["timedim"])
            else:
                arrays[name] = self.create_array_list(name,self.arrays_desc[name]["sizes"], self.arrays_desc[name]["subsizes"], self.arrays_desc[name]["dtype"], self.arrays_desc[name]["timedim"])
        return arrays

    def get_deisa_arrays(self):
        arrays = dict()
        self.arrays_desc = Queue("Arrays").get()
        for name in self.arrays_desc:
            arrays[name] = self.create_array(name,self.arrays_desc[name]["sizes"], self.arrays_desc[name]["subsizes"], self.arrays_desc[name]["dtype"], self.arrays_desc[name]["timedim"])
        return deisa_arrays(arrays)
