import sys
import dask
import numpy as np
import pandas as pd
import dask.array as da
from dask.distributed import Client, Event, get_client, comm, Queue, Future, Variable
import time
import asyncio
import json

class metadata:
    index = list()
    data = ""
    shap = None
    typ = ""
    def __init__(self, name):
        self.name = name 
        
class Bridge:
    adr = ""
    queue = None 
    workers = []
    client = None
    def __init__(self, Ssize, rank, pos, gmax):
        with open('scheduler.json') as f:
            s = json.load(f)
        self.adr = s["address"]
        self.client  = get_client(self.adr)
        self.rank = rank.item()
        self.position = pos
        listw = Variable("workers").get()
        if Ssize > len(listw): #more processes than workers 
            self.workers = [listw[int(rank.item())%len(listw)]]
        else:
            k = len(listw)//Ssize # more workers than processes 
            self.workers = listw[rank.item()*k:rank.item()*k+ k]
            
        self.queue = Queue(name = "queue"+str(rank.item()), maxsize = gmax.item())
        
   
    def publish_data(self, g, data) :
        name = "dns" + str(self.rank) + "g" + str(g)
        index = self.position.tolist()
        index.append(g.item())
        ds = metadata(name)
        ds.data = None
        ds.index = index
        ds.shap = data.shape
        ds.typ = str(data.dtype) 
        self.queue.put(dict(ds.__dict__.items()))      
        d_future = self.client.scatter(data, direct = True, workers=self.workers)
        toc = time.perf_counter()
        self.queue.put( d_future) 
   
    def Finalize(self):
        self.queue.put(1)
    
def Init(Ssize, rank, pos, gmax):
    return Bridge(Ssize,rank, pos, gmax)
   

class Adaptor:
    adr = ""
    client = None
    workers = []
    queues = []
    def __init__(self, Ssize, Sworker):
        with open('scheduler.json') as f:
            s = json.load(f)
        self.adr = s["address"]
        self.client  = get_client(self.adr)
        self.workers = [comm.get_address_host_port(i,strict=False) for i in self.client.scheduler_info()["workers"].keys()]
        while (len(self.workers)!= Sworker):
            self.workers = [comm.get_address_host_port(i,strict=False) for i in self.client.scheduler_info()["workers"].keys()]
            
        Variable("workers").set(self.workers)
        self.queues = [Queue("queue"+str(i)) for i in range(Ssize)]
        self.Ssize = Ssize
        
    def get_data(self):
        items = []
        l = self.client.sync(self.getAll, self.queues)
        for m in l:
            m[0]["data"] =  da.from_delayed(dask.delayed(m[1]), m[0]["shap"], dtype=m[0]["typ"])
            items.append(m[0])
        l = self.array_sort(items)
        return da.block(l)
    
    async def getAll(self, queues):
        res = []
        for q in queues:
            res.append( q._get(batch=2))
        return await asyncio.gather(*res)

    def array_sort(self, ListDs):
        if len(ListDs[0]["index"]) == 0:
            return ListDs[0]["data"]
        else:
            dico = dict()
            for e in ListDs:
                dico.setdefault(e["index"][-1],[]).append({"data": e["data"], "index": e["index"][:-1]})
            return [self.array_sort(dico[k]) for k in sorted(dico.keys())]
        
    def Finalization(self):
        for q in self.queues:
            q.get()
        self.client.shutdown()

def Initialization(Ssize, Sworker):
    return Adaptor(Ssize, Sworker)


    
