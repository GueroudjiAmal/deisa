#!/bin/bash

## prescript.py  
# sys.argv[1,2] : global_size.height/width
# sys.argv[3,4] : parallelism.height/width
# sys.argv[5] : generation 
# sys.argv[6] : gmax
# sys.argv[7] : nworker
# sys.argv[8] : timeStep

source ~/.bashrc

PYTH='/gpfs/workdir/gueroudjia/.conda/envs/PhDEnv/bin/python'
DIR=$PWD

module purge  
module load cmake/3.16.2/intel-19.0.3.199 gcc/9.2.0/gcc-4.8.5 openmpi/3.1.5/gcc-9.2.0
conda activate PhDEnv

GENERATION=10
TIMESTEP=300
NWORKERPNODE=16

CHUNKH=256
CHUNKW=512

GMAX=1000

RATIOSIMUNWORKERN=4

for RUN in 1 #2 4 
do 
    for VERSION in 16 #4 8 16 32
    do
        mkdir -p $WORKDIR/CLUSTER/DEISAE1/$RUN/$VERSION/
        WORKSPACE=$(mktemp -d -p $WORKDIR/CLUSTER/DEISAE1/$RUN/$VERSION/ deisaXXX)
        cd $WORKSPACE
        cp $DIR/Coupling.sh $DIR/*.py $DIR/simulation.*  $DIR/CMakeLists.txt  $DIR/Script.sh .
        ${HOME}/local/bin/pdirun cmake  -DCMAKE_BUILD_TYPE=Release .
        make -B simulation
        echo Running $WORKSPACE 

        case $VERSION in 

            4)
                PARALLELISM1=8
                PARALLELISM2=16
                PARTITION=cpu_med
                TIME=04:00:00
                                
                ;;
            8)
                PARALLELISM1=16
                PARALLELISM2=16
                PARTITION=cpu_med
                TIME=04:00:00
                ;;
            16)
                PARALLELISM1=16
                PARALLELISM2=32
                PARTITION=cpu_prod
                TIME=06:00:00
                ;;
                
            32)
                PARALLELISM1=32
                PARALLELISM2=32
                PARTITION=cpu_prod
                TIME=06:00:00
                
                ;;

             *)
                echo hum concentre toi un tiii peu ; exit
        esac   
        
        DATASIZE1=$(($PARALLELISM1 * $CHUNKH))
        DATASIZE2=$(($PARALLELISM2 * $CHUNKW))
        NWORKERNODE=$(($VERSION / $RATIOSIMUNWORKERN))
        NODES=$(($VERSION + $NWORKERNODE + 1))
        NWORKER=$(($NWORKERNODE * $NWORKERPNODE))
        
        $PYTH prescript.py $DATASIZE1 $DATASIZE2 $PARALLELISM1 $PARALLELISM2 $GENERATION $GMAX $NWORKER $TIMESTEP
        sbatch --job-name=dask-cluster --account=dask_coupling --time=$TIME --nodes=$NODES --partition=$PARTITION --exclusive Script.sh 
    done 
done
