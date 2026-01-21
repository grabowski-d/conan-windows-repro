cmake_minimum_required(VERSION 3.15)
project(mypkg CXX)

# Minimal CMakeLists.txt for Conan testing
# This file is required by cmake_layout() but we skip actual build

message(STATUS "CMake configuration for environment testing only")
message(STATUS "No actual build will be performed")

# Dummy target to satisfy Conan
add_library(${PROJECT_NAME} INTERFACE)

install(TARGETS ${PROJECT_NAME})
