;; Auto-generated. Do not edit!


(when (boundp 'perception_ros_msg::EndPoints)
  (if (not (find-package "PERCEPTION_ROS_MSG"))
    (make-package "PERCEPTION_ROS_MSG"))
  (shadow 'EndPoints (find-package "PERCEPTION_ROS_MSG")))
(unless (find-package "PERCEPTION_ROS_MSG::ENDPOINTS")
  (make-package "PERCEPTION_ROS_MSG::ENDPOINTS"))

(in-package "ROS")
;;//! \htmlinclude EndPoints.msg.html


(defclass perception_ros_msg::EndPoints
  :super ros::object
  :slots (_start _end ))

(defmethod perception_ros_msg::EndPoints
  (:init
   (&key
    ((:start __start) (instance perception_ros_msg::Point2f :init))
    ((:end __end) (instance perception_ros_msg::Point2f :init))
    )
   (send-super :init)
   (setq _start __start)
   (setq _end __end)
   self)
  (:start
   (&rest __start)
   (if (keywordp (car __start))
       (send* _start __start)
     (progn
       (if __start (setq _start (car __start)))
       _start)))
  (:end
   (&rest __end)
   (if (keywordp (car __end))
       (send* _end __end)
     (progn
       (if __end (setq _end (car __end)))
       _end)))
  (:serialization-length
   ()
   (+
    ;; perception_ros_msg/Point2f _start
    (send _start :serialization-length)
    ;; perception_ros_msg/Point2f _end
    (send _end :serialization-length)
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; perception_ros_msg/Point2f _start
       (send _start :serialize s)
     ;; perception_ros_msg/Point2f _end
       (send _end :serialize s)
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; perception_ros_msg/Point2f _start
     (send _start :deserialize buf ptr-) (incf ptr- (send _start :serialization-length))
   ;; perception_ros_msg/Point2f _end
     (send _end :deserialize buf ptr-) (incf ptr- (send _end :serialization-length))
   ;;
   self)
  )

(setf (get perception_ros_msg::EndPoints :md5sum-) "8837e560fc11e0ded6ca2f9a297edb61")
(setf (get perception_ros_msg::EndPoints :datatype-) "perception_ros_msg/EndPoints")
(setf (get perception_ros_msg::EndPoints :definition-)
      "Point2f start 
Point2f end 

================================================================================
MSG: perception_ros_msg/Point2f
std_msgs/Float32 x 
std_msgs/Float32 y 

================================================================================
MSG: std_msgs/Float32
float32 data
")



(provide :perception_ros_msg/EndPoints "8837e560fc11e0ded6ca2f9a297edb61")


