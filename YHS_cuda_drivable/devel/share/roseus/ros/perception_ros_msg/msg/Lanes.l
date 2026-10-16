;; Auto-generated. Do not edit!


(when (boundp 'perception_ros_msg::Lanes)
  (if (not (find-package "PERCEPTION_ROS_MSG"))
    (make-package "PERCEPTION_ROS_MSG"))
  (shadow 'Lanes (find-package "PERCEPTION_ROS_MSG")))
(unless (find-package "PERCEPTION_ROS_MSG::LANES")
  (make-package "PERCEPTION_ROS_MSG::LANES"))

(in-package "ROS")
;;//! \htmlinclude Lanes.msg.html


(defclass perception_ros_msg::Lanes
  :super ros::object
  :slots (_lanes ))

(defmethod perception_ros_msg::Lanes
  (:init
   (&key
    ((:lanes __lanes) ())
    )
   (send-super :init)
   (setq _lanes __lanes)
   self)
  (:lanes
   (&rest __lanes)
   (if (keywordp (car __lanes))
       (send* _lanes __lanes)
     (progn
       (if __lanes (setq _lanes (car __lanes)))
       _lanes)))
  (:serialization-length
   ()
   (+
    ;; perception_ros_msg/Lane[] _lanes
    (apply #'+ (send-all _lanes :serialization-length)) 4
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; perception_ros_msg/Lane[] _lanes
     (write-long (length _lanes) s)
     (dolist (elem _lanes)
       (send elem :serialize s)
       )
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; perception_ros_msg/Lane[] _lanes
   (let (n)
     (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4)
     (setq _lanes (let (r) (dotimes (i n) (push (instance perception_ros_msg::Lane :init) r)) r))
     (dolist (elem- _lanes)
     (send elem- :deserialize buf ptr-) (incf ptr- (send elem- :serialization-length))
     ))
   ;;
   self)
  )

(setf (get perception_ros_msg::Lanes :md5sum-) "8c91e3b4d885a65b5ff2c91de75a06a9")
(setf (get perception_ros_msg::Lanes :datatype-) "perception_ros_msg/Lanes")
(setf (get perception_ros_msg::Lanes :definition-)
      "Lane[] lanes
================================================================================
MSG: perception_ros_msg/Lane
std_msgs/Int32   lane_id 
Curve            curve 
EndPoints        end_points 
std_msgs/Int32   measure_status  
std_msgs/Float32 confidence 

================================================================================
MSG: std_msgs/Int32
int32 data
================================================================================
MSG: perception_ros_msg/Curve
std_msgs/Float32 x_start 
std_msgs/Float32 x_end 
std_msgs/Float32 a 
std_msgs/Float32 b 
std_msgs/Float32 c 
std_msgs/Float32 d 
================================================================================
MSG: std_msgs/Float32
float32 data
================================================================================
MSG: perception_ros_msg/EndPoints
Point2f start 
Point2f end 

================================================================================
MSG: perception_ros_msg/Point2f
std_msgs/Float32 x 
std_msgs/Float32 y 

")



(provide :perception_ros_msg/Lanes "8c91e3b4d885a65b5ff2c91de75a06a9")


