// Auto-generated. Do not edit!

// (in-package cav_msgs.msg)


"use strict";

const _serializer = _ros_msg_utils.Serialize;
const _arraySerializer = _serializer.Array;
const _deserializer = _ros_msg_utils.Deserialize;
const _arrayDeserializer = _deserializer.Array;
const _finder = _ros_msg_utils.Find;
const _getByteLength = _ros_msg_utils.getByteLength;

//-----------------------------------------------------------

class VehicleState {
  constructor(initObj={}) {
    if (initObj === null) {
      // initObj === null is a special case for deserialization where we don't initialize fields
      this.timestamp = null;
      this.id = null;
      this.name = null;
      this.vehicle_state = null;
      this.type = null;
      this.RTK_state_string = null;
      this.RTK_seq_num = null;
      this.RTK_timestamp_sec = null;
      this.RTK_timestamp_nsec = null;
      this.RTK_gps_status = null;
      this.RTK_gps_service = null;
      this.RTK_gps_longitude = null;
      this.RTK_gps_latitude = null;
      this.RTK_gps_altitude = null;
      this.RTK_gps_UTM_x = null;
      this.RTK_gps_UTM_y = null;
      this.RTK_gps_UTM_z = null;
      this.RTK_linear_ENU_vx = null;
      this.RTK_linear_ENU_vy = null;
      this.RTK_linear_ENU_vz = null;
      this.RTK_linear_vx = null;
      this.RTK_linear_vy = null;
      this.RTK_linear_vz = null;
      this.RTK_angular_vx = null;
      this.RTK_angular_vy = null;
      this.RTK_angular_vz = null;
      this.x = null;
      this.y = null;
      this.z = null;
      this.speed_x = null;
      this.speed_y = null;
      this.speed_z = null;
      this.acc_x = null;
      this.acc_y = null;
      this.acc_z = null;
      this.heading = null;
      this.pitch = null;
      this.roll = null;
      this.yaw_rate = null;
      this.size_x = null;
      this.size_y = null;
      this.size_z = null;
      this.wheelbase = null;
      this.gear_pos = null;
      this.by_wire_enabled = null;
      this.vehicle_mode = null;
      this.throttle_cmd = null;
      this.throttle_input = null;
      this.throttle_state = null;
      this.throttle_enabled = null;
      this.throttle_override = null;
      this.throttle_driver = null;
      this.throttle_timeout = null;
      this.brake_cmd = null;
      this.brake_input = null;
      this.brake_state = null;
      this.brake_torq_cmd = null;
      this.brake_torq_input = null;
      this.brake_torq_state = null;
      this.brake_boo_output = null;
      this.brake_enabled = null;
      this.brake_override = null;
      this.brake_driver = null;
      this.brake_timeout = null;
      this.steer_cmd = null;
      this.steer_state_front_wheel = null;
      this.steer_torque = null;
      this.steer_enabled = null;
      this.steer_override = null;
      this.steer_timeout = null;
      this.battery_volt = null;
      this.battery_SOC = null;
      this.engine_speed = null;
      this.vehicle_bug_code = null;
      this.vehicle_state_code = null;
    }
    else {
      if (initObj.hasOwnProperty('timestamp')) {
        this.timestamp = initObj.timestamp
      }
      else {
        this.timestamp = 0.0;
      }
      if (initObj.hasOwnProperty('id')) {
        this.id = initObj.id
      }
      else {
        this.id = 0;
      }
      if (initObj.hasOwnProperty('name')) {
        this.name = initObj.name
      }
      else {
        this.name = '';
      }
      if (initObj.hasOwnProperty('vehicle_state')) {
        this.vehicle_state = initObj.vehicle_state
      }
      else {
        this.vehicle_state = 0;
      }
      if (initObj.hasOwnProperty('type')) {
        this.type = initObj.type
      }
      else {
        this.type = 0;
      }
      if (initObj.hasOwnProperty('RTK_state_string')) {
        this.RTK_state_string = initObj.RTK_state_string
      }
      else {
        this.RTK_state_string = '';
      }
      if (initObj.hasOwnProperty('RTK_seq_num')) {
        this.RTK_seq_num = initObj.RTK_seq_num
      }
      else {
        this.RTK_seq_num = 0;
      }
      if (initObj.hasOwnProperty('RTK_timestamp_sec')) {
        this.RTK_timestamp_sec = initObj.RTK_timestamp_sec
      }
      else {
        this.RTK_timestamp_sec = 0;
      }
      if (initObj.hasOwnProperty('RTK_timestamp_nsec')) {
        this.RTK_timestamp_nsec = initObj.RTK_timestamp_nsec
      }
      else {
        this.RTK_timestamp_nsec = 0;
      }
      if (initObj.hasOwnProperty('RTK_gps_status')) {
        this.RTK_gps_status = initObj.RTK_gps_status
      }
      else {
        this.RTK_gps_status = 0;
      }
      if (initObj.hasOwnProperty('RTK_gps_service')) {
        this.RTK_gps_service = initObj.RTK_gps_service
      }
      else {
        this.RTK_gps_service = 0;
      }
      if (initObj.hasOwnProperty('RTK_gps_longitude')) {
        this.RTK_gps_longitude = initObj.RTK_gps_longitude
      }
      else {
        this.RTK_gps_longitude = 0.0;
      }
      if (initObj.hasOwnProperty('RTK_gps_latitude')) {
        this.RTK_gps_latitude = initObj.RTK_gps_latitude
      }
      else {
        this.RTK_gps_latitude = 0.0;
      }
      if (initObj.hasOwnProperty('RTK_gps_altitude')) {
        this.RTK_gps_altitude = initObj.RTK_gps_altitude
      }
      else {
        this.RTK_gps_altitude = 0.0;
      }
      if (initObj.hasOwnProperty('RTK_gps_UTM_x')) {
        this.RTK_gps_UTM_x = initObj.RTK_gps_UTM_x
      }
      else {
        this.RTK_gps_UTM_x = 0.0;
      }
      if (initObj.hasOwnProperty('RTK_gps_UTM_y')) {
        this.RTK_gps_UTM_y = initObj.RTK_gps_UTM_y
      }
      else {
        this.RTK_gps_UTM_y = 0.0;
      }
      if (initObj.hasOwnProperty('RTK_gps_UTM_z')) {
        this.RTK_gps_UTM_z = initObj.RTK_gps_UTM_z
      }
      else {
        this.RTK_gps_UTM_z = 0.0;
      }
      if (initObj.hasOwnProperty('RTK_linear_ENU_vx')) {
        this.RTK_linear_ENU_vx = initObj.RTK_linear_ENU_vx
      }
      else {
        this.RTK_linear_ENU_vx = 0.0;
      }
      if (initObj.hasOwnProperty('RTK_linear_ENU_vy')) {
        this.RTK_linear_ENU_vy = initObj.RTK_linear_ENU_vy
      }
      else {
        this.RTK_linear_ENU_vy = 0.0;
      }
      if (initObj.hasOwnProperty('RTK_linear_ENU_vz')) {
        this.RTK_linear_ENU_vz = initObj.RTK_linear_ENU_vz
      }
      else {
        this.RTK_linear_ENU_vz = 0.0;
      }
      if (initObj.hasOwnProperty('RTK_linear_vx')) {
        this.RTK_linear_vx = initObj.RTK_linear_vx
      }
      else {
        this.RTK_linear_vx = 0.0;
      }
      if (initObj.hasOwnProperty('RTK_linear_vy')) {
        this.RTK_linear_vy = initObj.RTK_linear_vy
      }
      else {
        this.RTK_linear_vy = 0.0;
      }
      if (initObj.hasOwnProperty('RTK_linear_vz')) {
        this.RTK_linear_vz = initObj.RTK_linear_vz
      }
      else {
        this.RTK_linear_vz = 0.0;
      }
      if (initObj.hasOwnProperty('RTK_angular_vx')) {
        this.RTK_angular_vx = initObj.RTK_angular_vx
      }
      else {
        this.RTK_angular_vx = 0.0;
      }
      if (initObj.hasOwnProperty('RTK_angular_vy')) {
        this.RTK_angular_vy = initObj.RTK_angular_vy
      }
      else {
        this.RTK_angular_vy = 0.0;
      }
      if (initObj.hasOwnProperty('RTK_angular_vz')) {
        this.RTK_angular_vz = initObj.RTK_angular_vz
      }
      else {
        this.RTK_angular_vz = 0.0;
      }
      if (initObj.hasOwnProperty('x')) {
        this.x = initObj.x
      }
      else {
        this.x = 0.0;
      }
      if (initObj.hasOwnProperty('y')) {
        this.y = initObj.y
      }
      else {
        this.y = 0.0;
      }
      if (initObj.hasOwnProperty('z')) {
        this.z = initObj.z
      }
      else {
        this.z = 0.0;
      }
      if (initObj.hasOwnProperty('speed_x')) {
        this.speed_x = initObj.speed_x
      }
      else {
        this.speed_x = 0.0;
      }
      if (initObj.hasOwnProperty('speed_y')) {
        this.speed_y = initObj.speed_y
      }
      else {
        this.speed_y = 0.0;
      }
      if (initObj.hasOwnProperty('speed_z')) {
        this.speed_z = initObj.speed_z
      }
      else {
        this.speed_z = 0.0;
      }
      if (initObj.hasOwnProperty('acc_x')) {
        this.acc_x = initObj.acc_x
      }
      else {
        this.acc_x = 0.0;
      }
      if (initObj.hasOwnProperty('acc_y')) {
        this.acc_y = initObj.acc_y
      }
      else {
        this.acc_y = 0.0;
      }
      if (initObj.hasOwnProperty('acc_z')) {
        this.acc_z = initObj.acc_z
      }
      else {
        this.acc_z = 0.0;
      }
      if (initObj.hasOwnProperty('heading')) {
        this.heading = initObj.heading
      }
      else {
        this.heading = 0.0;
      }
      if (initObj.hasOwnProperty('pitch')) {
        this.pitch = initObj.pitch
      }
      else {
        this.pitch = 0.0;
      }
      if (initObj.hasOwnProperty('roll')) {
        this.roll = initObj.roll
      }
      else {
        this.roll = 0.0;
      }
      if (initObj.hasOwnProperty('yaw_rate')) {
        this.yaw_rate = initObj.yaw_rate
      }
      else {
        this.yaw_rate = 0.0;
      }
      if (initObj.hasOwnProperty('size_x')) {
        this.size_x = initObj.size_x
      }
      else {
        this.size_x = 0.0;
      }
      if (initObj.hasOwnProperty('size_y')) {
        this.size_y = initObj.size_y
      }
      else {
        this.size_y = 0.0;
      }
      if (initObj.hasOwnProperty('size_z')) {
        this.size_z = initObj.size_z
      }
      else {
        this.size_z = 0.0;
      }
      if (initObj.hasOwnProperty('wheelbase')) {
        this.wheelbase = initObj.wheelbase
      }
      else {
        this.wheelbase = 0.0;
      }
      if (initObj.hasOwnProperty('gear_pos')) {
        this.gear_pos = initObj.gear_pos
      }
      else {
        this.gear_pos = 0;
      }
      if (initObj.hasOwnProperty('by_wire_enabled')) {
        this.by_wire_enabled = initObj.by_wire_enabled
      }
      else {
        this.by_wire_enabled = false;
      }
      if (initObj.hasOwnProperty('vehicle_mode')) {
        this.vehicle_mode = initObj.vehicle_mode
      }
      else {
        this.vehicle_mode = 0;
      }
      if (initObj.hasOwnProperty('throttle_cmd')) {
        this.throttle_cmd = initObj.throttle_cmd
      }
      else {
        this.throttle_cmd = 0.0;
      }
      if (initObj.hasOwnProperty('throttle_input')) {
        this.throttle_input = initObj.throttle_input
      }
      else {
        this.throttle_input = 0.0;
      }
      if (initObj.hasOwnProperty('throttle_state')) {
        this.throttle_state = initObj.throttle_state
      }
      else {
        this.throttle_state = 0.0;
      }
      if (initObj.hasOwnProperty('throttle_enabled')) {
        this.throttle_enabled = initObj.throttle_enabled
      }
      else {
        this.throttle_enabled = false;
      }
      if (initObj.hasOwnProperty('throttle_override')) {
        this.throttle_override = initObj.throttle_override
      }
      else {
        this.throttle_override = false;
      }
      if (initObj.hasOwnProperty('throttle_driver')) {
        this.throttle_driver = initObj.throttle_driver
      }
      else {
        this.throttle_driver = false;
      }
      if (initObj.hasOwnProperty('throttle_timeout')) {
        this.throttle_timeout = initObj.throttle_timeout
      }
      else {
        this.throttle_timeout = false;
      }
      if (initObj.hasOwnProperty('brake_cmd')) {
        this.brake_cmd = initObj.brake_cmd
      }
      else {
        this.brake_cmd = 0.0;
      }
      if (initObj.hasOwnProperty('brake_input')) {
        this.brake_input = initObj.brake_input
      }
      else {
        this.brake_input = 0.0;
      }
      if (initObj.hasOwnProperty('brake_state')) {
        this.brake_state = initObj.brake_state
      }
      else {
        this.brake_state = 0.0;
      }
      if (initObj.hasOwnProperty('brake_torq_cmd')) {
        this.brake_torq_cmd = initObj.brake_torq_cmd
      }
      else {
        this.brake_torq_cmd = 0.0;
      }
      if (initObj.hasOwnProperty('brake_torq_input')) {
        this.brake_torq_input = initObj.brake_torq_input
      }
      else {
        this.brake_torq_input = 0.0;
      }
      if (initObj.hasOwnProperty('brake_torq_state')) {
        this.brake_torq_state = initObj.brake_torq_state
      }
      else {
        this.brake_torq_state = 0.0;
      }
      if (initObj.hasOwnProperty('brake_boo_output')) {
        this.brake_boo_output = initObj.brake_boo_output
      }
      else {
        this.brake_boo_output = false;
      }
      if (initObj.hasOwnProperty('brake_enabled')) {
        this.brake_enabled = initObj.brake_enabled
      }
      else {
        this.brake_enabled = false;
      }
      if (initObj.hasOwnProperty('brake_override')) {
        this.brake_override = initObj.brake_override
      }
      else {
        this.brake_override = false;
      }
      if (initObj.hasOwnProperty('brake_driver')) {
        this.brake_driver = initObj.brake_driver
      }
      else {
        this.brake_driver = false;
      }
      if (initObj.hasOwnProperty('brake_timeout')) {
        this.brake_timeout = initObj.brake_timeout
      }
      else {
        this.brake_timeout = false;
      }
      if (initObj.hasOwnProperty('steer_cmd')) {
        this.steer_cmd = initObj.steer_cmd
      }
      else {
        this.steer_cmd = 0.0;
      }
      if (initObj.hasOwnProperty('steer_state_front_wheel')) {
        this.steer_state_front_wheel = initObj.steer_state_front_wheel
      }
      else {
        this.steer_state_front_wheel = 0.0;
      }
      if (initObj.hasOwnProperty('steer_torque')) {
        this.steer_torque = initObj.steer_torque
      }
      else {
        this.steer_torque = 0.0;
      }
      if (initObj.hasOwnProperty('steer_enabled')) {
        this.steer_enabled = initObj.steer_enabled
      }
      else {
        this.steer_enabled = false;
      }
      if (initObj.hasOwnProperty('steer_override')) {
        this.steer_override = initObj.steer_override
      }
      else {
        this.steer_override = false;
      }
      if (initObj.hasOwnProperty('steer_timeout')) {
        this.steer_timeout = initObj.steer_timeout
      }
      else {
        this.steer_timeout = false;
      }
      if (initObj.hasOwnProperty('battery_volt')) {
        this.battery_volt = initObj.battery_volt
      }
      else {
        this.battery_volt = 0.0;
      }
      if (initObj.hasOwnProperty('battery_SOC')) {
        this.battery_SOC = initObj.battery_SOC
      }
      else {
        this.battery_SOC = 0.0;
      }
      if (initObj.hasOwnProperty('engine_speed')) {
        this.engine_speed = initObj.engine_speed
      }
      else {
        this.engine_speed = 0;
      }
      if (initObj.hasOwnProperty('vehicle_bug_code')) {
        this.vehicle_bug_code = initObj.vehicle_bug_code
      }
      else {
        this.vehicle_bug_code = 0;
      }
      if (initObj.hasOwnProperty('vehicle_state_code')) {
        this.vehicle_state_code = initObj.vehicle_state_code
      }
      else {
        this.vehicle_state_code = 0;
      }
    }
  }

  static serialize(obj, buffer, bufferOffset) {
    // Serializes a message object of type VehicleState
    // Serialize message field [timestamp]
    bufferOffset = _serializer.float64(obj.timestamp, buffer, bufferOffset);
    // Serialize message field [id]
    bufferOffset = _serializer.int32(obj.id, buffer, bufferOffset);
    // Serialize message field [name]
    bufferOffset = _serializer.string(obj.name, buffer, bufferOffset);
    // Serialize message field [vehicle_state]
    bufferOffset = _serializer.int16(obj.vehicle_state, buffer, bufferOffset);
    // Serialize message field [type]
    bufferOffset = _serializer.int16(obj.type, buffer, bufferOffset);
    // Serialize message field [RTK_state_string]
    bufferOffset = _serializer.string(obj.RTK_state_string, buffer, bufferOffset);
    // Serialize message field [RTK_seq_num]
    bufferOffset = _serializer.int64(obj.RTK_seq_num, buffer, bufferOffset);
    // Serialize message field [RTK_timestamp_sec]
    bufferOffset = _serializer.int64(obj.RTK_timestamp_sec, buffer, bufferOffset);
    // Serialize message field [RTK_timestamp_nsec]
    bufferOffset = _serializer.int64(obj.RTK_timestamp_nsec, buffer, bufferOffset);
    // Serialize message field [RTK_gps_status]
    bufferOffset = _serializer.int16(obj.RTK_gps_status, buffer, bufferOffset);
    // Serialize message field [RTK_gps_service]
    bufferOffset = _serializer.int16(obj.RTK_gps_service, buffer, bufferOffset);
    // Serialize message field [RTK_gps_longitude]
    bufferOffset = _serializer.float64(obj.RTK_gps_longitude, buffer, bufferOffset);
    // Serialize message field [RTK_gps_latitude]
    bufferOffset = _serializer.float64(obj.RTK_gps_latitude, buffer, bufferOffset);
    // Serialize message field [RTK_gps_altitude]
    bufferOffset = _serializer.float64(obj.RTK_gps_altitude, buffer, bufferOffset);
    // Serialize message field [RTK_gps_UTM_x]
    bufferOffset = _serializer.float64(obj.RTK_gps_UTM_x, buffer, bufferOffset);
    // Serialize message field [RTK_gps_UTM_y]
    bufferOffset = _serializer.float64(obj.RTK_gps_UTM_y, buffer, bufferOffset);
    // Serialize message field [RTK_gps_UTM_z]
    bufferOffset = _serializer.float64(obj.RTK_gps_UTM_z, buffer, bufferOffset);
    // Serialize message field [RTK_linear_ENU_vx]
    bufferOffset = _serializer.float64(obj.RTK_linear_ENU_vx, buffer, bufferOffset);
    // Serialize message field [RTK_linear_ENU_vy]
    bufferOffset = _serializer.float64(obj.RTK_linear_ENU_vy, buffer, bufferOffset);
    // Serialize message field [RTK_linear_ENU_vz]
    bufferOffset = _serializer.float64(obj.RTK_linear_ENU_vz, buffer, bufferOffset);
    // Serialize message field [RTK_linear_vx]
    bufferOffset = _serializer.float64(obj.RTK_linear_vx, buffer, bufferOffset);
    // Serialize message field [RTK_linear_vy]
    bufferOffset = _serializer.float64(obj.RTK_linear_vy, buffer, bufferOffset);
    // Serialize message field [RTK_linear_vz]
    bufferOffset = _serializer.float64(obj.RTK_linear_vz, buffer, bufferOffset);
    // Serialize message field [RTK_angular_vx]
    bufferOffset = _serializer.float64(obj.RTK_angular_vx, buffer, bufferOffset);
    // Serialize message field [RTK_angular_vy]
    bufferOffset = _serializer.float64(obj.RTK_angular_vy, buffer, bufferOffset);
    // Serialize message field [RTK_angular_vz]
    bufferOffset = _serializer.float64(obj.RTK_angular_vz, buffer, bufferOffset);
    // Serialize message field [x]
    bufferOffset = _serializer.float64(obj.x, buffer, bufferOffset);
    // Serialize message field [y]
    bufferOffset = _serializer.float64(obj.y, buffer, bufferOffset);
    // Serialize message field [z]
    bufferOffset = _serializer.float64(obj.z, buffer, bufferOffset);
    // Serialize message field [speed_x]
    bufferOffset = _serializer.float64(obj.speed_x, buffer, bufferOffset);
    // Serialize message field [speed_y]
    bufferOffset = _serializer.float64(obj.speed_y, buffer, bufferOffset);
    // Serialize message field [speed_z]
    bufferOffset = _serializer.float64(obj.speed_z, buffer, bufferOffset);
    // Serialize message field [acc_x]
    bufferOffset = _serializer.float64(obj.acc_x, buffer, bufferOffset);
    // Serialize message field [acc_y]
    bufferOffset = _serializer.float64(obj.acc_y, buffer, bufferOffset);
    // Serialize message field [acc_z]
    bufferOffset = _serializer.float64(obj.acc_z, buffer, bufferOffset);
    // Serialize message field [heading]
    bufferOffset = _serializer.float64(obj.heading, buffer, bufferOffset);
    // Serialize message field [pitch]
    bufferOffset = _serializer.float64(obj.pitch, buffer, bufferOffset);
    // Serialize message field [roll]
    bufferOffset = _serializer.float64(obj.roll, buffer, bufferOffset);
    // Serialize message field [yaw_rate]
    bufferOffset = _serializer.float64(obj.yaw_rate, buffer, bufferOffset);
    // Serialize message field [size_x]
    bufferOffset = _serializer.float64(obj.size_x, buffer, bufferOffset);
    // Serialize message field [size_y]
    bufferOffset = _serializer.float64(obj.size_y, buffer, bufferOffset);
    // Serialize message field [size_z]
    bufferOffset = _serializer.float64(obj.size_z, buffer, bufferOffset);
    // Serialize message field [wheelbase]
    bufferOffset = _serializer.float64(obj.wheelbase, buffer, bufferOffset);
    // Serialize message field [gear_pos]
    bufferOffset = _serializer.int16(obj.gear_pos, buffer, bufferOffset);
    // Serialize message field [by_wire_enabled]
    bufferOffset = _serializer.bool(obj.by_wire_enabled, buffer, bufferOffset);
    // Serialize message field [vehicle_mode]
    bufferOffset = _serializer.int16(obj.vehicle_mode, buffer, bufferOffset);
    // Serialize message field [throttle_cmd]
    bufferOffset = _serializer.float64(obj.throttle_cmd, buffer, bufferOffset);
    // Serialize message field [throttle_input]
    bufferOffset = _serializer.float64(obj.throttle_input, buffer, bufferOffset);
    // Serialize message field [throttle_state]
    bufferOffset = _serializer.float64(obj.throttle_state, buffer, bufferOffset);
    // Serialize message field [throttle_enabled]
    bufferOffset = _serializer.bool(obj.throttle_enabled, buffer, bufferOffset);
    // Serialize message field [throttle_override]
    bufferOffset = _serializer.bool(obj.throttle_override, buffer, bufferOffset);
    // Serialize message field [throttle_driver]
    bufferOffset = _serializer.bool(obj.throttle_driver, buffer, bufferOffset);
    // Serialize message field [throttle_timeout]
    bufferOffset = _serializer.bool(obj.throttle_timeout, buffer, bufferOffset);
    // Serialize message field [brake_cmd]
    bufferOffset = _serializer.float64(obj.brake_cmd, buffer, bufferOffset);
    // Serialize message field [brake_input]
    bufferOffset = _serializer.float64(obj.brake_input, buffer, bufferOffset);
    // Serialize message field [brake_state]
    bufferOffset = _serializer.float64(obj.brake_state, buffer, bufferOffset);
    // Serialize message field [brake_torq_cmd]
    bufferOffset = _serializer.float64(obj.brake_torq_cmd, buffer, bufferOffset);
    // Serialize message field [brake_torq_input]
    bufferOffset = _serializer.float64(obj.brake_torq_input, buffer, bufferOffset);
    // Serialize message field [brake_torq_state]
    bufferOffset = _serializer.float64(obj.brake_torq_state, buffer, bufferOffset);
    // Serialize message field [brake_boo_output]
    bufferOffset = _serializer.bool(obj.brake_boo_output, buffer, bufferOffset);
    // Serialize message field [brake_enabled]
    bufferOffset = _serializer.bool(obj.brake_enabled, buffer, bufferOffset);
    // Serialize message field [brake_override]
    bufferOffset = _serializer.bool(obj.brake_override, buffer, bufferOffset);
    // Serialize message field [brake_driver]
    bufferOffset = _serializer.bool(obj.brake_driver, buffer, bufferOffset);
    // Serialize message field [brake_timeout]
    bufferOffset = _serializer.bool(obj.brake_timeout, buffer, bufferOffset);
    // Serialize message field [steer_cmd]
    bufferOffset = _serializer.float64(obj.steer_cmd, buffer, bufferOffset);
    // Serialize message field [steer_state_front_wheel]
    bufferOffset = _serializer.float64(obj.steer_state_front_wheel, buffer, bufferOffset);
    // Serialize message field [steer_torque]
    bufferOffset = _serializer.float64(obj.steer_torque, buffer, bufferOffset);
    // Serialize message field [steer_enabled]
    bufferOffset = _serializer.bool(obj.steer_enabled, buffer, bufferOffset);
    // Serialize message field [steer_override]
    bufferOffset = _serializer.bool(obj.steer_override, buffer, bufferOffset);
    // Serialize message field [steer_timeout]
    bufferOffset = _serializer.bool(obj.steer_timeout, buffer, bufferOffset);
    // Serialize message field [battery_volt]
    bufferOffset = _serializer.float64(obj.battery_volt, buffer, bufferOffset);
    // Serialize message field [battery_SOC]
    bufferOffset = _serializer.float64(obj.battery_SOC, buffer, bufferOffset);
    // Serialize message field [engine_speed]
    bufferOffset = _serializer.int16(obj.engine_speed, buffer, bufferOffset);
    // Serialize message field [vehicle_bug_code]
    bufferOffset = _serializer.int16(obj.vehicle_bug_code, buffer, bufferOffset);
    // Serialize message field [vehicle_state_code]
    bufferOffset = _serializer.int16(obj.vehicle_state_code, buffer, bufferOffset);
    return bufferOffset;
  }

  static deserialize(buffer, bufferOffset=[0]) {
    //deserializes a message object of type VehicleState
    let len;
    let data = new VehicleState(null);
    // Deserialize message field [timestamp]
    data.timestamp = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [id]
    data.id = _deserializer.int32(buffer, bufferOffset);
    // Deserialize message field [name]
    data.name = _deserializer.string(buffer, bufferOffset);
    // Deserialize message field [vehicle_state]
    data.vehicle_state = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [type]
    data.type = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [RTK_state_string]
    data.RTK_state_string = _deserializer.string(buffer, bufferOffset);
    // Deserialize message field [RTK_seq_num]
    data.RTK_seq_num = _deserializer.int64(buffer, bufferOffset);
    // Deserialize message field [RTK_timestamp_sec]
    data.RTK_timestamp_sec = _deserializer.int64(buffer, bufferOffset);
    // Deserialize message field [RTK_timestamp_nsec]
    data.RTK_timestamp_nsec = _deserializer.int64(buffer, bufferOffset);
    // Deserialize message field [RTK_gps_status]
    data.RTK_gps_status = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [RTK_gps_service]
    data.RTK_gps_service = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [RTK_gps_longitude]
    data.RTK_gps_longitude = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [RTK_gps_latitude]
    data.RTK_gps_latitude = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [RTK_gps_altitude]
    data.RTK_gps_altitude = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [RTK_gps_UTM_x]
    data.RTK_gps_UTM_x = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [RTK_gps_UTM_y]
    data.RTK_gps_UTM_y = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [RTK_gps_UTM_z]
    data.RTK_gps_UTM_z = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [RTK_linear_ENU_vx]
    data.RTK_linear_ENU_vx = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [RTK_linear_ENU_vy]
    data.RTK_linear_ENU_vy = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [RTK_linear_ENU_vz]
    data.RTK_linear_ENU_vz = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [RTK_linear_vx]
    data.RTK_linear_vx = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [RTK_linear_vy]
    data.RTK_linear_vy = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [RTK_linear_vz]
    data.RTK_linear_vz = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [RTK_angular_vx]
    data.RTK_angular_vx = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [RTK_angular_vy]
    data.RTK_angular_vy = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [RTK_angular_vz]
    data.RTK_angular_vz = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [x]
    data.x = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [y]
    data.y = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [z]
    data.z = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [speed_x]
    data.speed_x = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [speed_y]
    data.speed_y = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [speed_z]
    data.speed_z = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [acc_x]
    data.acc_x = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [acc_y]
    data.acc_y = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [acc_z]
    data.acc_z = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [heading]
    data.heading = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [pitch]
    data.pitch = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [roll]
    data.roll = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [yaw_rate]
    data.yaw_rate = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [size_x]
    data.size_x = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [size_y]
    data.size_y = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [size_z]
    data.size_z = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [wheelbase]
    data.wheelbase = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [gear_pos]
    data.gear_pos = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [by_wire_enabled]
    data.by_wire_enabled = _deserializer.bool(buffer, bufferOffset);
    // Deserialize message field [vehicle_mode]
    data.vehicle_mode = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [throttle_cmd]
    data.throttle_cmd = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [throttle_input]
    data.throttle_input = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [throttle_state]
    data.throttle_state = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [throttle_enabled]
    data.throttle_enabled = _deserializer.bool(buffer, bufferOffset);
    // Deserialize message field [throttle_override]
    data.throttle_override = _deserializer.bool(buffer, bufferOffset);
    // Deserialize message field [throttle_driver]
    data.throttle_driver = _deserializer.bool(buffer, bufferOffset);
    // Deserialize message field [throttle_timeout]
    data.throttle_timeout = _deserializer.bool(buffer, bufferOffset);
    // Deserialize message field [brake_cmd]
    data.brake_cmd = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [brake_input]
    data.brake_input = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [brake_state]
    data.brake_state = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [brake_torq_cmd]
    data.brake_torq_cmd = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [brake_torq_input]
    data.brake_torq_input = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [brake_torq_state]
    data.brake_torq_state = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [brake_boo_output]
    data.brake_boo_output = _deserializer.bool(buffer, bufferOffset);
    // Deserialize message field [brake_enabled]
    data.brake_enabled = _deserializer.bool(buffer, bufferOffset);
    // Deserialize message field [brake_override]
    data.brake_override = _deserializer.bool(buffer, bufferOffset);
    // Deserialize message field [brake_driver]
    data.brake_driver = _deserializer.bool(buffer, bufferOffset);
    // Deserialize message field [brake_timeout]
    data.brake_timeout = _deserializer.bool(buffer, bufferOffset);
    // Deserialize message field [steer_cmd]
    data.steer_cmd = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [steer_state_front_wheel]
    data.steer_state_front_wheel = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [steer_torque]
    data.steer_torque = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [steer_enabled]
    data.steer_enabled = _deserializer.bool(buffer, bufferOffset);
    // Deserialize message field [steer_override]
    data.steer_override = _deserializer.bool(buffer, bufferOffset);
    // Deserialize message field [steer_timeout]
    data.steer_timeout = _deserializer.bool(buffer, bufferOffset);
    // Deserialize message field [battery_volt]
    data.battery_volt = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [battery_SOC]
    data.battery_SOC = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [engine_speed]
    data.engine_speed = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [vehicle_bug_code]
    data.vehicle_bug_code = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [vehicle_state_code]
    data.vehicle_state_code = _deserializer.int16(buffer, bufferOffset);
    return data;
  }

  static getMessageSize(object) {
    let length = 0;
    length += _getByteLength(object.name);
    length += _getByteLength(object.RTK_state_string);
    return length + 443;
  }

  static datatype() {
    // Returns string type for a message object
    return 'cav_msgs/VehicleState';
  }

  static md5sum() {
    //Returns md5sum for a message object
    return '9bd3a4bb3c48f14d68f55c4dd2e4292a';
  }

  static messageDefinition() {
    // Returns full string definition for message
    return `
    ## timestamp, ros time or utc time
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
    
    
    `;
  }

  static Resolve(msg) {
    // deep-construct a valid message object instance of whatever was passed in
    if (typeof msg !== 'object' || msg === null) {
      msg = {};
    }
    const resolved = new VehicleState(null);
    if (msg.timestamp !== undefined) {
      resolved.timestamp = msg.timestamp;
    }
    else {
      resolved.timestamp = 0.0
    }

    if (msg.id !== undefined) {
      resolved.id = msg.id;
    }
    else {
      resolved.id = 0
    }

    if (msg.name !== undefined) {
      resolved.name = msg.name;
    }
    else {
      resolved.name = ''
    }

    if (msg.vehicle_state !== undefined) {
      resolved.vehicle_state = msg.vehicle_state;
    }
    else {
      resolved.vehicle_state = 0
    }

    if (msg.type !== undefined) {
      resolved.type = msg.type;
    }
    else {
      resolved.type = 0
    }

    if (msg.RTK_state_string !== undefined) {
      resolved.RTK_state_string = msg.RTK_state_string;
    }
    else {
      resolved.RTK_state_string = ''
    }

    if (msg.RTK_seq_num !== undefined) {
      resolved.RTK_seq_num = msg.RTK_seq_num;
    }
    else {
      resolved.RTK_seq_num = 0
    }

    if (msg.RTK_timestamp_sec !== undefined) {
      resolved.RTK_timestamp_sec = msg.RTK_timestamp_sec;
    }
    else {
      resolved.RTK_timestamp_sec = 0
    }

    if (msg.RTK_timestamp_nsec !== undefined) {
      resolved.RTK_timestamp_nsec = msg.RTK_timestamp_nsec;
    }
    else {
      resolved.RTK_timestamp_nsec = 0
    }

    if (msg.RTK_gps_status !== undefined) {
      resolved.RTK_gps_status = msg.RTK_gps_status;
    }
    else {
      resolved.RTK_gps_status = 0
    }

    if (msg.RTK_gps_service !== undefined) {
      resolved.RTK_gps_service = msg.RTK_gps_service;
    }
    else {
      resolved.RTK_gps_service = 0
    }

    if (msg.RTK_gps_longitude !== undefined) {
      resolved.RTK_gps_longitude = msg.RTK_gps_longitude;
    }
    else {
      resolved.RTK_gps_longitude = 0.0
    }

    if (msg.RTK_gps_latitude !== undefined) {
      resolved.RTK_gps_latitude = msg.RTK_gps_latitude;
    }
    else {
      resolved.RTK_gps_latitude = 0.0
    }

    if (msg.RTK_gps_altitude !== undefined) {
      resolved.RTK_gps_altitude = msg.RTK_gps_altitude;
    }
    else {
      resolved.RTK_gps_altitude = 0.0
    }

    if (msg.RTK_gps_UTM_x !== undefined) {
      resolved.RTK_gps_UTM_x = msg.RTK_gps_UTM_x;
    }
    else {
      resolved.RTK_gps_UTM_x = 0.0
    }

    if (msg.RTK_gps_UTM_y !== undefined) {
      resolved.RTK_gps_UTM_y = msg.RTK_gps_UTM_y;
    }
    else {
      resolved.RTK_gps_UTM_y = 0.0
    }

    if (msg.RTK_gps_UTM_z !== undefined) {
      resolved.RTK_gps_UTM_z = msg.RTK_gps_UTM_z;
    }
    else {
      resolved.RTK_gps_UTM_z = 0.0
    }

    if (msg.RTK_linear_ENU_vx !== undefined) {
      resolved.RTK_linear_ENU_vx = msg.RTK_linear_ENU_vx;
    }
    else {
      resolved.RTK_linear_ENU_vx = 0.0
    }

    if (msg.RTK_linear_ENU_vy !== undefined) {
      resolved.RTK_linear_ENU_vy = msg.RTK_linear_ENU_vy;
    }
    else {
      resolved.RTK_linear_ENU_vy = 0.0
    }

    if (msg.RTK_linear_ENU_vz !== undefined) {
      resolved.RTK_linear_ENU_vz = msg.RTK_linear_ENU_vz;
    }
    else {
      resolved.RTK_linear_ENU_vz = 0.0
    }

    if (msg.RTK_linear_vx !== undefined) {
      resolved.RTK_linear_vx = msg.RTK_linear_vx;
    }
    else {
      resolved.RTK_linear_vx = 0.0
    }

    if (msg.RTK_linear_vy !== undefined) {
      resolved.RTK_linear_vy = msg.RTK_linear_vy;
    }
    else {
      resolved.RTK_linear_vy = 0.0
    }

    if (msg.RTK_linear_vz !== undefined) {
      resolved.RTK_linear_vz = msg.RTK_linear_vz;
    }
    else {
      resolved.RTK_linear_vz = 0.0
    }

    if (msg.RTK_angular_vx !== undefined) {
      resolved.RTK_angular_vx = msg.RTK_angular_vx;
    }
    else {
      resolved.RTK_angular_vx = 0.0
    }

    if (msg.RTK_angular_vy !== undefined) {
      resolved.RTK_angular_vy = msg.RTK_angular_vy;
    }
    else {
      resolved.RTK_angular_vy = 0.0
    }

    if (msg.RTK_angular_vz !== undefined) {
      resolved.RTK_angular_vz = msg.RTK_angular_vz;
    }
    else {
      resolved.RTK_angular_vz = 0.0
    }

    if (msg.x !== undefined) {
      resolved.x = msg.x;
    }
    else {
      resolved.x = 0.0
    }

    if (msg.y !== undefined) {
      resolved.y = msg.y;
    }
    else {
      resolved.y = 0.0
    }

    if (msg.z !== undefined) {
      resolved.z = msg.z;
    }
    else {
      resolved.z = 0.0
    }

    if (msg.speed_x !== undefined) {
      resolved.speed_x = msg.speed_x;
    }
    else {
      resolved.speed_x = 0.0
    }

    if (msg.speed_y !== undefined) {
      resolved.speed_y = msg.speed_y;
    }
    else {
      resolved.speed_y = 0.0
    }

    if (msg.speed_z !== undefined) {
      resolved.speed_z = msg.speed_z;
    }
    else {
      resolved.speed_z = 0.0
    }

    if (msg.acc_x !== undefined) {
      resolved.acc_x = msg.acc_x;
    }
    else {
      resolved.acc_x = 0.0
    }

    if (msg.acc_y !== undefined) {
      resolved.acc_y = msg.acc_y;
    }
    else {
      resolved.acc_y = 0.0
    }

    if (msg.acc_z !== undefined) {
      resolved.acc_z = msg.acc_z;
    }
    else {
      resolved.acc_z = 0.0
    }

    if (msg.heading !== undefined) {
      resolved.heading = msg.heading;
    }
    else {
      resolved.heading = 0.0
    }

    if (msg.pitch !== undefined) {
      resolved.pitch = msg.pitch;
    }
    else {
      resolved.pitch = 0.0
    }

    if (msg.roll !== undefined) {
      resolved.roll = msg.roll;
    }
    else {
      resolved.roll = 0.0
    }

    if (msg.yaw_rate !== undefined) {
      resolved.yaw_rate = msg.yaw_rate;
    }
    else {
      resolved.yaw_rate = 0.0
    }

    if (msg.size_x !== undefined) {
      resolved.size_x = msg.size_x;
    }
    else {
      resolved.size_x = 0.0
    }

    if (msg.size_y !== undefined) {
      resolved.size_y = msg.size_y;
    }
    else {
      resolved.size_y = 0.0
    }

    if (msg.size_z !== undefined) {
      resolved.size_z = msg.size_z;
    }
    else {
      resolved.size_z = 0.0
    }

    if (msg.wheelbase !== undefined) {
      resolved.wheelbase = msg.wheelbase;
    }
    else {
      resolved.wheelbase = 0.0
    }

    if (msg.gear_pos !== undefined) {
      resolved.gear_pos = msg.gear_pos;
    }
    else {
      resolved.gear_pos = 0
    }

    if (msg.by_wire_enabled !== undefined) {
      resolved.by_wire_enabled = msg.by_wire_enabled;
    }
    else {
      resolved.by_wire_enabled = false
    }

    if (msg.vehicle_mode !== undefined) {
      resolved.vehicle_mode = msg.vehicle_mode;
    }
    else {
      resolved.vehicle_mode = 0
    }

    if (msg.throttle_cmd !== undefined) {
      resolved.throttle_cmd = msg.throttle_cmd;
    }
    else {
      resolved.throttle_cmd = 0.0
    }

    if (msg.throttle_input !== undefined) {
      resolved.throttle_input = msg.throttle_input;
    }
    else {
      resolved.throttle_input = 0.0
    }

    if (msg.throttle_state !== undefined) {
      resolved.throttle_state = msg.throttle_state;
    }
    else {
      resolved.throttle_state = 0.0
    }

    if (msg.throttle_enabled !== undefined) {
      resolved.throttle_enabled = msg.throttle_enabled;
    }
    else {
      resolved.throttle_enabled = false
    }

    if (msg.throttle_override !== undefined) {
      resolved.throttle_override = msg.throttle_override;
    }
    else {
      resolved.throttle_override = false
    }

    if (msg.throttle_driver !== undefined) {
      resolved.throttle_driver = msg.throttle_driver;
    }
    else {
      resolved.throttle_driver = false
    }

    if (msg.throttle_timeout !== undefined) {
      resolved.throttle_timeout = msg.throttle_timeout;
    }
    else {
      resolved.throttle_timeout = false
    }

    if (msg.brake_cmd !== undefined) {
      resolved.brake_cmd = msg.brake_cmd;
    }
    else {
      resolved.brake_cmd = 0.0
    }

    if (msg.brake_input !== undefined) {
      resolved.brake_input = msg.brake_input;
    }
    else {
      resolved.brake_input = 0.0
    }

    if (msg.brake_state !== undefined) {
      resolved.brake_state = msg.brake_state;
    }
    else {
      resolved.brake_state = 0.0
    }

    if (msg.brake_torq_cmd !== undefined) {
      resolved.brake_torq_cmd = msg.brake_torq_cmd;
    }
    else {
      resolved.brake_torq_cmd = 0.0
    }

    if (msg.brake_torq_input !== undefined) {
      resolved.brake_torq_input = msg.brake_torq_input;
    }
    else {
      resolved.brake_torq_input = 0.0
    }

    if (msg.brake_torq_state !== undefined) {
      resolved.brake_torq_state = msg.brake_torq_state;
    }
    else {
      resolved.brake_torq_state = 0.0
    }

    if (msg.brake_boo_output !== undefined) {
      resolved.brake_boo_output = msg.brake_boo_output;
    }
    else {
      resolved.brake_boo_output = false
    }

    if (msg.brake_enabled !== undefined) {
      resolved.brake_enabled = msg.brake_enabled;
    }
    else {
      resolved.brake_enabled = false
    }

    if (msg.brake_override !== undefined) {
      resolved.brake_override = msg.brake_override;
    }
    else {
      resolved.brake_override = false
    }

    if (msg.brake_driver !== undefined) {
      resolved.brake_driver = msg.brake_driver;
    }
    else {
      resolved.brake_driver = false
    }

    if (msg.brake_timeout !== undefined) {
      resolved.brake_timeout = msg.brake_timeout;
    }
    else {
      resolved.brake_timeout = false
    }

    if (msg.steer_cmd !== undefined) {
      resolved.steer_cmd = msg.steer_cmd;
    }
    else {
      resolved.steer_cmd = 0.0
    }

    if (msg.steer_state_front_wheel !== undefined) {
      resolved.steer_state_front_wheel = msg.steer_state_front_wheel;
    }
    else {
      resolved.steer_state_front_wheel = 0.0
    }

    if (msg.steer_torque !== undefined) {
      resolved.steer_torque = msg.steer_torque;
    }
    else {
      resolved.steer_torque = 0.0
    }

    if (msg.steer_enabled !== undefined) {
      resolved.steer_enabled = msg.steer_enabled;
    }
    else {
      resolved.steer_enabled = false
    }

    if (msg.steer_override !== undefined) {
      resolved.steer_override = msg.steer_override;
    }
    else {
      resolved.steer_override = false
    }

    if (msg.steer_timeout !== undefined) {
      resolved.steer_timeout = msg.steer_timeout;
    }
    else {
      resolved.steer_timeout = false
    }

    if (msg.battery_volt !== undefined) {
      resolved.battery_volt = msg.battery_volt;
    }
    else {
      resolved.battery_volt = 0.0
    }

    if (msg.battery_SOC !== undefined) {
      resolved.battery_SOC = msg.battery_SOC;
    }
    else {
      resolved.battery_SOC = 0.0
    }

    if (msg.engine_speed !== undefined) {
      resolved.engine_speed = msg.engine_speed;
    }
    else {
      resolved.engine_speed = 0
    }

    if (msg.vehicle_bug_code !== undefined) {
      resolved.vehicle_bug_code = msg.vehicle_bug_code;
    }
    else {
      resolved.vehicle_bug_code = 0
    }

    if (msg.vehicle_state_code !== undefined) {
      resolved.vehicle_state_code = msg.vehicle_state_code;
    }
    else {
      resolved.vehicle_state_code = 0
    }

    return resolved;
    }
};

module.exports = VehicleState;
