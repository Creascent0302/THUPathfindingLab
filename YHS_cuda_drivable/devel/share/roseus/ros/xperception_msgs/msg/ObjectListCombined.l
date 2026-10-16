;; Auto-generated. Do not edit!


(when (boundp 'xperception_msgs::ObjectListCombined)
  (if (not (find-package "XPERCEPTION_MSGS"))
    (make-package "XPERCEPTION_MSGS"))
  (shadow 'ObjectListCombined (find-package "XPERCEPTION_MSGS")))
(unless (find-package "XPERCEPTION_MSGS::OBJECTLISTCOMBINED")
  (make-package "XPERCEPTION_MSGS::OBJECTLISTCOMBINED"))

(in-package "ROS")
;;//! \htmlinclude ObjectListCombined.msg.html


(defclass xperception_msgs::ObjectListCombined
  :super ros::object
  :slots (_timestamp _edge_cloud_id _object_list_combined ))

(defmethod xperception_msgs::ObjectListCombined
  (:init
   (&key
    ((:timestamp __timestamp) 0.0)
    ((:edge_cloud_id __edge_cloud_id) 0)
    ((:object_list_combined __object_list_combined) ())
    )
   (send-super :init)
   (setq _timestamp (float __timestamp))
   (setq _edge_cloud_id (round __edge_cloud_id))
   (setq _object_list_combined __object_list_combined)
   self)
  (:timestamp
   (&optional __timestamp)
   (if __timestamp (setq _timestamp __timestamp)) _timestamp)
  (:edge_cloud_id
   (&optional __edge_cloud_id)
   (if __edge_cloud_id (setq _edge_cloud_id __edge_cloud_id)) _edge_cloud_id)
  (:object_list_combined
   (&rest __object_list_combined)
   (if (keywordp (car __object_list_combined))
       (send* _object_list_combined __object_list_combined)
     (progn
       (if __object_list_combined (setq _object_list_combined (car __object_list_combined)))
       _object_list_combined)))
  (:serialization-length
   ()
   (+
    ;; float64 _timestamp
    8
    ;; int32 _edge_cloud_id
    4
    ;; xperception_msgs/ObjectList[] _object_list_combined
    (apply #'+ (send-all _object_list_combined :serialization-length)) 4
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; float64 _timestamp
       (sys::poke _timestamp (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; int32 _edge_cloud_id
       (write-long _edge_cloud_id s)
     ;; xperception_msgs/ObjectList[] _object_list_combined
     (write-long (length _object_list_combined) s)
     (dolist (elem _object_list_combined)
       (send elem :serialize s)
       )
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; float64 _timestamp
     (setq _timestamp (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; int32 _edge_cloud_id
     (setq _edge_cloud_id (sys::peek buf ptr- :integer)) (incf ptr- 4)
   ;; xperception_msgs/ObjectList[] _object_list_combined
   (let (n)
     (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4)
     (setq _object_list_combined (let (r) (dotimes (i n) (push (instance xperception_msgs::ObjectList :init) r)) r))
     (dolist (elem- _object_list_combined)
     (send elem- :deserialize buf ptr-) (incf ptr- (send elem- :serialization-length))
     ))
   ;;
   self)
  )

(setf (get xperception_msgs::ObjectListCombined :md5sum-) "ed983b95b6bbd77ef3f9fc7491a344ae")
(setf (get xperception_msgs::ObjectListCombined :datatype-) "xperception_msgs/ObjectListCombined")
(setf (get xperception_msgs::ObjectListCombined :definition-)
      "
float64 timestamp
int32 edge_cloud_id
ObjectList[] object_list_combined
================================================================================
MSG: xperception_msgs/ObjectList

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



(provide :xperception_msgs/ObjectListCombined "ed983b95b6bbd77ef3f9fc7491a344ae")


