cmake_minimum_required(VERSION 3.15)
project(mypkg CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(MSVC)
    add_compile_options(/W4)
else()
    add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Add library
add_library(mypkg STATIC
    src/math.cpp
)

target_include_directories(mypkg PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Install
install(TARGETS mypkg DESTINATION lib)
install(FILES include/math.h DESTINATION include)
