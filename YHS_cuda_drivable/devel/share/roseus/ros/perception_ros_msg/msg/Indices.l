;; Auto-generated. Do not edit!


(when (boundp 'perception_ros_msg::Indices)
  (if (not (find-package "PERCEPTION_ROS_MSG"))
    (make-package "PERCEPTION_ROS_MSG"))
  (shadow 'Indices (find-package "PERCEPTION_ROS_MSG")))
(unless (find-package "PERCEPTION_ROS_MSG::INDICES")
  (make-package "PERCEPTION_ROS_MSG::INDICES"))

(in-package "ROS")
;;//! \htmlinclude Indices.msg.html
(if (not (find-package "STD_MSGS"))
  (ros::roseus-add-msgs "std_msgs"))


(defclass perception_ros_msg::Indices
  :super ros::object
  :slots (_indices ))

(defmethod perception_ros_msg::Indices
  (:init
   (&key
    ((:indices __indices) ())
    )
   (send-super :init)
   (setq _indices __indices)
   self)
  (:indices
   (&rest __indices)
   (if (keywordp (car __indices))
       (send* _indices __indices)
     (progn
       (if __indices (setq _indices (car __indices)))
       _indices)))
  (:serialization-length
   ()
   (+
    ;; std_msgs/Int32[] _indices
    (apply #'+ (send-all _indices :serialization-length)) 4
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; std_msgs/Int32[] _indices
     (write-long (length _indices) s)
     (dolist (elem _indices)
       (send elem :serialize s)
       )
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; std_msgs/Int32[] _indices
   (let (n)
     (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4)
     (setq _indices (let (r) (dotimes (i n) (push (instance std_msgs::Int32 :init) r)) r))
     (dolist (elem- _indices)
     (send elem- :deserialize buf ptr-) (incf ptr- (send elem- :serialization-length))
     ))
   ;;
   self)
  )

(setf (get perception_ros_msg::Indices :md5sum-) "355aaec182bd3a24f494f1ab4a82fd9e")
(setf (get perception_ros_msg::Indices :datatype-) "perception_ros_msg/Indices")
(setf (get perception_ros_msg::Indices :definition-)
      "std_msgs/Int32[]    indices
================================================================================
MSG: std_msgs/Int32
int32 data
")



(provide :perception_ros_msg/Indices "355aaec182bd3a24f494f1ab4a82fd9e")


