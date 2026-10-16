;; Auto-generated. Do not edit!


(when (boundp 'LocalMap_msgs::LocalMap_Element)
  (if (not (find-package "LOCALMAP_MSGS"))
    (make-package "LOCALMAP_MSGS"))
  (shadow 'LocalMap_Element (find-package "LOCALMAP_MSGS")))
(unless (find-package "LOCALMAP_MSGS::LOCALMAP_ELEMENT")
  (make-package "LOCALMAP_MSGS::LOCALMAP_ELEMENT"))

(in-package "ROS")
;;//! \htmlinclude LocalMap_Element.msg.html


(defclass LocalMap_msgs::LocalMap_Element
  :super ros::object
  :slots (_x_id _y_id _driveable_index _driveable_value _ct_x _ct_y ))

(defmethod LocalMap_msgs::LocalMap_Element
  (:init
   (&key
    ((:x_id __x_id) 0)
    ((:y_id __y_id) 0)
    ((:driveable_index __driveable_index) nil)
    ((:driveable_value __driveable_value) 0.0)
    ((:ct_x __ct_x) 0.0)
    ((:ct_y __ct_y) 0.0)
    )
   (send-super :init)
   (setq _x_id (round __x_id))
   (setq _y_id (round __y_id))
   (setq _driveable_index __driveable_index)
   (setq _driveable_value (float __driveable_value))
   (setq _ct_x (float __ct_x))
   (setq _ct_y (float __ct_y))
   self)
  (:x_id
   (&optional __x_id)
   (if __x_id (setq _x_id __x_id)) _x_id)
  (:y_id
   (&optional __y_id)
   (if __y_id (setq _y_id __y_id)) _y_id)
  (:driveable_index
   (&optional (__driveable_index :null))
   (if (not (eq __driveable_index :null)) (setq _driveable_index __driveable_index)) _driveable_index)
  (:driveable_value
   (&optional __driveable_value)
   (if __driveable_value (setq _driveable_value __driveable_value)) _driveable_value)
  (:ct_x
   (&optional __ct_x)
   (if __ct_x (setq _ct_x __ct_x)) _ct_x)
  (:ct_y
   (&optional __ct_y)
   (if __ct_y (setq _ct_y __ct_y)) _ct_y)
  (:serialization-length
   ()
   (+
    ;; int32 _x_id
    4
    ;; int32 _y_id
    4
    ;; bool _driveable_index
    1
    ;; float64 _driveable_value
    8
    ;; float64 _ct_x
    8
    ;; float64 _ct_y
    8
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; int32 _x_id
       (write-long _x_id s)
     ;; int32 _y_id
       (write-long _y_id s)
     ;; bool _driveable_index
       (if _driveable_index (write-byte -1 s) (write-byte 0 s))
     ;; float64 _driveable_value
       (sys::poke _driveable_value (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _ct_x
       (sys::poke _ct_x (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _ct_y
       (sys::poke _ct_y (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; int32 _x_id
     (setq _x_id (sys::peek buf ptr- :integer)) (incf ptr- 4)
   ;; int32 _y_id
     (setq _y_id (sys::peek buf ptr- :integer)) (incf ptr- 4)
   ;; bool _driveable_index
     (setq _driveable_index (not (= 0 (sys::peek buf ptr- :char)))) (incf ptr- 1)
   ;; float64 _driveable_value
     (setq _driveable_value (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _ct_x
     (setq _ct_x (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _ct_y
     (setq _ct_y (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;;
   self)
  )

(setf (get LocalMap_msgs::LocalMap_Element :md5sum-) "df3f78b67932ffce5c991845c7a225e9")
(setf (get LocalMap_msgs::LocalMap_Element :datatype-) "LocalMap_msgs/LocalMap_Element")
(setf (get LocalMap_msgs::LocalMap_Element :definition-)
      "
int32 x_id    #0,1,2,3,4,... east: +x
int32 y_id    #0,1,2,3,4,... north: +y

bool driveable_index     #0:not  1: driveable
float64 driveable_value    #[0,1] 1:best

float64 ct_x      # x of the center of this box
float64 ct_y      # y of the center of this box
")



(provide :LocalMap_msgs/LocalMap_Element "df3f78b67932ffce5c991845c7a225e9")


