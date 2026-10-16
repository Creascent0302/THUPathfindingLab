;; Auto-generated. Do not edit!


(when (boundp 'cav_msgs::Gpybm)
  (if (not (find-package "CAV_MSGS"))
    (make-package "CAV_MSGS"))
  (shadow 'Gpybm (find-package "CAV_MSGS")))
(unless (find-package "CAV_MSGS::GPYBM")
  (make-package "CAV_MSGS::GPYBM"))

(in-package "ROS")
;;//! \htmlinclude Gpybm.msg.html


(defclass cav_msgs::Gpybm
  :super ros::object
  :slots (_serial_number _utc _latitude _longitude _height _yaw _pitch _north_vel _east_vel _earth_vel _vel _gaussian_x _gaussian_y _base_station_x _base_station_y _status _status_vice ))

(defmethod cav_msgs::Gpybm
  (:init
   (&key
    ((:serial_number __serial_number) "")
    ((:utc __utc) 0.0)
    ((:latitude __latitude) 0.0)
    ((:longitude __longitude) 0.0)
    ((:height __height) 0.0)
    ((:yaw __yaw) 0.0)
    ((:pitch __pitch) 0.0)
    ((:north_vel __north_vel) 0.0)
    ((:east_vel __east_vel) 0.0)
    ((:earth_vel __earth_vel) 0.0)
    ((:vel __vel) 0.0)
    ((:gaussian_x __gaussian_x) 0.0)
    ((:gaussian_y __gaussian_y) 0.0)
    ((:base_station_x __base_station_x) 0.0)
    ((:base_station_y __base_station_y) 0.0)
    ((:status __status) 0)
    ((:status_vice __status_vice) 0)
    )
   (send-super :init)
   (setq _serial_number (string __serial_number))
   (setq _utc (float __utc))
   (setq _latitude (float __latitude))
   (setq _longitude (float __longitude))
   (setq _height (float __height))
   (setq _yaw (float __yaw))
   (setq _pitch (float __pitch))
   (setq _north_vel (float __north_vel))
   (setq _east_vel (float __east_vel))
   (setq _earth_vel (float __earth_vel))
   (setq _vel (float __vel))
   (setq _gaussian_x (float __gaussian_x))
   (setq _gaussian_y (float __gaussian_y))
   (setq _base_station_x (float __base_station_x))
   (setq _base_station_y (float __base_station_y))
   (setq _status (round __status))
   (setq _status_vice (round __status_vice))
   self)
  (:serial_number
   (&optional __serial_number)
   (if __serial_number (setq _serial_number __serial_number)) _serial_number)
  (:utc
   (&optional __utc)
   (if __utc (setq _utc __utc)) _utc)
  (:latitude
   (&optional __latitude)
   (if __latitude (setq _latitude __latitude)) _latitude)
  (:longitude
   (&optional __longitude)
   (if __longitude (setq _longitude __longitude)) _longitude)
  (:height
   (&optional __height)
   (if __height (setq _height __height)) _height)
  (:yaw
   (&optional __yaw)
   (if __yaw (setq _yaw __yaw)) _yaw)
  (:pitch
   (&optional __pitch)
   (if __pitch (setq _pitch __pitch)) _pitch)
  (:north_vel
   (&optional __north_vel)
   (if __north_vel (setq _north_vel __north_vel)) _north_vel)
  (:east_vel
   (&optional __east_vel)
   (if __east_vel (setq _east_vel __east_vel)) _east_vel)
  (:earth_vel
   (&optional __earth_vel)
   (if __earth_vel (setq _earth_vel __earth_vel)) _earth_vel)
  (:vel
   (&optional __vel)
   (if __vel (setq _vel __vel)) _vel)
  (:gaussian_x
   (&optional __gaussian_x)
   (if __gaussian_x (setq _gaussian_x __gaussian_x)) _gaussian_x)
  (:gaussian_y
   (&optional __gaussian_y)
   (if __gaussian_y (setq _gaussian_y __gaussian_y)) _gaussian_y)
  (:base_station_x
   (&optional __base_station_x)
   (if __base_station_x (setq _base_station_x __base_station_x)) _base_station_x)
  (:base_station_y
   (&optional __base_station_y)
   (if __base_station_y (setq _base_station_y __base_station_y)) _base_station_y)
  (:status
   (&optional __status)
   (if __status (setq _status __status)) _status)
  (:status_vice
   (&optional __status_vice)
   (if __status_vice (setq _status_vice __status_vice)) _status_vice)
  (:serialization-length
   ()
   (+
    ;; string _serial_number
    4 (length _serial_number)
    ;; float64 _utc
    8
    ;; float64 _latitude
    8
    ;; float64 _longitude
    8
    ;; float64 _height
    8
    ;; float64 _yaw
    8
    ;; float64 _pitch
    8
    ;; float64 _north_vel
    8
    ;; float64 _east_vel
    8
    ;; float64 _earth_vel
    8
    ;; float64 _vel
    8
    ;; float64 _gaussian_x
    8
    ;; float64 _gaussian_y
    8
    ;; float64 _base_station_x
    8
    ;; float64 _base_station_y
    8
    ;; int16 _status
    2
    ;; int16 _status_vice
    2
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; string _serial_number
       (write-long (length _serial_number) s) (princ _serial_number s)
     ;; float64 _utc
       (sys::poke _utc (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _latitude
       (sys::poke _latitude (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _longitude
       (sys::poke _longitude (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _height
       (sys::poke _height (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _yaw
       (sys::poke _yaw (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _pitch
       (sys::poke _pitch (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _north_vel
       (sys::poke _north_vel (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _east_vel
       (sys::poke _east_vel (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _earth_vel
       (sys::poke _earth_vel (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _vel
       (sys::poke _vel (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _gaussian_x
       (sys::poke _gaussian_x (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _gaussian_y
       (sys::poke _gaussian_y (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _base_station_x
       (sys::poke _base_station_x (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _base_station_y
       (sys::poke _base_station_y (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; int16 _status
       (write-word _status s)
     ;; int16 _status_vice
       (write-word _status_vice s)
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; string _serial_number
     (let (n) (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4) (setq _serial_number (subseq buf ptr- (+ ptr- n))) (incf ptr- n))
   ;; float64 _utc
     (setq _utc (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _latitude
     (setq _latitude (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _longitude
     (setq _longitude (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _height
     (setq _height (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _yaw
     (setq _yaw (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _pitch
     (setq _pitch (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _north_vel
     (setq _north_vel (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _east_vel
     (setq _east_vel (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _earth_vel
     (setq _earth_vel (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _vel
     (setq _vel (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _gaussian_x
     (setq _gaussian_x (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _gaussian_y
     (setq _gaussian_y (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _base_station_x
     (setq _base_station_x (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _base_station_y
     (setq _base_station_y (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; int16 _status
     (setq _status (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; int16 _status_vice
     (setq _status_vice (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;;
   self)
  )

(setf (get cav_msgs::Gpybm :md5sum-) "705e6b1ef5c61da21386f82da44e4cfd")
(setf (get cav_msgs::Gpybm :datatype-) "cav_msgs/Gpybm")
(setf (get cav_msgs::Gpybm :definition-)
      "string serial_number # sino gnss hardware serial number
float64 utc       # utc time
float64 latitude
float64 longitude
float64 height

float64 yaw
float64 pitch  
float64 north_vel
float64 east_vel
float64 earth_vel
float64 vel
float64 gaussian_x
float64 gaussian_y
float64 base_station_x
float64 base_station_y

int16 status	
int16 status_vice


")



(provide :cav_msgs/Gpybm "705e6b1ef5c61da21386f82da44e4cfd")


