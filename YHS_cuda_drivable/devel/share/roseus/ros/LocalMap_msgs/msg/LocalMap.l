;; Auto-generated. Do not edit!


(when (boundp 'LocalMap_msgs::LocalMap)
  (if (not (find-package "LOCALMAP_MSGS"))
    (make-package "LOCALMAP_MSGS"))
  (shadow 'LocalMap (find-package "LOCALMAP_MSGS")))
(unless (find-package "LOCALMAP_MSGS::LOCALMAP")
  (make-package "LOCALMAP_MSGS::LOCALMAP"))

(in-package "ROS")
;;//! \htmlinclude LocalMap.msg.html


(defclass LocalMap_msgs::LocalMap
  :super ros::object
  :slots (_timestamp _box_size_x _box_size_y _boxes_num_x _boxes_num_y _map_cx _map_cy _local_map ))

(defmethod LocalMap_msgs::LocalMap
  (:init
   (&key
    ((:timestamp __timestamp) 0.0)
    ((:box_size_x __box_size_x) 0.0)
    ((:box_size_y __box_size_y) 0.0)
    ((:boxes_num_x __boxes_num_x) 0)
    ((:boxes_num_y __boxes_num_y) 0)
    ((:map_cx __map_cx) 0.0)
    ((:map_cy __map_cy) 0.0)
    ((:local_map __local_map) ())
    )
   (send-super :init)
   (setq _timestamp (float __timestamp))
   (setq _box_size_x (float __box_size_x))
   (setq _box_size_y (float __box_size_y))
   (setq _boxes_num_x (round __boxes_num_x))
   (setq _boxes_num_y (round __boxes_num_y))
   (setq _map_cx (float __map_cx))
   (setq _map_cy (float __map_cy))
   (setq _local_map __local_map)
   self)
  (:timestamp
   (&optional __timestamp)
   (if __timestamp (setq _timestamp __timestamp)) _timestamp)
  (:box_size_x
   (&optional __box_size_x)
   (if __box_size_x (setq _box_size_x __box_size_x)) _box_size_x)
  (:box_size_y
   (&optional __box_size_y)
   (if __box_size_y (setq _box_size_y __box_size_y)) _box_size_y)
  (:boxes_num_x
   (&optional __boxes_num_x)
   (if __boxes_num_x (setq _boxes_num_x __boxes_num_x)) _boxes_num_x)
  (:boxes_num_y
   (&optional __boxes_num_y)
   (if __boxes_num_y (setq _boxes_num_y __boxes_num_y)) _boxes_num_y)
  (:map_cx
   (&optional __map_cx)
   (if __map_cx (setq _map_cx __map_cx)) _map_cx)
  (:map_cy
   (&optional __map_cy)
   (if __map_cy (setq _map_cy __map_cy)) _map_cy)
  (:local_map
   (&rest __local_map)
   (if (keywordp (car __local_map))
       (send* _local_map __local_map)
     (progn
       (if __local_map (setq _local_map (car __local_map)))
       _local_map)))
  (:serialization-length
   ()
   (+
    ;; float64 _timestamp
    8
    ;; float64 _box_size_x
    8
    ;; float64 _box_size_y
    8
    ;; int16 _boxes_num_x
    2
    ;; int16 _boxes_num_y
    2
    ;; float64 _map_cx
    8
    ;; float64 _map_cy
    8
    ;; LocalMap_msgs/LocalMap_Element[] _local_map
    (apply #'+ (send-all _local_map :serialization-length)) 4
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; float64 _timestamp
       (sys::poke _timestamp (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _box_size_x
       (sys::poke _box_size_x (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _box_size_y
       (sys::poke _box_size_y (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; int16 _boxes_num_x
       (write-word _boxes_num_x s)
     ;; int16 _boxes_num_y
       (write-word _boxes_num_y s)
     ;; float64 _map_cx
       (sys::poke _map_cx (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _map_cy
       (sys::poke _map_cy (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; LocalMap_msgs/LocalMap_Element[] _local_map
     (write-long (length _local_map) s)
     (dolist (elem _local_map)
       (send elem :serialize s)
       )
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; float64 _timestamp
     (setq _timestamp (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _box_size_x
     (setq _box_size_x (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _box_size_y
     (setq _box_size_y (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; int16 _boxes_num_x
     (setq _boxes_num_x (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; int16 _boxes_num_y
     (setq _boxes_num_y (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; float64 _map_cx
     (setq _map_cx (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _map_cy
     (setq _map_cy (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; LocalMap_msgs/LocalMap_Element[] _local_map
   (let (n)
     (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4)
     (setq _local_map (let (r) (dotimes (i n) (push (instance LocalMap_msgs::LocalMap_Element :init) r)) r))
     (dolist (elem- _local_map)
     (send elem- :deserialize buf ptr-) (incf ptr- (send elem- :serialization-length))
     ))
   ;;
   self)
  )

(setf (get LocalMap_msgs::LocalMap :md5sum-) "40731d50e6751621f77683a18a42cf49")
(setf (get LocalMap_msgs::LocalMap :datatype-) "LocalMap_msgs/LocalMap")
(setf (get LocalMap_msgs::LocalMap :definition-)
      "
##timestamp, ros time or utc time
float64     timestamp

float64 box_size_x  #size of each box
float64 box_size_y  #size of each box

int16 boxes_num_x   #how many boxes in x
int16 boxes_num_y   #how many boxes in y

float64 map_cx  #ct of the local map
float64 map_cy  #ct of the local map

LocalMap_Element[] local_map
================================================================================
MSG: LocalMap_msgs/LocalMap_Element

int32 x_id    #0,1,2,3,4,... east: +x
int32 y_id    #0,1,2,3,4,... north: +y

bool driveable_index     #0:not  1: driveable
float64 driveable_value    #[0,1] 1:best

float64 ct_x      # x of the center of this box
float64 ct_y      # y of the center of this box
")



(provide :LocalMap_msgs/LocalMap "40731d50e6751621f77683a18a42cf49")


