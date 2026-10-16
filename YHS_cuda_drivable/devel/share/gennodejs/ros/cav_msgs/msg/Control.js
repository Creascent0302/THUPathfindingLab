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

class Control {
  constructor(initObj={}) {
    if (initObj === null) {
      // initObj === null is a special case for deserialization where we don't initialize fields
      this.timestamp = null;
      this.count = null;
      this.brake_cmd = null;
      this.throttle_cmd = null;
      this.steering_cmd = null;
      this.gear_cmd = null;
      this.turn_signal_cmd = null;
      this.speed_cmd = null;
      this.acceleration_cmd = null;
      this.bywire_control_enable = null;
      this.emerg_brake = null;
      this.front_light = null;
      this.engine_enable = null;
      this.park_enable = null;
      this.vehicle_mode = null;
      this.yaw_speed_cmd = null;
      this.ey_out = null;
      this.ephi_out = null;
    }
    else {
      if (initObj.hasOwnProperty('timestamp')) {
        this.timestamp = initObj.timestamp
      }
      else {
        this.timestamp = 0.0;
      }
      if (initObj.hasOwnProperty('count')) {
        this.count = initObj.count
      }
      else {
        this.count = 0;
      }
      if (initObj.hasOwnProperty('brake_cmd')) {
        this.brake_cmd = initObj.brake_cmd
      }
      else {
        this.brake_cmd = 0.0;
      }
      if (initObj.hasOwnProperty('throttle_cmd')) {
        this.throttle_cmd = initObj.throttle_cmd
      }
      else {
        this.throttle_cmd = 0.0;
      }
      if (initObj.hasOwnProperty('steering_cmd')) {
        this.steering_cmd = initObj.steering_cmd
      }
      else {
        this.steering_cmd = 0.0;
      }
      if (initObj.hasOwnProperty('gear_cmd')) {
        this.gear_cmd = initObj.gear_cmd
      }
      else {
        this.gear_cmd = 0;
      }
      if (initObj.hasOwnProperty('turn_signal_cmd')) {
        this.turn_signal_cmd = initObj.turn_signal_cmd
      }
      else {
        this.turn_signal_cmd = 0;
      }
      if (initObj.hasOwnProperty('speed_cmd')) {
        this.speed_cmd = initObj.speed_cmd
      }
      else {
        this.speed_cmd = 0.0;
      }
      if (initObj.hasOwnProperty('acceleration_cmd')) {
        this.acceleration_cmd = initObj.acceleration_cmd
      }
      else {
        this.acceleration_cmd = 0.0;
      }
      if (initObj.hasOwnProperty('bywire_control_enable')) {
        this.bywire_control_enable = initObj.bywire_control_enable
      }
      else {
        this.bywire_control_enable = 0;
      }
      if (initObj.hasOwnProperty('emerg_brake')) {
        this.emerg_brake = initObj.emerg_brake
      }
      else {
        this.emerg_brake = 0;
      }
      if (initObj.hasOwnProperty('front_light')) {
        this.front_light = initObj.front_light
      }
      else {
        this.front_light = 0;
      }
      if (initObj.hasOwnProperty('engine_enable')) {
        this.engine_enable = initObj.engine_enable
      }
      else {
        this.engine_enable = 0;
      }
      if (initObj.hasOwnProperty('park_enable')) {
        this.park_enable = initObj.park_enable
      }
      else {
        this.park_enable = 0;
      }
      if (initObj.hasOwnProperty('vehicle_mode')) {
        this.vehicle_mode = initObj.vehicle_mode
      }
      else {
        this.vehicle_mode = 0;
      }
      if (initObj.hasOwnProperty('yaw_speed_cmd')) {
        this.yaw_speed_cmd = initObj.yaw_speed_cmd
      }
      else {
        this.yaw_speed_cmd = 0.0;
      }
      if (initObj.hasOwnProperty('ey_out')) {
        this.ey_out = initObj.ey_out
      }
      else {
        this.ey_out = 0.0;
      }
      if (initObj.hasOwnProperty('ephi_out')) {
        this.ephi_out = initObj.ephi_out
      }
      else {
        this.ephi_out = 0.0;
      }
    }
  }

  static serialize(obj, buffer, bufferOffset) {
    // Serializes a message object of type Control
    // Serialize message field [timestamp]
    bufferOffset = _serializer.float64(obj.timestamp, buffer, bufferOffset);
    // Serialize message field [count]
    bufferOffset = _serializer.int32(obj.count, buffer, bufferOffset);
    // Serialize message field [brake_cmd]
    bufferOffset = _serializer.float64(obj.brake_cmd, buffer, bufferOffset);
    // Serialize message field [throttle_cmd]
    bufferOffset = _serializer.float64(obj.throttle_cmd, buffer, bufferOffset);
    // Serialize message field [steering_cmd]
    bufferOffset = _serializer.float64(obj.steering_cmd, buffer, bufferOffset);
    // Serialize message field [gear_cmd]
    bufferOffset = _serializer.int16(obj.gear_cmd, buffer, bufferOffset);
    // Serialize message field [turn_signal_cmd]
    bufferOffset = _serializer.int16(obj.turn_signal_cmd, buffer, bufferOffset);
    // Serialize message field [speed_cmd]
    bufferOffset = _serializer.float64(obj.speed_cmd, buffer, bufferOffset);
    // Serialize message field [acceleration_cmd]
    bufferOffset = _serializer.float64(obj.acceleration_cmd, buffer, bufferOffset);
    // Serialize message field [bywire_control_enable]
    bufferOffset = _serializer.int16(obj.bywire_control_enable, buffer, bufferOffset);
    // Serialize message field [emerg_brake]
    bufferOffset = _serializer.int16(obj.emerg_brake, buffer, bufferOffset);
    // Serialize message field [front_light]
    bufferOffset = _serializer.int16(obj.front_light, buffer, bufferOffset);
    // Serialize message field [engine_enable]
    bufferOffset = _serializer.int16(obj.engine_enable, buffer, bufferOffset);
    // Serialize message field [park_enable]
    bufferOffset = _serializer.int16(obj.park_enable, buffer, bufferOffset);
    // Serialize message field [vehicle_mode]
    bufferOffset = _serializer.int16(obj.vehicle_mode, buffer, bufferOffset);
    // Serialize message field [yaw_speed_cmd]
    bufferOffset = _serializer.float64(obj.yaw_speed_cmd, buffer, bufferOffset);
    // Serialize message field [ey_out]
    bufferOffset = _serializer.float64(obj.ey_out, buffer, bufferOffset);
    // Serialize message field [ephi_out]
    bufferOffset = _serializer.float64(obj.ephi_out, buffer, bufferOffset);
    return bufferOffset;
  }

  static deserialize(buffer, bufferOffset=[0]) {
    //deserializes a message object of type Control
    let len;
    let data = new Control(null);
    // Deserialize message field [timestamp]
    data.timestamp = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [count]
    data.count = _deserializer.int32(buffer, bufferOffset);
    // Deserialize message field [brake_cmd]
    data.brake_cmd = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [throttle_cmd]
    data.throttle_cmd = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [steering_cmd]
    data.steering_cmd = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [gear_cmd]
    data.gear_cmd = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [turn_signal_cmd]
    data.turn_signal_cmd = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [speed_cmd]
    data.speed_cmd = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [acceleration_cmd]
    data.acceleration_cmd = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [bywire_control_enable]
    data.bywire_control_enable = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [emerg_brake]
    data.emerg_brake = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [front_light]
    data.front_light = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [engine_enable]
    data.engine_enable = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [park_enable]
    data.park_enable = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [vehicle_mode]
    data.vehicle_mode = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [yaw_speed_cmd]
    data.yaw_speed_cmd = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [ey_out]
    data.ey_out = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [ephi_out]
    data.ephi_out = _deserializer.float64(buffer, bufferOffset);
    return data;
  }

  static getMessageSize(object) {
    return 92;
  }

  static datatype() {
    // Returns string type for a message object
    return 'cav_msgs/Control';
  }

  static md5sum() {
    //Returns md5sum for a message object
    return '2213456a98df9c5879311b15b53093ed';
  }

  static messageDefinition() {
    // Returns full string definition for message
    return `
    ##timestamp
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
    
    `;
  }

  static Resolve(msg) {
    // deep-construct a valid message object instance of whatever was passed in
    if (typeof msg !== 'object' || msg === null) {
      msg = {};
    }
    const resolved = new Control(null);
    if (msg.timestamp !== undefined) {
      resolved.timestamp = msg.timestamp;
    }
    else {
      resolved.timestamp = 0.0
    }

    if (msg.count !== undefined) {
      resolved.count = msg.count;
    }
    else {
      resolved.count = 0
    }

    if (msg.brake_cmd !== undefined) {
      resolved.brake_cmd = msg.brake_cmd;
    }
    else {
      resolved.brake_cmd = 0.0
    }

    if (msg.throttle_cmd !== undefined) {
      resolved.throttle_cmd = msg.throttle_cmd;
    }
    else {
      resolved.throttle_cmd = 0.0
    }

    if (msg.steering_cmd !== undefined) {
      resolved.steering_cmd = msg.steering_cmd;
    }
    else {
      resolved.steering_cmd = 0.0
    }

    if (msg.gear_cmd !== undefined) {
      resolved.gear_cmd = msg.gear_cmd;
    }
    else {
      resolved.gear_cmd = 0
    }

    if (msg.turn_signal_cmd !== undefined) {
      resolved.turn_signal_cmd = msg.turn_signal_cmd;
    }
    else {
      resolved.turn_signal_cmd = 0
    }

    if (msg.speed_cmd !== undefined) {
      resolved.speed_cmd = msg.speed_cmd;
    }
    else {
      resolved.speed_cmd = 0.0
    }

    if (msg.acceleration_cmd !== undefined) {
      resolved.acceleration_cmd = msg.acceleration_cmd;
    }
    else {
      resolved.acceleration_cmd = 0.0
    }

    if (msg.bywire_control_enable !== undefined) {
      resolved.bywire_control_enable = msg.bywire_control_enable;
    }
    else {
      resolved.bywire_control_enable = 0
    }

    if (msg.emerg_brake !== undefined) {
      resolved.emerg_brake = msg.emerg_brake;
    }
    else {
      resolved.emerg_brake = 0
    }

    if (msg.front_light !== undefined) {
      resolved.front_light = msg.front_light;
    }
    else {
      resolved.front_light = 0
    }

    if (msg.engine_enable !== undefined) {
      resolved.engine_enable = msg.engine_enable;
    }
    else {
      resolved.engine_enable = 0
    }

    if (msg.park_enable !== undefined) {
      resolved.park_enable = msg.park_enable;
    }
    else {
      resolved.park_enable = 0
    }

    if (msg.vehicle_mode !== undefined) {
      resolved.vehicle_mode = msg.vehicle_mode;
    }
    else {
      resolved.vehicle_mode = 0
    }

    if (msg.yaw_speed_cmd !== undefined) {
      resolved.yaw_speed_cmd = msg.yaw_speed_cmd;
    }
    else {
      resolved.yaw_speed_cmd = 0.0
    }

    if (msg.ey_out !== undefined) {
      resolved.ey_out = msg.ey_out;
    }
    else {
      resolved.ey_out = 0.0
    }

    if (msg.ephi_out !== undefined) {
      resolved.ephi_out = msg.ephi_out;
    }
    else {
      resolved.ephi_out = 0.0
    }

    return resolved;
    }
};

module.exports = Control;
