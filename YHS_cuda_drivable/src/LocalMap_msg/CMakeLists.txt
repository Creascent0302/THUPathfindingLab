cmake_minimum_required(VERSION 3.16.3)
project(LocalMap_msgs)
find_package(catkin REQUIRED COMPONENTS
    roscpp
    rospy
    message_generation
    std_msgs
)
add_message_files(DIRECTORY msg FILES
    LocalMap_Element.msg
    LocalMap.msg
  )
generate_messages(DEPENDENCIES
    std_msgs
  )
catkin_package(CATKIN_DEPENDS 
    std_msgs message_runtime
)