#include <mpi.h>
#include <omp.h>
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <pdi.h>

/// size of the local data as [HEIGHT, WIDTH] including ghosts & boundary constants
int dsize[2];

/// 2D size of the process grid as [HEIGHT, WIDTH]
int psize[2];

/// 2D rank of the local process in the process grid as [YY, XX]
int pcoord[2];

/** Initialize the data all to 0 except for the left border (XX==0) initialized to 1 million
 * \param[out] dat the local data to initialize
 */
void init(double dat[dsize[0]][dsize[1]])
{
    for (int yy=0; yy<dsize[0]; ++yy)  for (int xx=0; xx<dsize[1]; ++xx)  dat[yy][xx] = 0;
    if ( pcoord[1] == 0 ) for (int yy=0; yy<dsize[0]; ++yy)  dat[yy][0] = 1000000;
}

/** Compute the values at the next time-step based on the values at the current time-step
 * \param[in]  cur  the local data at the current time-step
 * \param[out] next the local data at the next    time-step
 */
void iter(int dsize[2], double cur[dsize[0]][dsize[1]], double next[dsize[0]][dsize[1]])
{
    for (int xx=0; xx<dsize[1]; ++xx) {
        next[0][xx] = cur[0][xx];
    }
    #pragma omp parallel for
    for (int yy=1; yy<dsize[0]-1; ++yy) {
        next[yy][0] = cur[yy][0];
        for (int xx=1; xx<dsize[1]-1; ++xx) {
            next[yy][xx] =
                (cur[yy][xx]   *.5)
                + (cur[yy][xx-1] *.125)
                + (cur[yy][xx+1] *.125)
                + (cur[yy-1][xx] *.125)
                + (cur[yy+1][xx] *.125);
        }

        next[yy][dsize[1]-1] = cur[yy][dsize[1]-1];
    }

    for (int xx=0; xx<dsize[1]; ++xx) {
        next[dsize[0]-1][xx] = cur[dsize[0]-1][xx];
    }
}

/** Exchanges ghost values with neighbours
 * \param[in] cart_comm the MPI communicator with all processes organized in a 2D Cartesian grid
 * \param[in] cur the local data at the current time-step whose ghosts need exchanging
 */
void exchange(MPI_Comm cart_comm, double cur[dsize[0]][dsize[1]])
{
    MPI_Status status;
    int rank_source, rank_dest;
    static MPI_Datatype column, row;
    static int initialized = 0;

    if ( !initialized ) {
        MPI_Type_vector(dsize[0]-2, 1, dsize[1], MPI_INT, &column);
        MPI_Type_commit(&column);
        MPI_Type_contiguous(dsize[1]-2, MPI_INT, &row);
        MPI_Type_commit(&row);
        initialized = 1;
    }

    // send down
    MPI_Cart_shift(cart_comm, 0, 1, &rank_source, &rank_dest);
    MPI_Sendrecv(&cur[dsize[0]-2][1], 1, row, rank_dest,   100, // send row before ghost
                 &cur[0][1],          1, row, rank_source, 100, // receive 1st row (ghost)
                 cart_comm, &status);

    // send up
    MPI_Cart_shift(cart_comm, 0, -1, &rank_source, &rank_dest);
    MPI_Sendrecv(&cur[1][1],          1, row, rank_dest,   100, // send column after ghost
                 &cur[dsize[0]-1][1], 1, row, rank_source, 100, // receive last column (ghost)
                 cart_comm, &status);

    // send to the right
    MPI_Cart_shift(cart_comm, 1, 1, &rank_source, &rank_dest);
    MPI_Sendrecv(&cur[1][dsize[1]-2], 1, column, rank_dest,   100, // send column before ghost
                 &cur[1][0],          1, column, rank_source, 100, // receive 1st column (ghost)
                 cart_comm, &status);

    // send to the left
    MPI_Cart_shift(cart_comm, 1, -1, &rank_source, &rank_dest);
    MPI_Sendrecv(&cur[1][1], 1, column, rank_dest,   100, // send column after ghost
                 &cur[1][dsize[1]-1], 1, column, rank_source, 100, // receive last column (ghost)
                 cart_comm, &status);
}

int main( int argc, char* argv[] )
{
    MPI_Init(&argc, &argv);

    // load the configuration tree
    PC_tree_t conf = PC_parse_path("config.yml");

    // NEVER USE MPI_COMM_WORLD IN THE CODE, use our own communicator main_comm instead
    MPI_Comm main_comm = MPI_COMM_WORLD;

    // load the MPI rank & size
    int psize_1d;  MPI_Comm_size(main_comm, &psize_1d);
    int pcoord_1d; MPI_Comm_rank(main_comm, &pcoord_1d);

    long longval;

    // load the global data-size
    int global_size[2] ;
    PC_int(PC_get(conf, ".global_size.height"), &longval); global_size[0] = longval;
    PC_int(PC_get(conf, ".global_size.width"), &longval); global_size[1] = longval;

    // load the parallelism configuration
    PC_int(PC_get(conf, ".parallelism.height"), &longval); psize[0] = longval;
    PC_int(PC_get(conf, ".parallelism.width" ), &longval); psize[1] = longval;

    // load the generation configuration
    long generations ;
    PC_int(PC_get(conf, ".MaxtimeSteps" ), &generations);

    conf = PC_parse_path("simulation.yml");
    PDI_init(PC_get(conf, ".pdi"));

    // check the configuration is coherent
    assert(global_size[0]%psize[0]==0);
    assert(global_size[1]%psize[1]==0);
    assert(psize[1]*psize[0] == psize_1d);

    // compute the local data-size with space for ghosts and boundary constants
    dsize[0] = global_size[0]/psize[0] + 2;
    dsize[1] = global_size[1]/psize[1] + 2;

    // create a 2D Cartesian MPI communicator & get our coordinate (rank) in it
    int cart_period[2] = { 0, 0 };
    MPI_Comm cart_comm; MPI_Cart_create(main_comm, 2, psize, cart_period, 1, &cart_comm);
    MPI_Cart_coords(cart_comm, pcoord_1d, 2, pcoord);

    // allocate memory for the int buffered data
    double(*cur)[dsize[1]]  = malloc(sizeof(double)*dsize[1]*dsize[0]);
    double(*next)[dsize[1]] = malloc(sizeof(double)*dsize[1]*dsize[0]);

    // initialize the data content
    init(cur);

    // our loop counter so as to be able to use it outside the loop
    int ii=0;

    // share useful configuration bits with PDI
    PDI_multi_expose("init",
                        "pcoord", pcoord, PDI_OUT,
                        "pcoord_1d", &pcoord_1d, PDI_OUT,
                        "dsize", dsize,  PDI_OUT,
                        "psize", psize, PDI_OUT,
                        "timestep", &ii, PDI_OUT,
                        "MaxtimeSteps", &generations, PDI_OUT,
                         NULL);

    // the main loop
    for (; ii<generations; ++ii) {

        PDI_multi_expose("Available",
                 "timestep",         &ii, PDI_OUT,
                 "local_t", cur, PDI_OUT,
                  NULL);

        for (int jj=0; jj<10; ++jj){
            // compute the values for the next iteration
            iter(dsize, cur, next);

            // exchange data with the neighbours
            exchange(cart_comm, next);

            // swap the current and next values
            double (*tmp)[dsize[1]] = cur; cur = next; next = tmp;

            MPI_Barrier(cart_comm);
        }
    }

    PDI_finalize();

    // destroy the paraconf configuration tree
    PC_tree_destroy(&conf);

    // free the allocated memory
    free(cur);
    free(next);

    // finalize MPI
    MPI_Finalize();

    fprintf(stderr, "[%d] SUCCESS\n", pcoord_1d);
    return EXIT_SUCCESS;
}
