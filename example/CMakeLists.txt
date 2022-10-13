cmake_minimum_required(VERSION 3.9)
project(Coupling LANGUAGES C CXX)

find_package(MPI REQUIRED COMPONENTS C)
find_package(paraconf REQUIRED COMPONENTS C)
find_package(PDI 1.4 REQUIRED COMPONENTS C)
find_package(OpenMP COMPONENTS C)

add_executable(simulation simulation.c)
target_link_libraries(simulation m MPI::MPI_C paraconf::paraconf PDI::pdi)
target_compile_features(simulation PRIVATE c_std_99)
if ("${OpenMP_C_FOUND}")
  target_link_libraries(simulation OpenMP::OpenMP_C)
endif ()
