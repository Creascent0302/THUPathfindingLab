;; Auto-generated. Do not edit!


(when (boundp 'xperception_msgs::Object)
  (if (not (find-package "XPERCEPTION_MSGS"))
    (make-package "XPERCEPTION_MSGS"))
  (shadow 'Object (find-package "XPERCEPTION_MSGS")))
(unless (find-package "XPERCEPTION_MSGS::OBJECT")
  (make-package "XPERCEPTION_MSGS::OBJECT"))

(in-package "ROS")
;;//! \htmlinclude Object.msg.html


(defclass xperception_msgs::Object
  :super ros::object
  :slots (_timestamp _id _type _size_x _size_y _size_z _heading _speed _x _y _z _longitude _latitude _confidence _type_gt _size_x_gt _size_y_gt _size_z_gt _heading_gt _speed_gt _x_gt _y_gt _z_gt ))

(defmethod xperception_msgs::Object
  (:init
   (&key
    ((:timestamp __timestamp) 0.0)
    ((:id __id) 0)
    ((:type __type) 0)
    ((:size_x __size_x) 0.0)
    ((:size_y __size_y) 0.0)
    ((:size_z __size_z) 0.0)
    ((:heading __heading) 0.0)
    ((:speed __speed) 0.0)
    ((:x __x) 0.0)
    ((:y __y) 0.0)
    ((:z __z) 0.0)
    ((:longitude __longitude) 0.0)
    ((:latitude __latitude) 0.0)
    ((:confidence __confidence) 0.0)
    ((:type_gt __type_gt) 0)
    ((:size_x_gt __size_x_gt) 0.0)
    ((:size_y_gt __size_y_gt) 0.0)
    ((:size_z_gt __size_z_gt) 0.0)
    ((:heading_gt __heading_gt) 0.0)
    ((:speed_gt __speed_gt) 0.0)
    ((:x_gt __x_gt) 0.0)
    ((:y_gt __y_gt) 0.0)
    ((:z_gt __z_gt) 0.0)
    )
   (send-super :init)
   (setq _timestamp (float __timestamp))
   (setq _id (round __id))
   (setq _type (round __type))
   (setq _size_x (float __size_x))
   (setq _size_y (float __size_y))
   (setq _size_z (float __size_z))
   (setq _heading (float __heading))
   (setq _speed (float __speed))
   (setq _x (float __x))
   (setq _y (float __y))
   (setq _z (float __z))
   (setq _longitude (float __longitude))
   (setq _latitude (float __latitude))
   (setq _confidence (float __confidence))
   (setq _type_gt (round __type_gt))
   (setq _size_x_gt (float __size_x_gt))
   (setq _size_y_gt (float __size_y_gt))
   (setq _size_z_gt (float __size_z_gt))
   (setq _heading_gt (float __heading_gt))
   (setq _speed_gt (float __speed_gt))
   (setq _x_gt (float __x_gt))
   (setq _y_gt (float __y_gt))
   (setq _z_gt (float __z_gt))
   self)
  (:timestamp
   (&optional __timestamp)
   (if __timestamp (setq _timestamp __timestamp)) _timestamp)
  (:id
   (&optional __id)
   (if __id (setq _id __id)) _id)
  (:type
   (&optional __type)
   (if __type (setq _type __type)) _type)
  (:size_x
   (&optional __size_x)
   (if __size_x (setq _size_x __size_x)) _size_x)
  (:size_y
   (&optional __size_y)
   (if __size_y (setq _size_y __size_y)) _size_y)
  (:size_z
   (&optional __size_z)
   (if __size_z (setq _size_z __size_z)) _size_z)
  (:heading
   (&optional __heading)
   (if __heading (setq _heading __heading)) _heading)
  (:speed
   (&optional __speed)
   (if __speed (setq _speed __speed)) _speed)
  (:x
   (&optional __x)
   (if __x (setq _x __x)) _x)
  (:y
   (&optional __y)
   (if __y (setq _y __y)) _y)
  (:z
   (&optional __z)
   (if __z (setq _z __z)) _z)
  (:longitude
   (&optional __longitude)
   (if __longitude (setq _longitude __longitude)) _longitude)
  (:latitude
   (&optional __latitude)
   (if __latitude (setq _latitude __latitude)) _latitude)
  (:confidence
   (&optional __confidence)
   (if __confidence (setq _confidence __confidence)) _confidence)
  (:type_gt
   (&optional __type_gt)
   (if __type_gt (setq _type_gt __type_gt)) _type_gt)
  (:size_x_gt
   (&optional __size_x_gt)
   (if __size_x_gt (setq _size_x_gt __size_x_gt)) _size_x_gt)
  (:size_y_gt
   (&optional __size_y_gt)
   (if __size_y_gt (setq _size_y_gt __size_y_gt)) _size_y_gt)
  (:size_z_gt
   (&optional __size_z_gt)
   (if __size_z_gt (setq _size_z_gt __size_z_gt)) _size_z_gt)
  (:heading_gt
   (&optional __heading_gt)
   (if __heading_gt (setq _heading_gt __heading_gt)) _heading_gt)
  (:speed_gt
   (&optional __speed_gt)
   (if __speed_gt (setq _speed_gt __speed_gt)) _speed_gt)
  (:x_gt
   (&optional __x_gt)
   (if __x_gt (setq _x_gt __x_gt)) _x_gt)
  (:y_gt
   (&optional __y_gt)
   (if __y_gt (setq _y_gt __y_gt)) _y_gt)
  (:z_gt
   (&optional __z_gt)
   (if __z_gt (setq _z_gt __z_gt)) _z_gt)
  (:serialization-length
   ()
   (+
    ;; float64 _timestamp
    8
    ;; int32 _id
    4
    ;; int16 _type
    2
    ;; float64 _size_x
    8
    ;; float64 _size_y
    8
    ;; float64 _size_z
    8
    ;; float64 _heading
    8
    ;; float64 _speed
    8
    ;; float64 _x
    8
    ;; float64 _y
    8
    ;; float64 _z
    8
    ;; float64 _longitude
    8
    ;; float64 _latitude
    8
    ;; float64 _confidence
    8
    ;; int16 _type_gt
    2
    ;; float64 _size_x_gt
    8
    ;; float64 _size_y_gt
    8
    ;; float64 _size_z_gt
    8
    ;; float64 _heading_gt
    8
    ;; float64 _speed_gt
    8
    ;; float64 _x_gt
    8
    ;; float64 _y_gt
    8
    ;; float64 _z_gt
    8
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; float64 _timestamp
       (sys::poke _timestamp (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; int32 _id
       (write-long _id s)
     ;; int16 _type
       (write-word _type s)
     ;; float64 _size_x
       (sys::poke _size_x (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _size_y
       (sys::poke _size_y (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _size_z
       (sys::poke _size_z (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _heading
       (sys::poke _heading (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _speed
       (sys::poke _speed (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _x
       (sys::poke _x (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _y
       (sys::poke _y (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _z
       (sys::poke _z (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _longitude
       (sys::poke _longitude (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _latitude
       (sys::poke _latitude (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _confidence
       (sys::poke _confidence (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; int16 _type_gt
       (write-word _type_gt s)
     ;; float64 _size_x_gt
       (sys::poke _size_x_gt (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _size_y_gt
       (sys::poke _size_y_gt (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _size_z_gt
       (sys::poke _size_z_gt (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _heading_gt
       (sys::poke _heading_gt (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _speed_gt
       (sys::poke _speed_gt (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _x_gt
       (sys::poke _x_gt (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _y_gt
       (sys::poke _y_gt (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _z_gt
       (sys::poke _z_gt (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; float64 _timestamp
     (setq _timestamp (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; int32 _id
     (setq _id (sys::peek buf ptr- :integer)) (incf ptr- 4)
   ;; int16 _type
     (setq _type (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; float64 _size_x
     (setq _size_x (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _size_y
     (setq _size_y (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _size_z
     (setq _size_z (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _heading
     (setq _heading (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _speed
     (setq _speed (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _x
     (setq _x (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _y
     (setq _y (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _z
     (setq _z (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _longitude
     (setq _longitude (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _latitude
     (setq _latitude (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _confidence
     (setq _confidence (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; int16 _type_gt
     (setq _type_gt (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; float64 _size_x_gt
     (setq _size_x_gt (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _size_y_gt
     (setq _size_y_gt (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _size_z_gt
     (setq _size_z_gt (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _heading_gt
     (setq _heading_gt (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _speed_gt
     (setq _speed_gt (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _x_gt
     (setq _x_gt (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _y_gt
     (setq _y_gt (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _z_gt
     (setq _z_gt (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;;
   self)
  )

(setf (get xperception_msgs::Object :md5sum-) "2c44886b8e81c73c66565953388c0ff2")
(setf (get xperception_msgs::Object :datatype-) "xperception_msgs/Object")
(setf (get xperception_msgs::Object :definition-)
      "
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



(provide :xperception_msgs/Object "2c44886b8e81c73c66565953388c0ff2")


