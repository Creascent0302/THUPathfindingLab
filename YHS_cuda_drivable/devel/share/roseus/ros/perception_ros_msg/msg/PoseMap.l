;; Auto-generated. Do not edit!


(when (boundp 'perception_ros_msg::PoseMap)
  (if (not (find-package "PERCEPTION_ROS_MSG"))
    (make-package "PERCEPTION_ROS_MSG"))
  (shadow 'PoseMap (find-package "PERCEPTION_ROS_MSG")))
(unless (find-package "PERCEPTION_ROS_MSG::POSEMAP")
  (make-package "PERCEPTION_ROS_MSG::POSEMAP"))

(in-package "ROS")
;;//! \htmlinclude PoseMap.msg.html


(defclass perception_ros_msg::PoseMap
  :super ros::object
  :slots (_status_poses ))

(defmethod perception_ros_msg::PoseMap
  (:init
   (&key
    ((:status_poses __status_poses) ())
    )
   (send-super :init)
   (setq _status_poses __status_poses)
   self)
  (:status_poses
   (&rest __status_poses)
   (if (keywordp (car __status_poses))
       (send* _status_poses __status_poses)
     (progn
       (if __status_poses (setq _status_poses (car __status_poses)))
       _status_poses)))
  (:serialization-length
   ()
   (+
    ;; perception_ros_msg/AxisStatusPose[] _status_poses
    (apply #'+ (send-all _status_poses :serialization-length)) 4
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; perception_ros_msg/AxisStatusPose[] _status_poses
     (write-long (length _status_poses) s)
     (dolist (elem _status_poses)
       (send elem :serialize s)
       )
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; perception_ros_msg/AxisStatusPose[] _status_poses
   (let (n)
     (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4)
     (setq _status_poses (let (r) (dotimes (i n) (push (instance perception_ros_msg::AxisStatusPose :init) r)) r))
     (dolist (elem- _status_poses)
     (send elem- :deserialize buf ptr-) (incf ptr- (send elem- :serialization-length))
     ))
   ;;
   self)
  )

(setf (get perception_ros_msg::PoseMap :md5sum-) "51fc7df0ce0cb8096f687175e8cb1f26")
(setf (get perception_ros_msg::PoseMap :datatype-) "perception_ros_msg/PoseMap")
(setf (get perception_ros_msg::PoseMap :definition-)
      "AxisStatusPose[] status_poses 

================================================================================
MSG: perception_ros_msg/AxisStatusPose
std_msgs/Int32 status 
Pose           pose 
================================================================================
MSG: std_msgs/Int32
int32 data
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
")



(provide :perception_ros_msg/PoseMap "51fc7df0ce0cb8096f687175e8cb1f26")


