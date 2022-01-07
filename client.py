import time
from dask_interface import Initialization
from  dask_interface import Adaptor
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

Adaptor = Initialization(Ssize, Sworkers)
Adaptor.client.get_versions(check=True)

# Results 
Results = []

with performance_report(filename="dask-report.html"):
    for g in range(0, generations, timeStep):
        arrays = C.get_data()
        arrays = da.reshape(arrays, (arrays.shape[1],arrays.shape[2])) 
        pca=IncrementalPCA(n_components=2,copy=False, svd_solver='randomized')
        pca.fit(arrays) 
        print(pca.explained_variance_ , pca.singular_values_)
        del arrays
  
Adaptor.Finalization()
    
