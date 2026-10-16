;; Auto-generated. Do not edit!


(when (boundp 'perception_ros_msg::FreeSpaceInfos)
  (if (not (find-package "PERCEPTION_ROS_MSG"))
    (make-package "PERCEPTION_ROS_MSG"))
  (shadow 'FreeSpaceInfos (find-package "PERCEPTION_ROS_MSG")))
(unless (find-package "PERCEPTION_ROS_MSG::FREESPACEINFOS")
  (make-package "PERCEPTION_ROS_MSG::FREESPACEINFOS"))

(in-package "ROS")
;;//! \htmlinclude FreeSpaceInfos.msg.html
(if (not (find-package "STD_MSGS"))
  (ros::roseus-add-msgs "std_msgs"))


(defclass perception_ros_msg::FreeSpaceInfos
  :super ros::object
  :slots (_fs_pts _fs_confidence ))

(defmethod perception_ros_msg::FreeSpaceInfos
  (:init
   (&key
    ((:fs_pts __fs_pts) ())
    ((:fs_confidence __fs_confidence) ())
    )
   (send-super :init)
   (setq _fs_pts __fs_pts)
   (setq _fs_confidence __fs_confidence)
   self)
  (:fs_pts
   (&rest __fs_pts)
   (if (keywordp (car __fs_pts))
       (send* _fs_pts __fs_pts)
     (progn
       (if __fs_pts (setq _fs_pts (car __fs_pts)))
       _fs_pts)))
  (:fs_confidence
   (&rest __fs_confidence)
   (if (keywordp (car __fs_confidence))
       (send* _fs_confidence __fs_confidence)
     (progn
       (if __fs_confidence (setq _fs_confidence (car __fs_confidence)))
       _fs_confidence)))
  (:serialization-length
   ()
   (+
    ;; perception_ros_msg/Point3f[] _fs_pts
    (apply #'+ (send-all _fs_pts :serialization-length)) 4
    ;; std_msgs/Float32[] _fs_confidence
    (apply #'+ (send-all _fs_confidence :serialization-length)) 4
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; perception_ros_msg/Point3f[] _fs_pts
     (write-long (length _fs_pts) s)
     (dolist (elem _fs_pts)
       (send elem :serialize s)
       )
     ;; std_msgs/Float32[] _fs_confidence
     (write-long (length _fs_confidence) s)
     (dolist (elem _fs_confidence)
       (send elem :serialize s)
       )
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; perception_ros_msg/Point3f[] _fs_pts
   (let (n)
     (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4)
     (setq _fs_pts (let (r) (dotimes (i n) (push (instance perception_ros_msg::Point3f :init) r)) r))
     (dolist (elem- _fs_pts)
     (send elem- :deserialize buf ptr-) (incf ptr- (send elem- :serialization-length))
     ))
   ;; std_msgs/Float32[] _fs_confidence
   (let (n)
     (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4)
     (setq _fs_confidence (let (r) (dotimes (i n) (push (instance std_msgs::Float32 :init) r)) r))
     (dolist (elem- _fs_confidence)
     (send elem- :deserialize buf ptr-) (incf ptr- (send elem- :serialization-length))
     ))
   ;;
   self)
  )

(setf (get perception_ros_msg::FreeSpaceInfos :md5sum-) "a60987ee9bd368f8db4ac0adf7d909b0")
(setf (get perception_ros_msg::FreeSpaceInfos :datatype-) "perception_ros_msg/FreeSpaceInfos")
(setf (get perception_ros_msg::FreeSpaceInfos :definition-)
      "Point3f[]        fs_pts
std_msgs/Float32[] fs_confidence 

================================================================================
MSG: perception_ros_msg/Point3f
std_msgs/Float32 x 
std_msgs/Float32 y 
std_msgs/Float32 z 
================================================================================
MSG: std_msgs/Float32
float32 data
")



(provide :perception_ros_msg/FreeSpaceInfos "a60987ee9bd368f8db4ac0adf7d909b0")


