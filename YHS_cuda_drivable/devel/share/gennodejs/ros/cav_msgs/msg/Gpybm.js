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

class Gpybm {
  constructor(initObj={}) {
    if (initObj === null) {
      // initObj === null is a special case for deserialization where we don't initialize fields
      this.serial_number = null;
      this.utc = null;
      this.latitude = null;
      this.longitude = null;
      this.height = null;
      this.yaw = null;
      this.pitch = null;
      this.north_vel = null;
      this.east_vel = null;
      this.earth_vel = null;
      this.vel = null;
      this.gaussian_x = null;
      this.gaussian_y = null;
      this.base_station_x = null;
      this.base_station_y = null;
      this.status = null;
      this.status_vice = null;
    }
    else {
      if (initObj.hasOwnProperty('serial_number')) {
        this.serial_number = initObj.serial_number
      }
      else {
        this.serial_number = '';
      }
      if (initObj.hasOwnProperty('utc')) {
        this.utc = initObj.utc
      }
      else {
        this.utc = 0.0;
      }
      if (initObj.hasOwnProperty('latitude')) {
        this.latitude = initObj.latitude
      }
      else {
        this.latitude = 0.0;
      }
      if (initObj.hasOwnProperty('longitude')) {
        this.longitude = initObj.longitude
      }
      else {
        this.longitude = 0.0;
      }
      if (initObj.hasOwnProperty('height')) {
        this.height = initObj.height
      }
      else {
        this.height = 0.0;
      }
      if (initObj.hasOwnProperty('yaw')) {
        this.yaw = initObj.yaw
      }
      else {
        this.yaw = 0.0;
      }
      if (initObj.hasOwnProperty('pitch')) {
        this.pitch = initObj.pitch
      }
      else {
        this.pitch = 0.0;
      }
      if (initObj.hasOwnProperty('north_vel')) {
        this.north_vel = initObj.north_vel
      }
      else {
        this.north_vel = 0.0;
      }
      if (initObj.hasOwnProperty('east_vel')) {
        this.east_vel = initObj.east_vel
      }
      else {
        this.east_vel = 0.0;
      }
      if (initObj.hasOwnProperty('earth_vel')) {
        this.earth_vel = initObj.earth_vel
      }
      else {
        this.earth_vel = 0.0;
      }
      if (initObj.hasOwnProperty('vel')) {
        this.vel = initObj.vel
      }
      else {
        this.vel = 0.0;
      }
      if (initObj.hasOwnProperty('gaussian_x')) {
        this.gaussian_x = initObj.gaussian_x
      }
      else {
        this.gaussian_x = 0.0;
      }
      if (initObj.hasOwnProperty('gaussian_y')) {
        this.gaussian_y = initObj.gaussian_y
      }
      else {
        this.gaussian_y = 0.0;
      }
      if (initObj.hasOwnProperty('base_station_x')) {
        this.base_station_x = initObj.base_station_x
      }
      else {
        this.base_station_x = 0.0;
      }
      if (initObj.hasOwnProperty('base_station_y')) {
        this.base_station_y = initObj.base_station_y
      }
      else {
        this.base_station_y = 0.0;
      }
      if (initObj.hasOwnProperty('status')) {
        this.status = initObj.status
      }
      else {
        this.status = 0;
      }
      if (initObj.hasOwnProperty('status_vice')) {
        this.status_vice = initObj.status_vice
      }
      else {
        this.status_vice = 0;
      }
    }
  }

  static serialize(obj, buffer, bufferOffset) {
    // Serializes a message object of type Gpybm
    // Serialize message field [serial_number]
    bufferOffset = _serializer.string(obj.serial_number, buffer, bufferOffset);
    // Serialize message field [utc]
    bufferOffset = _serializer.float64(obj.utc, buffer, bufferOffset);
    // Serialize message field [latitude]
    bufferOffset = _serializer.float64(obj.latitude, buffer, bufferOffset);
    // Serialize message field [longitude]
    bufferOffset = _serializer.float64(obj.longitude, buffer, bufferOffset);
    // Serialize message field [height]
    bufferOffset = _serializer.float64(obj.height, buffer, bufferOffset);
    // Serialize message field [yaw]
    bufferOffset = _serializer.float64(obj.yaw, buffer, bufferOffset);
    // Serialize message field [pitch]
    bufferOffset = _serializer.float64(obj.pitch, buffer, bufferOffset);
    // Serialize message field [north_vel]
    bufferOffset = _serializer.float64(obj.north_vel, buffer, bufferOffset);
    // Serialize message field [east_vel]
    bufferOffset = _serializer.float64(obj.east_vel, buffer, bufferOffset);
    // Serialize message field [earth_vel]
    bufferOffset = _serializer.float64(obj.earth_vel, buffer, bufferOffset);
    // Serialize message field [vel]
    bufferOffset = _serializer.float64(obj.vel, buffer, bufferOffset);
    // Serialize message field [gaussian_x]
    bufferOffset = _serializer.float64(obj.gaussian_x, buffer, bufferOffset);
    // Serialize message field [gaussian_y]
    bufferOffset = _serializer.float64(obj.gaussian_y, buffer, bufferOffset);
    // Serialize message field [base_station_x]
    bufferOffset = _serializer.float64(obj.base_station_x, buffer, bufferOffset);
    // Serialize message field [base_station_y]
    bufferOffset = _serializer.float64(obj.base_station_y, buffer, bufferOffset);
    // Serialize message field [status]
    bufferOffset = _serializer.int16(obj.status, buffer, bufferOffset);
    // Serialize message field [status_vice]
    bufferOffset = _serializer.int16(obj.status_vice, buffer, bufferOffset);
    return bufferOffset;
  }

  static deserialize(buffer, bufferOffset=[0]) {
    //deserializes a message object of type Gpybm
    let len;
    let data = new Gpybm(null);
    // Deserialize message field [serial_number]
    data.serial_number = _deserializer.string(buffer, bufferOffset);
    // Deserialize message field [utc]
    data.utc = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [latitude]
    data.latitude = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [longitude]
    data.longitude = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [height]
    data.height = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [yaw]
    data.yaw = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [pitch]
    data.pitch = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [north_vel]
    data.north_vel = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [east_vel]
    data.east_vel = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [earth_vel]
    data.earth_vel = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [vel]
    data.vel = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [gaussian_x]
    data.gaussian_x = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [gaussian_y]
    data.gaussian_y = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [base_station_x]
    data.base_station_x = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [base_station_y]
    data.base_station_y = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [status]
    data.status = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [status_vice]
    data.status_vice = _deserializer.int16(buffer, bufferOffset);
    return data;
  }

  static getMessageSize(object) {
    let length = 0;
    length += _getByteLength(object.serial_number);
    return length + 120;
  }

  static datatype() {
    // Returns string type for a message object
    return 'cav_msgs/Gpybm';
  }

  static md5sum() {
    //Returns md5sum for a message object
    return '705e6b1ef5c61da21386f82da44e4cfd';
  }

  static messageDefinition() {
    // Returns full string definition for message
    return `
    string serial_number # sino gnss hardware serial number
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
    
    
    `;
  }

  static Resolve(msg) {
    // deep-construct a valid message object instance of whatever was passed in
    if (typeof msg !== 'object' || msg === null) {
      msg = {};
    }
    const resolved = new Gpybm(null);
    if (msg.serial_number !== undefined) {
      resolved.serial_number = msg.serial_number;
    }
    else {
      resolved.serial_number = ''
    }

    if (msg.utc !== undefined) {
      resolved.utc = msg.utc;
    }
    else {
      resolved.utc = 0.0
    }

    if (msg.latitude !== undefined) {
      resolved.latitude = msg.latitude;
    }
    else {
      resolved.latitude = 0.0
    }

    if (msg.longitude !== undefined) {
      resolved.longitude = msg.longitude;
    }
    else {
      resolved.longitude = 0.0
    }

    if (msg.height !== undefined) {
      resolved.height = msg.height;
    }
    else {
      resolved.height = 0.0
    }

    if (msg.yaw !== undefined) {
      resolved.yaw = msg.yaw;
    }
    else {
      resolved.yaw = 0.0
    }

    if (msg.pitch !== undefined) {
      resolved.pitch = msg.pitch;
    }
    else {
      resolved.pitch = 0.0
    }

    if (msg.north_vel !== undefined) {
      resolved.north_vel = msg.north_vel;
    }
    else {
      resolved.north_vel = 0.0
    }

    if (msg.east_vel !== undefined) {
      resolved.east_vel = msg.east_vel;
    }
    else {
      resolved.east_vel = 0.0
    }

    if (msg.earth_vel !== undefined) {
      resolved.earth_vel = msg.earth_vel;
    }
    else {
      resolved.earth_vel = 0.0
    }

    if (msg.vel !== undefined) {
      resolved.vel = msg.vel;
    }
    else {
      resolved.vel = 0.0
    }

    if (msg.gaussian_x !== undefined) {
      resolved.gaussian_x = msg.gaussian_x;
    }
    else {
      resolved.gaussian_x = 0.0
    }

    if (msg.gaussian_y !== undefined) {
      resolved.gaussian_y = msg.gaussian_y;
    }
    else {
      resolved.gaussian_y = 0.0
    }

    if (msg.base_station_x !== undefined) {
      resolved.base_station_x = msg.base_station_x;
    }
    else {
      resolved.base_station_x = 0.0
    }

    if (msg.base_station_y !== undefined) {
      resolved.base_station_y = msg.base_station_y;
    }
    else {
      resolved.base_station_y = 0.0
    }

    if (msg.status !== undefined) {
      resolved.status = msg.status;
    }
    else {
      resolved.status = 0
    }

    if (msg.status_vice !== undefined) {
      resolved.status_vice = msg.status_vice;
    }
    else {
      resolved.status_vice = 0
    }

    return resolved;
    }
};

module.exports = Gpybm;
