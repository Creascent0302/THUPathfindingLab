;; Auto-generated. Do not edit!


(when (boundp 'xperception_msgs::ObjectList)
  (if (not (find-package "XPERCEPTION_MSGS"))
    (make-package "XPERCEPTION_MSGS"))
  (shadow 'ObjectList (find-package "XPERCEPTION_MSGS")))
(unless (find-package "XPERCEPTION_MSGS::OBJECTLIST")
  (make-package "XPERCEPTION_MSGS::OBJECTLIST"))

(in-package "ROS")
;;//! \htmlinclude ObjectList.msg.html


(defclass xperception_msgs::ObjectList
  :super ros::object
  :slots (_timestamp _sensor_info _object_list ))

(defmethod xperception_msgs::ObjectList
  (:init
   (&key
    ((:timestamp __timestamp) 0.0)
    ((:sensor_info __sensor_info) ())
    ((:object_list __object_list) ())
    )
   (send-super :init)
   (setq _timestamp (float __timestamp))
   (setq _sensor_info __sensor_info)
   (setq _object_list __object_list)
   self)
  (:timestamp
   (&optional __timestamp)
   (if __timestamp (setq _timestamp __timestamp)) _timestamp)
  (:sensor_info
   (&rest __sensor_info)
   (if (keywordp (car __sensor_info))
       (send* _sensor_info __sensor_info)
     (progn
       (if __sensor_info (setq _sensor_info (car __sensor_info)))
       _sensor_info)))
  (:object_list
   (&rest __object_list)
   (if (keywordp (car __object_list))
       (send* _object_list __object_list)
     (progn
       (if __object_list (setq _object_list (car __object_list)))
       _object_list)))
  (:serialization-length
   ()
   (+
    ;; float64 _timestamp
    8
    ;; xperception_msgs/Object[] _sensor_info
    (apply #'+ (send-all _sensor_info :serialization-length)) 4
    ;; xperception_msgs/Object[] _object_list
    (apply #'+ (send-all _object_list :serialization-length)) 4
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; float64 _timestamp
       (sys::poke _timestamp (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; xperception_msgs/Object[] _sensor_info
     (write-long (length _sensor_info) s)
     (dolist (elem _sensor_info)
       (send elem :serialize s)
       )
     ;; xperception_msgs/Object[] _object_list
     (write-long (length _object_list) s)
     (dolist (elem _object_list)
       (send elem :serialize s)
       )
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; float64 _timestamp
     (setq _timestamp (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; xperception_msgs/Object[] _sensor_info
   (let (n)
     (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4)
     (setq _sensor_info (let (r) (dotimes (i n) (push (instance xperception_msgs::Object :init) r)) r))
     (dolist (elem- _sensor_info)
     (send elem- :deserialize buf ptr-) (incf ptr- (send elem- :serialization-length))
     ))
   ;; xperception_msgs/Object[] _object_list
   (let (n)
     (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4)
     (setq _object_list (let (r) (dotimes (i n) (push (instance xperception_msgs::Object :init) r)) r))
     (dolist (elem- _object_list)
     (send elem- :deserialize buf ptr-) (incf ptr- (send elem- :serialization-length))
     ))
   ;;
   self)
  )

(setf (get xperception_msgs::ObjectList :md5sum-) "1412027a16f3faa1ede2a385fdedbb80")
(setf (get xperception_msgs::ObjectList :datatype-) "xperception_msgs/ObjectList")
(setf (get xperception_msgs::ObjectList :definition-)
      "
float64     timestamp
Object[]    sensor_info
Object[]    object_list
================================================================================
MSG: xperception_msgs/Object

float64 	timestamp
int32 		id 
int16 		type
float64 	size_x
float64 	size_y
float64 	size_z

float64 	heading
float64 	speed

float64 	x 
float64 	y
float64 	z

float64 	longitude
float64 	latitude

float64     confidence
## ground truth
int16       type_gt
float64     size_x_gt
float64     size_y_gt
float64     size_z_gt
float64     heading_gt
float64     speed_gt
float64     x_gt
float64     y_gt
float64     z_gt

")



(provide :xperception_msgs/ObjectList "1412027a16f3faa1ede2a385fdedbb80")


