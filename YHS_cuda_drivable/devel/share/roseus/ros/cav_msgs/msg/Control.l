;; Auto-generated. Do not edit!


(when (boundp 'cav_msgs::Control)
  (if (not (find-package "CAV_MSGS"))
    (make-package "CAV_MSGS"))
  (shadow 'Control (find-package "CAV_MSGS")))
(unless (find-package "CAV_MSGS::CONTROL")
  (make-package "CAV_MSGS::CONTROL"))

(in-package "ROS")
;;//! \htmlinclude Control.msg.html


(defclass cav_msgs::Control
  :super ros::object
  :slots (_timestamp _count _brake_cmd _throttle_cmd _steering_cmd _gear_cmd _turn_signal_cmd _speed_cmd _acceleration_cmd _bywire_control_enable _emerg_brake _front_light _engine_enable _park_enable _vehicle_mode _yaw_speed_cmd _ey_out _ephi_out ))

(defmethod cav_msgs::Control
  (:init
   (&key
    ((:timestamp __timestamp) 0.0)
    ((:count __count) 0)
    ((:brake_cmd __brake_cmd) 0.0)
    ((:throttle_cmd __throttle_cmd) 0.0)
    ((:steering_cmd __steering_cmd) 0.0)
    ((:gear_cmd __gear_cmd) 0)
    ((:turn_signal_cmd __turn_signal_cmd) 0)
    ((:speed_cmd __speed_cmd) 0.0)
    ((:acceleration_cmd __acceleration_cmd) 0.0)
    ((:bywire_control_enable __bywire_control_enable) 0)
    ((:emerg_brake __emerg_brake) 0)
    ((:front_light __front_light) 0)
    ((:engine_enable __engine_enable) 0)
    ((:park_enable __park_enable) 0)
    ((:vehicle_mode __vehicle_mode) 0)
    ((:yaw_speed_cmd __yaw_speed_cmd) 0.0)
    ((:ey_out __ey_out) 0.0)
    ((:ephi_out __ephi_out) 0.0)
    )
   (send-super :init)
   (setq _timestamp (float __timestamp))
   (setq _count (round __count))
   (setq _brake_cmd (float __brake_cmd))
   (setq _throttle_cmd (float __throttle_cmd))
   (setq _steering_cmd (float __steering_cmd))
   (setq _gear_cmd (round __gear_cmd))
   (setq _turn_signal_cmd (round __turn_signal_cmd))
   (setq _speed_cmd (float __speed_cmd))
   (setq _acceleration_cmd (float __acceleration_cmd))
   (setq _bywire_control_enable (round __bywire_control_enable))
   (setq _emerg_brake (round __emerg_brake))
   (setq _front_light (round __front_light))
   (setq _engine_enable (round __engine_enable))
   (setq _park_enable (round __park_enable))
   (setq _vehicle_mode (round __vehicle_mode))
   (setq _yaw_speed_cmd (float __yaw_speed_cmd))
   (setq _ey_out (float __ey_out))
   (setq _ephi_out (float __ephi_out))
   self)
  (:timestamp
   (&optional __timestamp)
   (if __timestamp (setq _timestamp __timestamp)) _timestamp)
  (:count
   (&optional __count)
   (if __count (setq _count __count)) _count)
  (:brake_cmd
   (&optional __brake_cmd)
   (if __brake_cmd (setq _brake_cmd __brake_cmd)) _brake_cmd)
  (:throttle_cmd
   (&optional __throttle_cmd)
   (if __throttle_cmd (setq _throttle_cmd __throttle_cmd)) _throttle_cmd)
  (:steering_cmd
   (&optional __steering_cmd)
   (if __steering_cmd (setq _steering_cmd __steering_cmd)) _steering_cmd)
  (:gear_cmd
   (&optional __gear_cmd)
   (if __gear_cmd (setq _gear_cmd __gear_cmd)) _gear_cmd)
  (:turn_signal_cmd
   (&optional __turn_signal_cmd)
   (if __turn_signal_cmd (setq _turn_signal_cmd __turn_signal_cmd)) _turn_signal_cmd)
  (:speed_cmd
   (&optional __speed_cmd)
   (if __speed_cmd (setq _speed_cmd __speed_cmd)) _speed_cmd)
  (:acceleration_cmd
   (&optional __acceleration_cmd)
   (if __acceleration_cmd (setq _acceleration_cmd __acceleration_cmd)) _acceleration_cmd)
  (:bywire_control_enable
   (&optional __bywire_control_enable)
   (if __bywire_control_enable (setq _bywire_control_enable __bywire_control_enable)) _bywire_control_enable)
  (:emerg_brake
   (&optional __emerg_brake)
   (if __emerg_brake (setq _emerg_brake __emerg_brake)) _emerg_brake)
  (:front_light
   (&optional __front_light)
   (if __front_light (setq _front_light __front_light)) _front_light)
  (:engine_enable
   (&optional __engine_enable)
   (if __engine_enable (setq _engine_enable __engine_enable)) _engine_enable)
  (:park_enable
   (&optional __park_enable)
   (if __park_enable (setq _park_enable __park_enable)) _park_enable)
  (:vehicle_mode
   (&optional __vehicle_mode)
   (if __vehicle_mode (setq _vehicle_mode __vehicle_mode)) _vehicle_mode)
  (:yaw_speed_cmd
   (&optional __yaw_speed_cmd)
   (if __yaw_speed_cmd (setq _yaw_speed_cmd __yaw_speed_cmd)) _yaw_speed_cmd)
  (:ey_out
   (&optional __ey_out)
   (if __ey_out (setq _ey_out __ey_out)) _ey_out)
  (:ephi_out
   (&optional __ephi_out)
   (if __ephi_out (setq _ephi_out __ephi_out)) _ephi_out)
  (:serialization-length
   ()
   (+
    ;; float64 _timestamp
    8
    ;; int32 _count
    4
    ;; float64 _brake_cmd
    8
    ;; float64 _throttle_cmd
    8
    ;; float64 _steering_cmd
    8
    ;; int16 _gear_cmd
    2
    ;; int16 _turn_signal_cmd
    2
    ;; float64 _speed_cmd
    8
    ;; float64 _acceleration_cmd
    8
    ;; int16 _bywire_control_enable
    2
    ;; int16 _emerg_brake
    2
    ;; int16 _front_light
    2
    ;; int16 _engine_enable
    2
    ;; int16 _park_enable
    2
    ;; int16 _vehicle_mode
    2
    ;; float64 _yaw_speed_cmd
    8
    ;; float64 _ey_out
    8
    ;; float64 _ephi_out
    8
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; float64 _timestamp
       (sys::poke _timestamp (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; int32 _count
       (write-long _count s)
     ;; float64 _brake_cmd
       (sys::poke _brake_cmd (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _throttle_cmd
       (sys::poke _throttle_cmd (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _steering_cmd
       (sys::poke _steering_cmd (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; int16 _gear_cmd
       (write-word _gear_cmd s)
     ;; int16 _turn_signal_cmd
       (write-word _turn_signal_cmd s)
     ;; float64 _speed_cmd
       (sys::poke _speed_cmd (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _acceleration_cmd
       (sys::poke _acceleration_cmd (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; int16 _bywire_control_enable
       (write-word _bywire_control_enable s)
     ;; int16 _emerg_brake
       (write-word _emerg_brake s)
     ;; int16 _front_light
       (write-word _front_light s)
     ;; int16 _engine_enable
       (write-word _engine_enable s)
     ;; int16 _park_enable
       (write-word _park_enable s)
     ;; int16 _vehicle_mode
       (write-word _vehicle_mode s)
     ;; float64 _yaw_speed_cmd
       (sys::poke _yaw_speed_cmd (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _ey_out
       (sys::poke _ey_out (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _ephi_out
       (sys::poke _ephi_out (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; float64 _timestamp
     (setq _timestamp (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; int32 _count
     (setq _count (sys::peek buf ptr- :integer)) (incf ptr- 4)
   ;; float64 _brake_cmd
     (setq _brake_cmd (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _throttle_cmd
     (setq _throttle_cmd (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _steering_cmd
     (setq _steering_cmd (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; int16 _gear_cmd
     (setq _gear_cmd (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; int16 _turn_signal_cmd
     (setq _turn_signal_cmd (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; float64 _speed_cmd
     (setq _speed_cmd (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _acceleration_cmd
     (setq _acceleration_cmd (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; int16 _bywire_control_enable
     (setq _bywire_control_enable (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; int16 _emerg_brake
     (setq _emerg_brake (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; int16 _front_light
     (setq _front_light (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; int16 _engine_enable
     (setq _engine_enable (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; int16 _park_enable
     (setq _park_enable (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; int16 _vehicle_mode
     (setq _vehicle_mode (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; float64 _yaw_speed_cmd
     (setq _yaw_speed_cmd (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _ey_out
     (setq _ey_out (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _ephi_out
     (setq _ephi_out (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;;
   self)
  )

(setf (get cav_msgs::Control :md5sum-) "2213456a98df9c5879311b15b53093ed")
(setf (get cav_msgs::Control :datatype-) "cav_msgs/Control")
(setf (get cav_msgs::Control :definition-)
      "##timestamp
float64 timestamp 			#ros time
int32 	count               #1,2,3,4,5,...

float64 brake_cmd 			#brake pedal opening [0-1, 100%]
float64 throttle_cmd 		#throttle pedal openning [0-1, 100%]
float64 steering_cmd 		#(-0.25pi to 0.25pi) rad, angle of wheels
int16 	gear_cmd            # NONE:0, PARK:1, REVERSE:2, NEUTRAL:3, DRIVE:4, LOW:5
int16 	turn_signal_cmd     # NONE:0, LEFT:1, RIGHT:2

float64 speed_cmd           #speed cmd, m/s
float64 acceleration_cmd    #acceleration cmd, m/s/s

int16 bywire_control_enable #self-driving enabled, 0-off, 1-on
int16 emerg_brake           #0:normal brake, 1:emergency brake
int16 front_light           #0-off, 1-on

int16 engine_enable         #0-off 1-on
int16 park_enable           #0-off, 1-on
int16 vehicle_mode          #0-pure EV, 1-Hybrid
float64 yaw_speed_cmd       #rad/s


##
float64 ey_out              #tracking error, lateral offset
float64 ephi_out            #tracking error, heading angle

")



(provide :cav_msgs/Control "2213456a98df9c5879311b15b53093ed")


