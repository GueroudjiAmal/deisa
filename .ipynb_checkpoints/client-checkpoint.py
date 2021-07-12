import time
from dask_interface import Initialization
from  dask_interface import CoupleDask
import numpy as np
import pandas as pd
import yaml
import dask.array as da
from dask.distributed import performance_report
from dask_ml.decomposition import IncrementalPCA


with open(r'config.yml') as file:
    data = yaml.load(file, Loader=yaml.FullLoader)
    Ssize = data["parallelism"]["height"]*data["parallelism"]["width"]
    generations = data["generations"]
    Sworkers = data["workers"]
    timeStep = 1
C = Initialization(Ssize, Sworkers)
C.client.get_versions(check=True)


# Results 
Results = []

# perf holds different time measurements 
# generation, getdata, get-from-queues, computation 
perf = np.empty([generations//timeStep, 4])
t = time.perf_counter()


with performance_report(filename="dask-report.html"):
    for g in range(0, generations, timeStep):
        tic3 = time.perf_counter()
        tic = time.perf_counter()
        arrays, perf[g//timeStep][2] = C.get_data()
        arrays = da.reshape(arrays, (arrays.shape[1],arrays.shape[2])) 
        toc = time.perf_counter()
        perf[g//timeStep][1] = toc - tic
        tic1 = time.perf_counter()
        pca=IncrementalPCA(n_components=2,copy=False, svd_solver='randomized')
        pca.fit(arrays) 
        Results.append([pca.explained_variance_ , pca.singular_values_])
        arrays=None
        toc1 = time.perf_counter()
        perf[g//timeStep][3] = toc1 - tic1  
        toc3 = time.perf_counter()
        perf[g//timeStep][0] = toc3 - tic3

tp = time.perf_counter()
print("Total time to Dask solution is ", tp-t)

pperf = pd.DataFrame(perf,columns=['generation', 'getdata', 'getdataq', 'computation'])
pdata = pd.DataFrame(Results,columns=[ 'his', 'bins'])

with open("perf.csv", "a") as fperf:
    pperf.to_csv(fperf, encoding='utf-8', index=False)
    
with open("diag.csv", "a") as fdiag:
    pdata.to_csv(fdiag, encoding='utf-8', index=False)
    
C.Finalization()
    