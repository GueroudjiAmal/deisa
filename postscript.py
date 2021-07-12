import yaml
import sys
import os
import glob
import pandas as pd
    
extension = 'csv'
all_fileBridges = [i for i in glob.glob('perfBridge*.{}'.format(extension))]
combined_csv = pd.concat([pd.read_csv(f) for f in all_fileBridges ])
combined_csv.to_csv( "perfBridge.csv", index=False, encoding='utf-8-sig')
[os.remove(f) for f in all_fileBridges]
all_fileSEP = [i for i in glob.glob('SimuPDI*.{}'.format(extension))]
combined_csv = pd.concat([pd.read_csv(f) for f in all_fileSEP ])
combined_csv.to_csv( "SimuPDI.csv", index=False, encoding='utf-8-sig')
[os.remove(f) for f in all_fileSEP]