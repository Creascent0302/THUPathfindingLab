cmake_minimum_required(VERSION 3.16.3)
project(drivable_area_detection)

# 首先禁用所有位置的 PIC
set(CMAKE_POSITION_INDEPENDENT_CODE OFF)

# 启用 CUDA 支持
enable_language(CUDA)

# 设置 CUDA 标准
set(CMAKE_CUDA_STANDARD 14)
set(CMAKE_CUDA_STANDARD_REQUIRED ON)
set(CMAKE_CUDA_ARCHITECTURES "native")

# 设置构建类型
set(CMAKE_BUILD_TYPE "Release")
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 对于 Debug 构建的选项
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    add_compile_options(-g -O0)
endif()

# 查找 CUDA
find_package(CUDA REQUIRED)

# 其他包的查找
find_package(catkin REQUIRED COMPONENTS
  geometry_msgs
  nav_msgs
  sensor_msgs
  roscpp
  rospy
  rosbag
  std_msgs
  cv_bridge
  filters
  tf
  LocalMap_msgs
  cav_msgs
  perception_ros_msg
  xperception_msgs
  grid_map_core
  grid_map_cv
  grid_map_filters
  grid_map_loader
  grid_map_msgs
  grid_map_octomap
  grid_map_ros
  grid_map_rviz_plugin
  grid_map_sdf
  grid_map_visualization
)

find_package(Eigen3 REQUIRED)
find_package(PCL REQUIRED)
find_package(OpenCV REQUIRED)

# 包含目录
include_directories(
    include
    ${catkin_INCLUDE_DIRS} 
    ${PCL_INCLUDE_DIRS}
    ${Eigen3_INCLUDE_DIRS}
    ${OpenCV_INCLUDE_DIRS}
    ${CUDA_INCLUDE_DIRS}
    src/
)

# 设置 CUDA 编译选项
set(CUDA_NVCC_FLAGS "${CUDA_NVCC_FLAGS} -std=c++14 --expt-relaxed-constexpr")
set(CUDA_PROPAGATE_HOST_FLAGS OFF)

# 创建单独的 CUDA 静态库
cuda_add_library(cuda_kernels STATIC src/cuda_kernels.cu)
set_target_properties(cuda_kernels PROPERTIES
    POSITION_INDEPENDENT_CODE OFF
    CUDA_PROPAGATE_HOST_FLAGS OFF
)

# 设置 CUDA 库的包含目录
target_include_directories(cuda_kernels PRIVATE
    include
    ${catkin_INCLUDE_DIRS} 
    ${PCL_INCLUDE_DIRS}
    ${Eigen3_INCLUDE_DIRS}
    ${OpenCV_INCLUDE_DIRS}
    ${CUDA_INCLUDE_DIRS}
    src/
)

catkin_package(
  CATKIN_DEPENDS geometry_msgs nav_msgs roscpp rospy std_msgs
  DEPENDS Eigen3 PCL 
  INCLUDE_DIRS include
)

# 创建主可执行文件（不包含 CUDA 文件）
add_executable(clear_test 
    src/dr_detect.cpp 
    src/drivable_detect.cpp 
    src/CVaRcal.cpp 
    src/CVaRcal_cuda.cpp
)

# 设置主目标的属性
set_target_properties(clear_test PROPERTIES
    POSITION_INDEPENDENT_CODE OFF
)

# 设置主目标的包含目录
target_include_directories(clear_test PRIVATE
    include
    ${catkin_INCLUDE_DIRS} 
    ${PCL_INCLUDE_DIRS}
    ${Eigen3_INCLUDE_DIRS}
    ${OpenCV_INCLUDE_DIRS}
    ${CUDA_INCLUDE_DIRS}
    src/
)

# 链接库
target_link_libraries(clear_test 
    cuda_kernels  # 链接 CUDA 静态库
    ${catkin_LIBRARIES} 
    ${PCL_LIBRARIES} 
    ${OpenCV_LIBS}  
    ${CUDA_LIBRARIES}
)

if(catkin_EXPORTED_TARGETS)
  add_dependencies(clear_test ${catkin_EXPORTED_TARGETS})
endif()

# 确保 CUDA 库先编译
add_dependencies(clear_test cuda_kernels)