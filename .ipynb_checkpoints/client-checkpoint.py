import yaml
from dask_interface import Initialization
from dask.distributed import performance_report

with open(r'config.yml') as file:
    data = yaml.load(file, Loader=yaml.FullLoader)
    Ssize = data["parallelism"]["height"]*data["parallelism"]["width"]
    generations = data["generations"]
    Sworkers = data["workers"]
    timeStep = 1

Adaptor = Initialization(Ssize, Sworkers)
Adaptor.client.get_versions(check=True)

Results = []

with performance_report(filename="dask-report.html"):
    for g in range(generations):
        arrays = Adaptor.get_data()
        cpt = 0.99*(arrays.mean() + arrays.max())/0.58 + arrays.min() - arrays.mean()
        Results.append(Adaptor.client.compute(cpt).result())
        del arrays
        
print("Mean values per time step", Results) 
Adaptor.Finalization()
    
