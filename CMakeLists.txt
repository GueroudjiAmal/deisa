cmake_minimum_required(VERSION 3.9)
project(dask_coupling LANGUAGES C)

find_package(MPI REQUIRED COMPONENTS C)
find_package(paraconf REQUIRED COMPONENTS C)
find_package(PDI 1.2.0 REQUIRED COMPONENTS C)
find_package(OpenMP)
set(CMAKE_C_STANDARD 99)

add_executable(simulation simulation.c)
target_link_libraries(simulation m MPI::MPI_C OpenMP::OpenMP_C  paraconf::paraconf PDI::pdi)

