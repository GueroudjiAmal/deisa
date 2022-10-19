#=============================================================================
# Copyright (c) 2020-2022 Centre national de la recherche scientifique (CNRS)
# Copyright (c) 2020-2022 Commissariat a l'énergie atomique et aux énergies alternatives (CEA)
# Copyright (c) 2020-2022 Institut national de recherche en informatique et en automatique (Inria)
# Copyright (c) 2020-2022 Université Paris-Saclay
# Copyright (c) 2020-2022 Université de Versailles Saint-Quentin-en-Yvelines
#
# SPDX-License-Identifier: MIT
#=============================================================================

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
