

cmake_minimum_required(VERSION 2.8.3)
project(cav_msgs)

find_package(catkin REQUIRED COMPONENTS
	roscpp
	rospy
	message_generation
	std_msgs
)
                      

add_message_files( DIRECTORY msg FILES
	Control.msg
	VehicleState.msg
    Gpybm.msg
)
 
generate_messages(DEPENDENCIES
	std_msgs
)

catkin_package(CATKIN_DEPENDS	
	message_runtime
	std_msgs
)

 
  
