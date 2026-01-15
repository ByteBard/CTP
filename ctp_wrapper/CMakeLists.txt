cmake_minimum_required(VERSION 3.10)
project(ctp_wrapper VERSION 1.0.0 LANGUAGES CXX)

# C++11 标准
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Windows特定设置
if(WIN32)
    add_definitions(-D_CRT_SECURE_NO_WARNINGS)
    add_definitions(-DCTP_WRAPPER_EXPORTS)
endif()

# CTP API 路径 (64位Windows)
set(CTP_API_DIR "${CMAKE_SOURCE_DIR}/../Sim/v6.6.8_T1_20220520_winApi/tradeapi/20220520_tradeapi64_se_windows")

# 头文件目录
include_directories(
    ${CMAKE_SOURCE_DIR}/src
    ${CMAKE_SOURCE_DIR}/include
    ${CTP_API_DIR}
)

# 库文件目录
link_directories(${CTP_API_DIR})

# 源文件
set(SOURCES
    src/ctp_wrapper.cpp
)

# 创建动态库
add_library(ctp_wrapper SHARED ${SOURCES})

# 链接CTP库
target_link_libraries(ctp_wrapper
    thosttraderapi_se
)

# 输出目录
set_target_properties(ctp_wrapper PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/python
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/python
    ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/python
)

# 复制CTP DLL到输出目录
if(WIN32)
    add_custom_command(TARGET ctp_wrapper POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${CTP_API_DIR}/thosttraderapi_se.dll"
            "${CMAKE_SOURCE_DIR}/python/"
        COMMENT "Copying CTP DLL to output directory"
    )
endif()

# 输出编译信息
message(STATUS "CTP API Directory: ${CTP_API_DIR}")
message(STATUS "Output Directory: ${CMAKE_SOURCE_DIR}/python")
