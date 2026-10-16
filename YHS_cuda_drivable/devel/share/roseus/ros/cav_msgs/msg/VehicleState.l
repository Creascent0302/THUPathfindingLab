;; Auto-generated. Do not edit!


(when (boundp 'cav_msgs::VehicleState)
  (if (not (find-package "CAV_MSGS"))
    (make-package "CAV_MSGS"))
  (shadow 'VehicleState (find-package "CAV_MSGS")))
(unless (find-package "CAV_MSGS::VEHICLESTATE")
  (make-package "CAV_MSGS::VEHICLESTATE"))

(in-package "ROS")
;;//! \htmlinclude VehicleState.msg.html


(defclass cav_msgs::VehicleState
  :super ros::object
  :slots (_timestamp _id _name _vehicle_state _type _RTK_state_string _RTK_seq_num _RTK_timestamp_sec _RTK_timestamp_nsec _RTK_gps_status _RTK_gps_service _RTK_gps_longitude _RTK_gps_latitude _RTK_gps_altitude _RTK_gps_UTM_x _RTK_gps_UTM_y _RTK_gps_UTM_z _RTK_linear_ENU_vx _RTK_linear_ENU_vy _RTK_linear_ENU_vz _RTK_linear_vx _RTK_linear_vy _RTK_linear_vz _RTK_angular_vx _RTK_angular_vy _RTK_angular_vz _x _y _z _speed_x _speed_y _speed_z _acc_x _acc_y _acc_z _heading _pitch _roll _yaw_rate _size_x _size_y _size_z _wheelbase _gear_pos _by_wire_enabled _vehicle_mode _throttle_cmd _throttle_input _throttle_state _throttle_enabled _throttle_override _throttle_driver _throttle_timeout _brake_cmd _brake_input _brake_state _brake_torq_cmd _brake_torq_input _brake_torq_state _brake_boo_output _brake_enabled _brake_override _brake_driver _brake_timeout _steer_cmd _steer_state_front_wheel _steer_torque _steer_enabled _steer_override _steer_timeout _battery_volt _battery_SOC _engine_speed _vehicle_bug_code _vehicle_state_code ))

(defmethod cav_msgs::VehicleState
  (:init
   (&key
    ((:timestamp __timestamp) 0.0)
    ((:id __id) 0)
    ((:name __name) "")
    ((:vehicle_state __vehicle_state) 0)
    ((:type __type) 0)
    ((:RTK_state_string __RTK_state_string) "")
    ((:RTK_seq_num __RTK_seq_num) 0)
    ((:RTK_timestamp_sec __RTK_timestamp_sec) 0)
    ((:RTK_timestamp_nsec __RTK_timestamp_nsec) 0)
    ((:RTK_gps_status __RTK_gps_status) 0)
    ((:RTK_gps_service __RTK_gps_service) 0)
    ((:RTK_gps_longitude __RTK_gps_longitude) 0.0)
    ((:RTK_gps_latitude __RTK_gps_latitude) 0.0)
    ((:RTK_gps_altitude __RTK_gps_altitude) 0.0)
    ((:RTK_gps_UTM_x __RTK_gps_UTM_x) 0.0)
    ((:RTK_gps_UTM_y __RTK_gps_UTM_y) 0.0)
    ((:RTK_gps_UTM_z __RTK_gps_UTM_z) 0.0)
    ((:RTK_linear_ENU_vx __RTK_linear_ENU_vx) 0.0)
    ((:RTK_linear_ENU_vy __RTK_linear_ENU_vy) 0.0)
    ((:RTK_linear_ENU_vz __RTK_linear_ENU_vz) 0.0)
    ((:RTK_linear_vx __RTK_linear_vx) 0.0)
    ((:RTK_linear_vy __RTK_linear_vy) 0.0)
    ((:RTK_linear_vz __RTK_linear_vz) 0.0)
    ((:RTK_angular_vx __RTK_angular_vx) 0.0)
    ((:RTK_angular_vy __RTK_angular_vy) 0.0)
    ((:RTK_angular_vz __RTK_angular_vz) 0.0)
    ((:x __x) 0.0)
    ((:y __y) 0.0)
    ((:z __z) 0.0)
    ((:speed_x __speed_x) 0.0)
    ((:speed_y __speed_y) 0.0)
    ((:speed_z __speed_z) 0.0)
    ((:acc_x __acc_x) 0.0)
    ((:acc_y __acc_y) 0.0)
    ((:acc_z __acc_z) 0.0)
    ((:heading __heading) 0.0)
    ((:pitch __pitch) 0.0)
    ((:roll __roll) 0.0)
    ((:yaw_rate __yaw_rate) 0.0)
    ((:size_x __size_x) 0.0)
    ((:size_y __size_y) 0.0)
    ((:size_z __size_z) 0.0)
    ((:wheelbase __wheelbase) 0.0)
    ((:gear_pos __gear_pos) 0)
    ((:by_wire_enabled __by_wire_enabled) nil)
    ((:vehicle_mode __vehicle_mode) 0)
    ((:throttle_cmd __throttle_cmd) 0.0)
    ((:throttle_input __throttle_input) 0.0)
    ((:throttle_state __throttle_state) 0.0)
    ((:throttle_enabled __throttle_enabled) nil)
    ((:throttle_override __throttle_override) nil)
    ((:throttle_driver __throttle_driver) nil)
    ((:throttle_timeout __throttle_timeout) nil)
    ((:brake_cmd __brake_cmd) 0.0)
    ((:brake_input __brake_input) 0.0)
    ((:brake_state __brake_state) 0.0)
    ((:brake_torq_cmd __brake_torq_cmd) 0.0)
    ((:brake_torq_input __brake_torq_input) 0.0)
    ((:brake_torq_state __brake_torq_state) 0.0)
    ((:brake_boo_output __brake_boo_output) nil)
    ((:brake_enabled __brake_enabled) nil)
    ((:brake_override __brake_override) nil)
    ((:brake_driver __brake_driver) nil)
    ((:brake_timeout __brake_timeout) nil)
    ((:steer_cmd __steer_cmd) 0.0)
    ((:steer_state_front_wheel __steer_state_front_wheel) 0.0)
    ((:steer_torque __steer_torque) 0.0)
    ((:steer_enabled __steer_enabled) nil)
    ((:steer_override __steer_override) nil)
    ((:steer_timeout __steer_timeout) nil)
    ((:battery_volt __battery_volt) 0.0)
    ((:battery_SOC __battery_SOC) 0.0)
    ((:engine_speed __engine_speed) 0)
    ((:vehicle_bug_code __vehicle_bug_code) 0)
    ((:vehicle_state_code __vehicle_state_code) 0)
    )
   (send-super :init)
   (setq _timestamp (float __timestamp))
   (setq _id (round __id))
   (setq _name (string __name))
   (setq _vehicle_state (round __vehicle_state))
   (setq _type (round __type))
   (setq _RTK_state_string (string __RTK_state_string))
   (setq _RTK_seq_num (round __RTK_seq_num))
   (setq _RTK_timestamp_sec (round __RTK_timestamp_sec))
   (setq _RTK_timestamp_nsec (round __RTK_timestamp_nsec))
   (setq _RTK_gps_status (round __RTK_gps_status))
   (setq _RTK_gps_service (round __RTK_gps_service))
   (setq _RTK_gps_longitude (float __RTK_gps_longitude))
   (setq _RTK_gps_latitude (float __RTK_gps_latitude))
   (setq _RTK_gps_altitude (float __RTK_gps_altitude))
   (setq _RTK_gps_UTM_x (float __RTK_gps_UTM_x))
   (setq _RTK_gps_UTM_y (float __RTK_gps_UTM_y))
   (setq _RTK_gps_UTM_z (float __RTK_gps_UTM_z))
   (setq _RTK_linear_ENU_vx (float __RTK_linear_ENU_vx))
   (setq _RTK_linear_ENU_vy (float __RTK_linear_ENU_vy))
   (setq _RTK_linear_ENU_vz (float __RTK_linear_ENU_vz))
   (setq _RTK_linear_vx (float __RTK_linear_vx))
   (setq _RTK_linear_vy (float __RTK_linear_vy))
   (setq _RTK_linear_vz (float __RTK_linear_vz))
   (setq _RTK_angular_vx (float __RTK_angular_vx))
   (setq _RTK_angular_vy (float __RTK_angular_vy))
   (setq _RTK_angular_vz (float __RTK_angular_vz))
   (setq _x (float __x))
   (setq _y (float __y))
   (setq _z (float __z))
   (setq _speed_x (float __speed_x))
   (setq _speed_y (float __speed_y))
   (setq _speed_z (float __speed_z))
   (setq _acc_x (float __acc_x))
   (setq _acc_y (float __acc_y))
   (setq _acc_z (float __acc_z))
   (setq _heading (float __heading))
   (setq _pitch (float __pitch))
   (setq _roll (float __roll))
   (setq _yaw_rate (float __yaw_rate))
   (setq _size_x (float __size_x))
   (setq _size_y (float __size_y))
   (setq _size_z (float __size_z))
   (setq _wheelbase (float __wheelbase))
   (setq _gear_pos (round __gear_pos))
   (setq _by_wire_enabled __by_wire_enabled)
   (setq _vehicle_mode (round __vehicle_mode))
   (setq _throttle_cmd (float __throttle_cmd))
   (setq _throttle_input (float __throttle_input))
   (setq _throttle_state (float __throttle_state))
   (setq _throttle_enabled __throttle_enabled)
   (setq _throttle_override __throttle_override)
   (setq _throttle_driver __throttle_driver)
   (setq _throttle_timeout __throttle_timeout)
   (setq _brake_cmd (float __brake_cmd))
   (setq _brake_input (float __brake_input))
   (setq _brake_state (float __brake_state))
   (setq _brake_torq_cmd (float __brake_torq_cmd))
   (setq _brake_torq_input (float __brake_torq_input))
   (setq _brake_torq_state (float __brake_torq_state))
   (setq _brake_boo_output __brake_boo_output)
   (setq _brake_enabled __brake_enabled)
   (setq _brake_override __brake_override)
   (setq _brake_driver __brake_driver)
   (setq _brake_timeout __brake_timeout)
   (setq _steer_cmd (float __steer_cmd))
   (setq _steer_state_front_wheel (float __steer_state_front_wheel))
   (setq _steer_torque (float __steer_torque))
   (setq _steer_enabled __steer_enabled)
   (setq _steer_override __steer_override)
   (setq _steer_timeout __steer_timeout)
   (setq _battery_volt (float __battery_volt))
   (setq _battery_SOC (float __battery_SOC))
   (setq _engine_speed (round __engine_speed))
   (setq _vehicle_bug_code (round __vehicle_bug_code))
   (setq _vehicle_state_code (round __vehicle_state_code))
   self)
  (:timestamp
   (&optional __timestamp)
   (if __timestamp (setq _timestamp __timestamp)) _timestamp)
  (:id
   (&optional __id)
   (if __id (setq _id __id)) _id)
  (:name
   (&optional __name)
   (if __name (setq _name __name)) _name)
  (:vehicle_state
   (&optional __vehicle_state)
   (if __vehicle_state (setq _vehicle_state __vehicle_state)) _vehicle_state)
  (:type
   (&optional __type)
   (if __type (setq _type __type)) _type)
  (:RTK_state_string
   (&optional __RTK_state_string)
   (if __RTK_state_string (setq _RTK_state_string __RTK_state_string)) _RTK_state_string)
  (:RTK_seq_num
   (&optional __RTK_seq_num)
   (if __RTK_seq_num (setq _RTK_seq_num __RTK_seq_num)) _RTK_seq_num)
  (:RTK_timestamp_sec
   (&optional __RTK_timestamp_sec)
   (if __RTK_timestamp_sec (setq _RTK_timestamp_sec __RTK_timestamp_sec)) _RTK_timestamp_sec)
  (:RTK_timestamp_nsec
   (&optional __RTK_timestamp_nsec)
   (if __RTK_timestamp_nsec (setq _RTK_timestamp_nsec __RTK_timestamp_nsec)) _RTK_timestamp_nsec)
  (:RTK_gps_status
   (&optional __RTK_gps_status)
   (if __RTK_gps_status (setq _RTK_gps_status __RTK_gps_status)) _RTK_gps_status)
  (:RTK_gps_service
   (&optional __RTK_gps_service)
   (if __RTK_gps_service (setq _RTK_gps_service __RTK_gps_service)) _RTK_gps_service)
  (:RTK_gps_longitude
   (&optional __RTK_gps_longitude)
   (if __RTK_gps_longitude (setq _RTK_gps_longitude __RTK_gps_longitude)) _RTK_gps_longitude)
  (:RTK_gps_latitude
   (&optional __RTK_gps_latitude)
   (if __RTK_gps_latitude (setq _RTK_gps_latitude __RTK_gps_latitude)) _RTK_gps_latitude)
  (:RTK_gps_altitude
   (&optional __RTK_gps_altitude)
   (if __RTK_gps_altitude (setq _RTK_gps_altitude __RTK_gps_altitude)) _RTK_gps_altitude)
  (:RTK_gps_UTM_x
   (&optional __RTK_gps_UTM_x)
   (if __RTK_gps_UTM_x (setq _RTK_gps_UTM_x __RTK_gps_UTM_x)) _RTK_gps_UTM_x)
  (:RTK_gps_UTM_y
   (&optional __RTK_gps_UTM_y)
   (if __RTK_gps_UTM_y (setq _RTK_gps_UTM_y __RTK_gps_UTM_y)) _RTK_gps_UTM_y)
  (:RTK_gps_UTM_z
   (&optional __RTK_gps_UTM_z)
   (if __RTK_gps_UTM_z (setq _RTK_gps_UTM_z __RTK_gps_UTM_z)) _RTK_gps_UTM_z)
  (:RTK_linear_ENU_vx
   (&optional __RTK_linear_ENU_vx)
   (if __RTK_linear_ENU_vx (setq _RTK_linear_ENU_vx __RTK_linear_ENU_vx)) _RTK_linear_ENU_vx)
  (:RTK_linear_ENU_vy
   (&optional __RTK_linear_ENU_vy)
   (if __RTK_linear_ENU_vy (setq _RTK_linear_ENU_vy __RTK_linear_ENU_vy)) _RTK_linear_ENU_vy)
  (:RTK_linear_ENU_vz
   (&optional __RTK_linear_ENU_vz)
   (if __RTK_linear_ENU_vz (setq _RTK_linear_ENU_vz __RTK_linear_ENU_vz)) _RTK_linear_ENU_vz)
  (:RTK_linear_vx
   (&optional __RTK_linear_vx)
   (if __RTK_linear_vx (setq _RTK_linear_vx __RTK_linear_vx)) _RTK_linear_vx)
  (:RTK_linear_vy
   (&optional __RTK_linear_vy)
   (if __RTK_linear_vy (setq _RTK_linear_vy __RTK_linear_vy)) _RTK_linear_vy)
  (:RTK_linear_vz
   (&optional __RTK_linear_vz)
   (if __RTK_linear_vz (setq _RTK_linear_vz __RTK_linear_vz)) _RTK_linear_vz)
  (:RTK_angular_vx
   (&optional __RTK_angular_vx)
   (if __RTK_angular_vx (setq _RTK_angular_vx __RTK_angular_vx)) _RTK_angular_vx)
  (:RTK_angular_vy
   (&optional __RTK_angular_vy)
   (if __RTK_angular_vy (setq _RTK_angular_vy __RTK_angular_vy)) _RTK_angular_vy)
  (:RTK_angular_vz
   (&optional __RTK_angular_vz)
   (if __RTK_angular_vz (setq _RTK_angular_vz __RTK_angular_vz)) _RTK_angular_vz)
  (:x
   (&optional __x)
   (if __x (setq _x __x)) _x)
  (:y
   (&optional __y)
   (if __y (setq _y __y)) _y)
  (:z
   (&optional __z)
   (if __z (setq _z __z)) _z)
  (:speed_x
   (&optional __speed_x)
   (if __speed_x (setq _speed_x __speed_x)) _speed_x)
  (:speed_y
   (&optional __speed_y)
   (if __speed_y (setq _speed_y __speed_y)) _speed_y)
  (:speed_z
   (&optional __speed_z)
   (if __speed_z (setq _speed_z __speed_z)) _speed_z)
  (:acc_x
   (&optional __acc_x)
   (if __acc_x (setq _acc_x __acc_x)) _acc_x)
  (:acc_y
   (&optional __acc_y)
   (if __acc_y (setq _acc_y __acc_y)) _acc_y)
  (:acc_z
   (&optional __acc_z)
   (if __acc_z (setq _acc_z __acc_z)) _acc_z)
  (:heading
   (&optional __heading)
   (if __heading (setq _heading __heading)) _heading)
  (:pitch
   (&optional __pitch)
   (if __pitch (setq _pitch __pitch)) _pitch)
  (:roll
   (&optional __roll)
   (if __roll (setq _roll __roll)) _roll)
  (:yaw_rate
   (&optional __yaw_rate)
   (if __yaw_rate (setq _yaw_rate __yaw_rate)) _yaw_rate)
  (:size_x
   (&optional __size_x)
   (if __size_x (setq _size_x __size_x)) _size_x)
  (:size_y
   (&optional __size_y)
   (if __size_y (setq _size_y __size_y)) _size_y)
  (:size_z
   (&optional __size_z)
   (if __size_z (setq _size_z __size_z)) _size_z)
  (:wheelbase
   (&optional __wheelbase)
   (if __wheelbase (setq _wheelbase __wheelbase)) _wheelbase)
  (:gear_pos
   (&optional __gear_pos)
   (if __gear_pos (setq _gear_pos __gear_pos)) _gear_pos)
  (:by_wire_enabled
   (&optional (__by_wire_enabled :null))
   (if (not (eq __by_wire_enabled :null)) (setq _by_wire_enabled __by_wire_enabled)) _by_wire_enabled)
  (:vehicle_mode
   (&optional __vehicle_mode)
   (if __vehicle_mode (setq _vehicle_mode __vehicle_mode)) _vehicle_mode)
  (:throttle_cmd
   (&optional __throttle_cmd)
   (if __throttle_cmd (setq _throttle_cmd __throttle_cmd)) _throttle_cmd)
  (:throttle_input
   (&optional __throttle_input)
   (if __throttle_input (setq _throttle_input __throttle_input)) _throttle_input)
  (:throttle_state
   (&optional __throttle_state)
   (if __throttle_state (setq _throttle_state __throttle_state)) _throttle_state)
  (:throttle_enabled
   (&optional (__throttle_enabled :null))
   (if (not (eq __throttle_enabled :null)) (setq _throttle_enabled __throttle_enabled)) _throttle_enabled)
  (:throttle_override
   (&optional (__throttle_override :null))
   (if (not (eq __throttle_override :null)) (setq _throttle_override __throttle_override)) _throttle_override)
  (:throttle_driver
   (&optional (__throttle_driver :null))
   (if (not (eq __throttle_driver :null)) (setq _throttle_driver __throttle_driver)) _throttle_driver)
  (:throttle_timeout
   (&optional (__throttle_timeout :null))
   (if (not (eq __throttle_timeout :null)) (setq _throttle_timeout __throttle_timeout)) _throttle_timeout)
  (:brake_cmd
   (&optional __brake_cmd)
   (if __brake_cmd (setq _brake_cmd __brake_cmd)) _brake_cmd)
  (:brake_input
   (&optional __brake_input)
   (if __brake_input (setq _brake_input __brake_input)) _brake_input)
  (:brake_state
   (&optional __brake_state)
   (if __brake_state (setq _brake_state __brake_state)) _brake_state)
  (:brake_torq_cmd
   (&optional __brake_torq_cmd)
   (if __brake_torq_cmd (setq _brake_torq_cmd __brake_torq_cmd)) _brake_torq_cmd)
  (:brake_torq_input
   (&optional __brake_torq_input)
   (if __brake_torq_input (setq _brake_torq_input __brake_torq_input)) _brake_torq_input)
  (:brake_torq_state
   (&optional __brake_torq_state)
   (if __brake_torq_state (setq _brake_torq_state __brake_torq_state)) _brake_torq_state)
  (:brake_boo_output
   (&optional (__brake_boo_output :null))
   (if (not (eq __brake_boo_output :null)) (setq _brake_boo_output __brake_boo_output)) _brake_boo_output)
  (:brake_enabled
   (&optional (__brake_enabled :null))
   (if (not (eq __brake_enabled :null)) (setq _brake_enabled __brake_enabled)) _brake_enabled)
  (:brake_override
   (&optional (__brake_override :null))
   (if (not (eq __brake_override :null)) (setq _brake_override __brake_override)) _brake_override)
  (:brake_driver
   (&optional (__brake_driver :null))
   (if (not (eq __brake_driver :null)) (setq _brake_driver __brake_driver)) _brake_driver)
  (:brake_timeout
   (&optional (__brake_timeout :null))
   (if (not (eq __brake_timeout :null)) (setq _brake_timeout __brake_timeout)) _brake_timeout)
  (:steer_cmd
   (&optional __steer_cmd)
   (if __steer_cmd (setq _steer_cmd __steer_cmd)) _steer_cmd)
  (:steer_state_front_wheel
   (&optional __steer_state_front_wheel)
   (if __steer_state_front_wheel (setq _steer_state_front_wheel __steer_state_front_wheel)) _steer_state_front_wheel)
  (:steer_torque
   (&optional __steer_torque)
   (if __steer_torque (setq _steer_torque __steer_torque)) _steer_torque)
  (:steer_enabled
   (&optional (__steer_enabled :null))
   (if (not (eq __steer_enabled :null)) (setq _steer_enabled __steer_enabled)) _steer_enabled)
  (:steer_override
   (&optional (__steer_override :null))
   (if (not (eq __steer_override :null)) (setq _steer_override __steer_override)) _steer_override)
  (:steer_timeout
   (&optional (__steer_timeout :null))
   (if (not (eq __steer_timeout :null)) (setq _steer_timeout __steer_timeout)) _steer_timeout)
  (:battery_volt
   (&optional __battery_volt)
   (if __battery_volt (setq _battery_volt __battery_volt)) _battery_volt)
  (:battery_SOC
   (&optional __battery_SOC)
   (if __battery_SOC (setq _battery_SOC __battery_SOC)) _battery_SOC)
  (:engine_speed
   (&optional __engine_speed)
   (if __engine_speed (setq _engine_speed __engine_speed)) _engine_speed)
  (:vehicle_bug_code
   (&optional __vehicle_bug_code)
   (if __vehicle_bug_code (setq _vehicle_bug_code __vehicle_bug_code)) _vehicle_bug_code)
  (:vehicle_state_code
   (&optional __vehicle_state_code)
   (if __vehicle_state_code (setq _vehicle_state_code __vehicle_state_code)) _vehicle_state_code)
  (:serialization-length
   ()
   (+
    ;; float64 _timestamp
    8
    ;; int32 _id
    4
    ;; string _name
    4 (length _name)
    ;; int16 _vehicle_state
    2
    ;; int16 _type
    2
    ;; string _RTK_state_string
    4 (length _RTK_state_string)
    ;; int64 _RTK_seq_num
    8
    ;; int64 _RTK_timestamp_sec
    8
    ;; int64 _RTK_timestamp_nsec
    8
    ;; int16 _RTK_gps_status
    2
    ;; int16 _RTK_gps_service
    2
    ;; float64 _RTK_gps_longitude
    8
    ;; float64 _RTK_gps_latitude
    8
    ;; float64 _RTK_gps_altitude
    8
    ;; float64 _RTK_gps_UTM_x
    8
    ;; float64 _RTK_gps_UTM_y
    8
    ;; float64 _RTK_gps_UTM_z
    8
    ;; float64 _RTK_linear_ENU_vx
    8
    ;; float64 _RTK_linear_ENU_vy
    8
    ;; float64 _RTK_linear_ENU_vz
    8
    ;; float64 _RTK_linear_vx
    8
    ;; float64 _RTK_linear_vy
    8
    ;; float64 _RTK_linear_vz
    8
    ;; float64 _RTK_angular_vx
    8
    ;; float64 _RTK_angular_vy
    8
    ;; float64 _RTK_angular_vz
    8
    ;; float64 _x
    8
    ;; float64 _y
    8
    ;; float64 _z
    8
    ;; float64 _speed_x
    8
    ;; float64 _speed_y
    8
    ;; float64 _speed_z
    8
    ;; float64 _acc_x
    8
    ;; float64 _acc_y
    8
    ;; float64 _acc_z
    8
    ;; float64 _heading
    8
    ;; float64 _pitch
    8
    ;; float64 _roll
    8
    ;; float64 _yaw_rate
    8
    ;; float64 _size_x
    8
    ;; float64 _size_y
    8
    ;; float64 _size_z
    8
    ;; float64 _wheelbase
    8
    ;; int16 _gear_pos
    2
    ;; bool _by_wire_enabled
    1
    ;; int16 _vehicle_mode
    2
    ;; float64 _throttle_cmd
    8
    ;; float64 _throttle_input
    8
    ;; float64 _throttle_state
    8
    ;; bool _throttle_enabled
    1
    ;; bool _throttle_override
    1
    ;; bool _throttle_driver
    1
    ;; bool _throttle_timeout
    1
    ;; float64 _brake_cmd
    8
    ;; float64 _brake_input
    8
    ;; float64 _brake_state
    8
    ;; float64 _brake_torq_cmd
    8
    ;; float64 _brake_torq_input
    8
    ;; float64 _brake_torq_state
    8
    ;; bool _brake_boo_output
    1
    ;; bool _brake_enabled
    1
    ;; bool _brake_override
    1
    ;; bool _brake_driver
    1
    ;; bool _brake_timeout
    1
    ;; float64 _steer_cmd
    8
    ;; float64 _steer_state_front_wheel
    8
    ;; float64 _steer_torque
    8
    ;; bool _steer_enabled
    1
    ;; bool _steer_override
    1
    ;; bool _steer_timeout
    1
    ;; float64 _battery_volt
    8
    ;; float64 _battery_SOC
    8
    ;; int16 _engine_speed
    2
    ;; int16 _vehicle_bug_code
    2
    ;; int16 _vehicle_state_code
    2
    ))
  (:serialize
   (&optional strm)
   (let ((s (if strm strm
              (make-string-output-stream (send self :serialization-length)))))
     ;; float64 _timestamp
       (sys::poke _timestamp (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; int32 _id
       (write-long _id s)
     ;; string _name
       (write-long (length _name) s) (princ _name s)
     ;; int16 _vehicle_state
       (write-word _vehicle_state s)
     ;; int16 _type
       (write-word _type s)
     ;; string _RTK_state_string
       (write-long (length _RTK_state_string) s) (princ _RTK_state_string s)
     ;; int64 _RTK_seq_num
#+(or :alpha :irix6 :x86_64)
       (progn (sys::poke _RTK_seq_num (send s :buffer) (send s :count) :long) (incf (stream-count s) 8))
#-(or :alpha :irix6 :x86_64)
       (cond ((and (class _RTK_seq_num) (= (length (_RTK_seq_num . bv)) 2)) ;; bignum
              (write-long (ash (elt (_RTK_seq_num . bv) 0) 0) s)
              (write-long (ash (elt (_RTK_seq_num . bv) 1) -1) s))
             ((and (class _RTK_seq_num) (= (length (_RTK_seq_num . bv)) 1)) ;; big1
              (write-long (elt (_RTK_seq_num . bv) 0) s)
              (write-long (if (>= _RTK_seq_num 0) 0 #xffffffff) s))
             (t                                         ;; integer
              (write-long _RTK_seq_num s)(write-long (if (>= _RTK_seq_num 0) 0 #xffffffff) s)))
     ;; int64 _RTK_timestamp_sec
#+(or :alpha :irix6 :x86_64)
       (progn (sys::poke _RTK_timestamp_sec (send s :buffer) (send s :count) :long) (incf (stream-count s) 8))
#-(or :alpha :irix6 :x86_64)
       (cond ((and (class _RTK_timestamp_sec) (= (length (_RTK_timestamp_sec . bv)) 2)) ;; bignum
              (write-long (ash (elt (_RTK_timestamp_sec . bv) 0) 0) s)
              (write-long (ash (elt (_RTK_timestamp_sec . bv) 1) -1) s))
             ((and (class _RTK_timestamp_sec) (= (length (_RTK_timestamp_sec . bv)) 1)) ;; big1
              (write-long (elt (_RTK_timestamp_sec . bv) 0) s)
              (write-long (if (>= _RTK_timestamp_sec 0) 0 #xffffffff) s))
             (t                                         ;; integer
              (write-long _RTK_timestamp_sec s)(write-long (if (>= _RTK_timestamp_sec 0) 0 #xffffffff) s)))
     ;; int64 _RTK_timestamp_nsec
#+(or :alpha :irix6 :x86_64)
       (progn (sys::poke _RTK_timestamp_nsec (send s :buffer) (send s :count) :long) (incf (stream-count s) 8))
#-(or :alpha :irix6 :x86_64)
       (cond ((and (class _RTK_timestamp_nsec) (= (length (_RTK_timestamp_nsec . bv)) 2)) ;; bignum
              (write-long (ash (elt (_RTK_timestamp_nsec . bv) 0) 0) s)
              (write-long (ash (elt (_RTK_timestamp_nsec . bv) 1) -1) s))
             ((and (class _RTK_timestamp_nsec) (= (length (_RTK_timestamp_nsec . bv)) 1)) ;; big1
              (write-long (elt (_RTK_timestamp_nsec . bv) 0) s)
              (write-long (if (>= _RTK_timestamp_nsec 0) 0 #xffffffff) s))
             (t                                         ;; integer
              (write-long _RTK_timestamp_nsec s)(write-long (if (>= _RTK_timestamp_nsec 0) 0 #xffffffff) s)))
     ;; int16 _RTK_gps_status
       (write-word _RTK_gps_status s)
     ;; int16 _RTK_gps_service
       (write-word _RTK_gps_service s)
     ;; float64 _RTK_gps_longitude
       (sys::poke _RTK_gps_longitude (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _RTK_gps_latitude
       (sys::poke _RTK_gps_latitude (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _RTK_gps_altitude
       (sys::poke _RTK_gps_altitude (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _RTK_gps_UTM_x
       (sys::poke _RTK_gps_UTM_x (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _RTK_gps_UTM_y
       (sys::poke _RTK_gps_UTM_y (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _RTK_gps_UTM_z
       (sys::poke _RTK_gps_UTM_z (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _RTK_linear_ENU_vx
       (sys::poke _RTK_linear_ENU_vx (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _RTK_linear_ENU_vy
       (sys::poke _RTK_linear_ENU_vy (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _RTK_linear_ENU_vz
       (sys::poke _RTK_linear_ENU_vz (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _RTK_linear_vx
       (sys::poke _RTK_linear_vx (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _RTK_linear_vy
       (sys::poke _RTK_linear_vy (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _RTK_linear_vz
       (sys::poke _RTK_linear_vz (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _RTK_angular_vx
       (sys::poke _RTK_angular_vx (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _RTK_angular_vy
       (sys::poke _RTK_angular_vy (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _RTK_angular_vz
       (sys::poke _RTK_angular_vz (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _x
       (sys::poke _x (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _y
       (sys::poke _y (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _z
       (sys::poke _z (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _speed_x
       (sys::poke _speed_x (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _speed_y
       (sys::poke _speed_y (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _speed_z
       (sys::poke _speed_z (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _acc_x
       (sys::poke _acc_x (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _acc_y
       (sys::poke _acc_y (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _acc_z
       (sys::poke _acc_z (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _heading
       (sys::poke _heading (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _pitch
       (sys::poke _pitch (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _roll
       (sys::poke _roll (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _yaw_rate
       (sys::poke _yaw_rate (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _size_x
       (sys::poke _size_x (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _size_y
       (sys::poke _size_y (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _size_z
       (sys::poke _size_z (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _wheelbase
       (sys::poke _wheelbase (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; int16 _gear_pos
       (write-word _gear_pos s)
     ;; bool _by_wire_enabled
       (if _by_wire_enabled (write-byte -1 s) (write-byte 0 s))
     ;; int16 _vehicle_mode
       (write-word _vehicle_mode s)
     ;; float64 _throttle_cmd
       (sys::poke _throttle_cmd (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _throttle_input
       (sys::poke _throttle_input (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _throttle_state
       (sys::poke _throttle_state (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; bool _throttle_enabled
       (if _throttle_enabled (write-byte -1 s) (write-byte 0 s))
     ;; bool _throttle_override
       (if _throttle_override (write-byte -1 s) (write-byte 0 s))
     ;; bool _throttle_driver
       (if _throttle_driver (write-byte -1 s) (write-byte 0 s))
     ;; bool _throttle_timeout
       (if _throttle_timeout (write-byte -1 s) (write-byte 0 s))
     ;; float64 _brake_cmd
       (sys::poke _brake_cmd (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _brake_input
       (sys::poke _brake_input (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _brake_state
       (sys::poke _brake_state (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _brake_torq_cmd
       (sys::poke _brake_torq_cmd (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _brake_torq_input
       (sys::poke _brake_torq_input (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _brake_torq_state
       (sys::poke _brake_torq_state (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; bool _brake_boo_output
       (if _brake_boo_output (write-byte -1 s) (write-byte 0 s))
     ;; bool _brake_enabled
       (if _brake_enabled (write-byte -1 s) (write-byte 0 s))
     ;; bool _brake_override
       (if _brake_override (write-byte -1 s) (write-byte 0 s))
     ;; bool _brake_driver
       (if _brake_driver (write-byte -1 s) (write-byte 0 s))
     ;; bool _brake_timeout
       (if _brake_timeout (write-byte -1 s) (write-byte 0 s))
     ;; float64 _steer_cmd
       (sys::poke _steer_cmd (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _steer_state_front_wheel
       (sys::poke _steer_state_front_wheel (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _steer_torque
       (sys::poke _steer_torque (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; bool _steer_enabled
       (if _steer_enabled (write-byte -1 s) (write-byte 0 s))
     ;; bool _steer_override
       (if _steer_override (write-byte -1 s) (write-byte 0 s))
     ;; bool _steer_timeout
       (if _steer_timeout (write-byte -1 s) (write-byte 0 s))
     ;; float64 _battery_volt
       (sys::poke _battery_volt (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; float64 _battery_SOC
       (sys::poke _battery_SOC (send s :buffer) (send s :count) :double) (incf (stream-count s) 8)
     ;; int16 _engine_speed
       (write-word _engine_speed s)
     ;; int16 _vehicle_bug_code
       (write-word _vehicle_bug_code s)
     ;; int16 _vehicle_state_code
       (write-word _vehicle_state_code s)
     ;;
     (if (null strm) (get-output-stream-string s))))
  (:deserialize
   (buf &optional (ptr- 0))
   ;; float64 _timestamp
     (setq _timestamp (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; int32 _id
     (setq _id (sys::peek buf ptr- :integer)) (incf ptr- 4)
   ;; string _name
     (let (n) (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4) (setq _name (subseq buf ptr- (+ ptr- n))) (incf ptr- n))
   ;; int16 _vehicle_state
     (setq _vehicle_state (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; int16 _type
     (setq _type (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; string _RTK_state_string
     (let (n) (setq n (sys::peek buf ptr- :integer)) (incf ptr- 4) (setq _RTK_state_string (subseq buf ptr- (+ ptr- n))) (incf ptr- n))
   ;; int64 _RTK_seq_num
#+(or :alpha :irix6 :x86_64)
      (setf _RTK_seq_num (prog1 (sys::peek buf ptr- :long) (incf ptr- 8)))
#-(or :alpha :irix6 :x86_64)
      (setf _RTK_seq_num (let ((b0 (prog1 (sys::peek buf ptr- :integer) (incf ptr- 4)))
                  (b1 (prog1 (sys::peek buf ptr- :integer) (incf ptr- 4))))
              (cond ((= b1 -1) b0)
                     ((and (= b1  0)
                           (<= lisp::most-negative-fixnum b0 lisp::most-positive-fixnum))
                      b0)
                    ((= b1  0) (make-instance bignum :size 1 :bv (integer-vector b0)))
                    (t (make-instance bignum :size 2 :bv (integer-vector b0 (ash b1 1)))))))
   ;; int64 _RTK_timestamp_sec
#+(or :alpha :irix6 :x86_64)
      (setf _RTK_timestamp_sec (prog1 (sys::peek buf ptr- :long) (incf ptr- 8)))
#-(or :alpha :irix6 :x86_64)
      (setf _RTK_timestamp_sec (let ((b0 (prog1 (sys::peek buf ptr- :integer) (incf ptr- 4)))
                  (b1 (prog1 (sys::peek buf ptr- :integer) (incf ptr- 4))))
              (cond ((= b1 -1) b0)
                     ((and (= b1  0)
                           (<= lisp::most-negative-fixnum b0 lisp::most-positive-fixnum))
                      b0)
                    ((= b1  0) (make-instance bignum :size 1 :bv (integer-vector b0)))
                    (t (make-instance bignum :size 2 :bv (integer-vector b0 (ash b1 1)))))))
   ;; int64 _RTK_timestamp_nsec
#+(or :alpha :irix6 :x86_64)
      (setf _RTK_timestamp_nsec (prog1 (sys::peek buf ptr- :long) (incf ptr- 8)))
#-(or :alpha :irix6 :x86_64)
      (setf _RTK_timestamp_nsec (let ((b0 (prog1 (sys::peek buf ptr- :integer) (incf ptr- 4)))
                  (b1 (prog1 (sys::peek buf ptr- :integer) (incf ptr- 4))))
              (cond ((= b1 -1) b0)
                     ((and (= b1  0)
                           (<= lisp::most-negative-fixnum b0 lisp::most-positive-fixnum))
                      b0)
                    ((= b1  0) (make-instance bignum :size 1 :bv (integer-vector b0)))
                    (t (make-instance bignum :size 2 :bv (integer-vector b0 (ash b1 1)))))))
   ;; int16 _RTK_gps_status
     (setq _RTK_gps_status (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; int16 _RTK_gps_service
     (setq _RTK_gps_service (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; float64 _RTK_gps_longitude
     (setq _RTK_gps_longitude (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _RTK_gps_latitude
     (setq _RTK_gps_latitude (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _RTK_gps_altitude
     (setq _RTK_gps_altitude (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _RTK_gps_UTM_x
     (setq _RTK_gps_UTM_x (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _RTK_gps_UTM_y
     (setq _RTK_gps_UTM_y (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _RTK_gps_UTM_z
     (setq _RTK_gps_UTM_z (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _RTK_linear_ENU_vx
     (setq _RTK_linear_ENU_vx (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _RTK_linear_ENU_vy
     (setq _RTK_linear_ENU_vy (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _RTK_linear_ENU_vz
     (setq _RTK_linear_ENU_vz (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _RTK_linear_vx
     (setq _RTK_linear_vx (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _RTK_linear_vy
     (setq _RTK_linear_vy (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _RTK_linear_vz
     (setq _RTK_linear_vz (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _RTK_angular_vx
     (setq _RTK_angular_vx (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _RTK_angular_vy
     (setq _RTK_angular_vy (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _RTK_angular_vz
     (setq _RTK_angular_vz (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _x
     (setq _x (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _y
     (setq _y (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _z
     (setq _z (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _speed_x
     (setq _speed_x (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _speed_y
     (setq _speed_y (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _speed_z
     (setq _speed_z (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _acc_x
     (setq _acc_x (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _acc_y
     (setq _acc_y (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _acc_z
     (setq _acc_z (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _heading
     (setq _heading (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _pitch
     (setq _pitch (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _roll
     (setq _roll (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _yaw_rate
     (setq _yaw_rate (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _size_x
     (setq _size_x (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _size_y
     (setq _size_y (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _size_z
     (setq _size_z (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _wheelbase
     (setq _wheelbase (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; int16 _gear_pos
     (setq _gear_pos (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; bool _by_wire_enabled
     (setq _by_wire_enabled (not (= 0 (sys::peek buf ptr- :char)))) (incf ptr- 1)
   ;; int16 _vehicle_mode
     (setq _vehicle_mode (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; float64 _throttle_cmd
     (setq _throttle_cmd (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _throttle_input
     (setq _throttle_input (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _throttle_state
     (setq _throttle_state (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; bool _throttle_enabled
     (setq _throttle_enabled (not (= 0 (sys::peek buf ptr- :char)))) (incf ptr- 1)
   ;; bool _throttle_override
     (setq _throttle_override (not (= 0 (sys::peek buf ptr- :char)))) (incf ptr- 1)
   ;; bool _throttle_driver
     (setq _throttle_driver (not (= 0 (sys::peek buf ptr- :char)))) (incf ptr- 1)
   ;; bool _throttle_timeout
     (setq _throttle_timeout (not (= 0 (sys::peek buf ptr- :char)))) (incf ptr- 1)
   ;; float64 _brake_cmd
     (setq _brake_cmd (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _brake_input
     (setq _brake_input (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _brake_state
     (setq _brake_state (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _brake_torq_cmd
     (setq _brake_torq_cmd (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _brake_torq_input
     (setq _brake_torq_input (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _brake_torq_state
     (setq _brake_torq_state (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; bool _brake_boo_output
     (setq _brake_boo_output (not (= 0 (sys::peek buf ptr- :char)))) (incf ptr- 1)
   ;; bool _brake_enabled
     (setq _brake_enabled (not (= 0 (sys::peek buf ptr- :char)))) (incf ptr- 1)
   ;; bool _brake_override
     (setq _brake_override (not (= 0 (sys::peek buf ptr- :char)))) (incf ptr- 1)
   ;; bool _brake_driver
     (setq _brake_driver (not (= 0 (sys::peek buf ptr- :char)))) (incf ptr- 1)
   ;; bool _brake_timeout
     (setq _brake_timeout (not (= 0 (sys::peek buf ptr- :char)))) (incf ptr- 1)
   ;; float64 _steer_cmd
     (setq _steer_cmd (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _steer_state_front_wheel
     (setq _steer_state_front_wheel (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _steer_torque
     (setq _steer_torque (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; bool _steer_enabled
     (setq _steer_enabled (not (= 0 (sys::peek buf ptr- :char)))) (incf ptr- 1)
   ;; bool _steer_override
     (setq _steer_override (not (= 0 (sys::peek buf ptr- :char)))) (incf ptr- 1)
   ;; bool _steer_timeout
     (setq _steer_timeout (not (= 0 (sys::peek buf ptr- :char)))) (incf ptr- 1)
   ;; float64 _battery_volt
     (setq _battery_volt (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; float64 _battery_SOC
     (setq _battery_SOC (sys::peek buf ptr- :double)) (incf ptr- 8)
   ;; int16 _engine_speed
     (setq _engine_speed (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; int16 _vehicle_bug_code
     (setq _vehicle_bug_code (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;; int16 _vehicle_state_code
     (setq _vehicle_state_code (sys::peek buf ptr- :short)) (incf ptr- 2)
   ;;
   self)
  )

(setf (get cav_msgs::VehicleState :md5sum-) "9bd3a4bb3c48f14d68f55c4dd2e4292a")
(setf (get cav_msgs::VehicleState :datatype-) "cav_msgs/VehicleState")
(setf (get cav_msgs::VehicleState :definition-)
      "## timestamp, ros time or utc time
float64 timestamp 

## task related
int32 	id
string  name
int16 	vehicle_state #0: normal 1: damage 2: low battery 
int16 	type
#发布自车71
##未知 0 坦克 10 装甲运兵车 11 轻型高机动平台12 小型无人战车 13 机器狗 14 保障车15
##YHS 17 LT 18 Lynx 19

## RTK state
string 	RTK_state_string
int64   RTK_seq_num
int64   RTK_timestamp_sec
int64   RTK_timestamp_nsec

int16   RTK_gps_status
int16   RTK_gps_service


## RTK position
float64 RTK_gps_longitude   #degree
float64 RTK_gps_latitude    #degree
float64 RTK_gps_altitude    #m

##position of c.g.
float64 RTK_gps_UTM_x       #meter
float64 RTK_gps_UTM_y       #meter
float64 RTK_gps_UTM_z       #meter


##RTK ENU speed, m/s, global coordinate system
float64 RTK_linear_ENU_vx
float64 RTK_linear_ENU_vy
float64 RTK_linear_ENU_vz

##RTK local coordinate system, m/s
float64 RTK_linear_vx
float64 RTK_linear_vy
float64 RTK_linear_vz

##RTK local angular speed, m/s
float64 RTK_angular_vx
float64 RTK_angular_vy
float64 RTK_angular_vz

##key vehicle state
##position, meter
float64 x
float64 y
float64 z

##RTK local coordinate system, m/s
float64 speed_x
float64 speed_y
float64 speed_z

## acceleration m/s2
float64 acc_x
float64 acc_y
float64 acc_z

## rad
float64 heading         #yaw, rad
float64 pitch           #rad
float64 roll            #rad
float64 yaw_rate        #rad/s

##vehicle size
float64 size_x          #meter
float64 size_y          #meter
float64 size_z          #meter
float64 wheelbase       #meter

##gear position
#GEAR_NONE       (0)
#GEAR_PARK       (1)
#GEAR_REVERSE    (2)
#GEAR_NEUTRAL    (3)
#GEAR_DRIVE      (4)
#GEAR_LOW        (5)
int16   gear_pos


#by-wire, true or false
bool    by_wire_enabled
int16   vehicle_mode         # vehicle mode feedback 0：remote mode, 1：self driving mode


## vehicle state from CAN bus
float64 throttle_cmd
float64 throttle_input
float64 throttle_state      #percentage %
bool    throttle_enabled
bool    throttle_override
bool    throttle_driver
bool    throttle_timeout

float64 brake_cmd
float64 brake_input
float64 brake_state         #percentage %
float64 brake_torq_cmd
float64 brake_torq_input
float64 brake_torq_state
bool    brake_boo_output
bool    brake_enabled
bool    brake_override
bool    brake_driver
bool    brake_timeout

float64 steer_cmd
float64 steer_state_front_wheel # rad
float64 steer_torque
bool    steer_enabled
bool    steer_override
bool    steer_timeout


## Batter and Engine
float64 battery_volt        # V
float64 battery_SOC         # %
int16 engine_speed          # r/min

int16 vehicle_bug_code
int16 vehicle_state_code 


")



(provide :cav_msgs/VehicleState "9bd3a4bb3c48f14d68f55c4dd2e4292a")


