## BEGIN_TUTORIAL
## This CMakeLists.txt file for rviz_plugin_tutorials builds both the
## TeleopPanel tutorial and the ImuDisplay tutorial.
##
## First start with some standard catkin stuff.
cmake_minimum_required(VERSION 2.8.3)
project(perception_ros_msg)

# 设置C++相关配置
add_definitions(-O3)
add_definitions(-std=c++11)
add_compile_options(-W)
add_compile_options(-std=c++11)

## 添加PCL 
find_package(PCL REQUIRED)
include_directories(${PCL_INCLUDE_DIRS})
link_directories(${PCL_LIBRARY_DIRS})
add_definitions(${PCL_DEFINITIONS})

## This setting causes Qt's "MOC" generation to happen automatically.
set(CMAKE_AUTOMOC ON)
## Cmake include current direction 
set(CMAKE_INCLUDE_CURRENT_DIR ON)

# 添加Catkin 
find_package(catkin REQUIRED COMPONENTS 
        rviz
        cv_bridge
        genmsg
        pcl_conversions
        pcl_ros
        roscpp
        rospy
        std_msgs
        geometry_msgs
        sensor_msgs
        message_generation)

add_message_files(
        FILES 
        Point2f.msg
        Point3f.msg
        Point4f.msg 
        Point3d.msg 
        Matrix3f.msg
        Indices.msg  
        EndPoints.msg 
        Curve.msg
        CoreInfo.msg 
        SupplementInfo.msg
        Object.msg 
        Objects.msg 
        FreeSpaceInfos.msg 
        Lane.msg 
        Lanes.msg 
        RoadEdge.msg 
        RoadEdges.msg    
        Pose.msg 
        AxisStatusPose.msg 
        PoseMap.msg
        LidarFrameMsg.msg 
        RsPerceptionMsg.msg 
)

generate_messages(
        DEPENDENCIES
        std_msgs
        geometry_msgs
        sensor_msgs 
)

catkin_package()

include_directories(${catkin_INCLUDE_DIRS})
link_directories(${catkin_LIBRARY_DIRS})




