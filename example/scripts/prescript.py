import yaml
import sys
# sys.argv[1] : global_size.height
# sys.argv[2] : global_size.width
# sys.argv[3] : parallelism.height
# sys.argv[4] : parallelism.width
# sys.argv[5] : generation 
# sys.argv[6] : nworkers

with open('config.yml', 'w') as file:
    data = {"global_size":   {"height": int(sys.argv[1]), "width": int(sys.argv[2])},
             "parallelism":  { "height": int(sys.argv[3]), "width": int(sys.argv[4])},
             "MaxtimeSteps": int(sys.argv[5]),
             "workers":   int(sys.argv[6])}
if data:
    with open('config.yml','w') as file:
        yaml.safe_dump(data, file) 
 

