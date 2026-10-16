;; Auto-generated. Do not edit!


(when (boundp 'perception_ros_msg::RsPerceptionMsg)
  (if (not (find-package "PERCEPTION_ROS_MSG"))
    (make-package "PERCEPTION_ROS_MSG"))
  (shadow 'RsPerceptionMsg (find-package "PERCEPTION_ROS_MSG")))
(unless (find-package "PERCEPTION_ROS_MSG::RSPERCEPTIONMSG")
  (make-package "PERCEPTION_ROS_MSG::RSPERCEPTIONMSG"))

(in-package "ROS")
;;//! \htmlinclude RsPerceptionMsg.msg.html
(if (not (find-package "STD_MSGS"))
  (ros::roseus-add-msgs "std_msgs"))


(defclass perception_ros_msg::RsPerceptionMsg
  :super ros::object
  :slots (_lidarframe _device_id ))

(defmethod perception_ros_msg::RsPerceptionMsg
  (:init
   (&key
    ((:lidarframe __lidarframe) (instance perception_ros_msg::LidarFrameMsg :init))
    ((:device_id __device_id) (instance std_msgs::Int32 :init))
    )
   (send-super :init)
   (setq _lidarframe __lidarframe)
   (setq _device_id __device_id)
   self)
  (:lidarframe
   (&rest __lidarframe)
   (if (keywordp (car __lidarframe))
       (send* _lidarframe __lidarframe)
     (progn
       (if __lidarframe (setq _lidarframe (car __lidarframe)))
       _lidarframe)))
  (:device_id
   (&rest __device_id)
   (if (keywordp (car __device_id))
       (send* _device_id __device_id)
     (progn
       (if __device_id (setq _device_id (car __device_id)))
       _device_id)))
  (:serialization-length
   ()
   (+
    ;; perception_ros_msg/LidarFrameMsg _lidarframe
    (send _lidarframe :serialization-length)
    ;; std_msgs/Int32 _device_id
    (send _device_id :serialization-length)
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; perception_ros_msg/LidarFrameMsg _lidarframe
       (send _lidarframe :serialize s)
     ;; std_msgs/Int32 _device_id
       (send _device_id :serialize s)
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; perception_ros_msg/LidarFrameMsg _lidarframe
     (send _lidarframe :deserialize buf ptr-) (incf ptr- (send _lidarframe :serialization-length))
   ;; std_msgs/Int32 _device_id
     (send _device_id :deserialize buf ptr-) (incf ptr- (send _device_id :serialization-length))
   ;;
   self)
  )

(setf (get perception_ros_msg::RsPerceptionMsg :md5sum-) "6ed114efee5ecd5e94f0dbd1aa700b6d")
(setf (get perception_ros_msg::RsPerceptionMsg :datatype-) "perception_ros_msg/RsPerceptionMsg")
(setf (get perception_ros_msg::RsPerceptionMsg :definition-)
      "# Field Of LidarFrameMsg 
LidarFrameMsg           lidarframe 
std_msgs/Int32          device_id  
================================================================================
MSG: perception_ros_msg/LidarFrameMsg


std_msgs/String frame_id
std_msgs/Float64 timestamp 
Pose             global_pose 
Point3d          gps_origin 
PoseMap          status_pose_map 
std_msgs/Int32   status 
Indices          valid_indices 
Objects          objects 

std_msgs/Bool  has_pointcloud 
Point4f[]      scan_pointcloud 

std_msgs/Bool  has_attention_objects 
Objects        attention_objects 

std_msgs/Bool  has_freespace 
FreeSpaceInfos freespace_infos 

std_msgs/Bool   has_lanes 
Lanes           lanes 

std_msgs/Bool   has_roadedges 
RoadEdges       roadedges 

std_msgs/Bool   has_sematice_indices 
Indices         non_ground_indices
Indices         ground_indices 
Indices         background_indices 

================================================================================
MSG: std_msgs/String
string data

================================================================================
MSG: std_msgs/Float64
float64 data
================================================================================
MSG: perception_ros_msg/Pose
std_msgs/Float32 x 
std_msgs/Float32 y 
std_msgs/Float32 z 

std_msgs/Float32 roll 
std_msgs/Float32 pitch
std_msgs/Float32 yaw

std_msgs/Int32 status 

================================================================================
MSG: std_msgs/Float32
float32 data
================================================================================
MSG: std_msgs/Int32
int32 data
================================================================================
MSG: perception_ros_msg/Point3d
std_msgs/Float64 x 
std_msgs/Float64 y 
std_msgs/Float64 z 

================================================================================
MSG: perception_ros_msg/PoseMap
AxisStatusPose[] status_poses 

================================================================================
MSG: perception_ros_msg/AxisStatusPose
std_msgs/Int32 status 
Pose           pose 
================================================================================
MSG: perception_ros_msg/Indices
std_msgs/Int32[]    indices
================================================================================
MSG: perception_ros_msg/Objects
Object[]         objects
================================================================================
MSG: perception_ros_msg/Object
CoreInfo coreinfo
std_msgs/Bool  hassupplmentinfo 
SupplementInfo supplementinfo 

================================================================================
MSG: perception_ros_msg/CoreInfo
std_msgs/Float64 timestamp

std_msgs/Int32 priority_id
std_msgs/Float32 exist_confidence 
Point3f          center 
Point3f          center_cov 
Point3f          size 
Point3f          size_cov 
Point3f          direction 
Point3f          direction_cov         
std_msgs/Int32   type 
std_msgs/Float32 type_confidence 
std_msgs/Int32   attention_type 
std_msgs/Int32   motion_state
std_msgs/Int32   lane_pos
std_msgs/Int32   trakcer_id 
std_msgs/Float64 age 
Point3f          velocity 
Point3f          velocity_cov 
Point3f          acceleration 
Point3f          acceleration_cov 
std_msgs/Float32 angle_velocity 
std_msgs/Float32 angle_velocity_cov 
std_msgs/Float32 angle_acceleration 
std_msgs/Float32 angle_acceleration_cov  
Point3f          anchor 
Point3f          nearest_point 


================================================================================
MSG: perception_ros_msg/Point3f
std_msgs/Float32 x 
std_msgs/Float32 y 
std_msgs/Float32 z 
================================================================================
MSG: std_msgs/Bool
bool data
================================================================================
MSG: perception_ros_msg/SupplementInfo
std_msgs/UInt32     unique_id

Point3f[]           polygon
std_msgs/Int32      left_point_index 
std_msgs/Int32      right_point_index 

std_msgs/Int32[]    cloud_indices

std_msgs/Float32[]  latent_types
std_msgs/Int32      size_type 
std_msgs/Int32      mode 
std_msgs/Bool       in_roi 
std_msgs/Int32      tracking_state
Point3f             geo_center 
Point3f             geo_size 



Point3f[]           trajectory 
Point3f[]           history_velocity
std_msgs/Int32[]    history_type 
std_msgs/Int32      gps_mode 
Point3d             gps_info 

================================================================================
MSG: std_msgs/UInt32
uint32 data
================================================================================
MSG: perception_ros_msg/Point4f
std_msgs/Float32 x 
std_msgs/Float32 y 
std_msgs/Float32 z 
std_msgs/Float32 i 

================================================================================
MSG: perception_ros_msg/FreeSpaceInfos
Point3f[]        fs_pts
std_msgs/Float32[] fs_confidence 

================================================================================
MSG: perception_ros_msg/Lanes
Lane[] lanes
================================================================================
MSG: perception_ros_msg/Lane
std_msgs/Int32   lane_id 
Curve            curve 
EndPoints        end_points 
std_msgs/Int32   measure_status  
std_msgs/Float32 confidence 

================================================================================
MSG: perception_ros_msg/Curve
std_msgs/Float32 x_start 
std_msgs/Float32 x_end 
std_msgs/Float32 a 
std_msgs/Float32 b 
std_msgs/Float32 c 
std_msgs/Float32 d 
================================================================================
MSG: perception_ros_msg/EndPoints
Point2f start 
Point2f end 

================================================================================
MSG: perception_ros_msg/Point2f
std_msgs/Float32 x 
std_msgs/Float32 y 

================================================================================
MSG: perception_ros_msg/RoadEdges
RoadEdge[] curbs

================================================================================
MSG: perception_ros_msg/RoadEdge
std_msgs/Int32   roadedge_id  
Curve            curve 
EndPoints        end_points 
std_msgs/Int32   measure_status  
std_msgs/Float32 confidence 

")



(provide :perception_ros_msg/RsPerceptionMsg "6ed114efee5ecd5e94f0dbd1aa700b6d")


