// Auto-generated. Do not edit!

// (in-package xperception_msgs.msg)


"use strict";

const _serializer = _ros_msg_utils.Serialize;
const _arraySerializer = _serializer.Array;
const _deserializer = _ros_msg_utils.Deserialize;
const _arrayDeserializer = _deserializer.Array;
const _finder = _ros_msg_utils.Find;
const _getByteLength = _ros_msg_utils.getByteLength;

//-----------------------------------------------------------

class Object {
  constructor(initObj={}) {
    if (initObj === null) {
      // initObj === null is a special case for deserialization where we don't initialize fields
      this.timestamp = null;
      this.id = null;
      this.type = null;
      this.size_x = null;
      this.size_y = null;
      this.size_z = null;
      this.heading = null;
      this.speed = null;
      this.x = null;
      this.y = null;
      this.z = null;
      this.longitude = null;
      this.latitude = null;
      this.confidence = null;
      this.type_gt = null;
      this.size_x_gt = null;
      this.size_y_gt = null;
      this.size_z_gt = null;
      this.heading_gt = null;
      this.speed_gt = null;
      this.x_gt = null;
      this.y_gt = null;
      this.z_gt = null;
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
      if (initObj.hasOwnProperty('type')) {
        this.type = initObj.type
      }
      else {
        this.type = 0;
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
      if (initObj.hasOwnProperty('heading')) {
        this.heading = initObj.heading
      }
      else {
        this.heading = 0.0;
      }
      if (initObj.hasOwnProperty('speed')) {
        this.speed = initObj.speed
      }
      else {
        this.speed = 0.0;
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
      if (initObj.hasOwnProperty('longitude')) {
        this.longitude = initObj.longitude
      }
      else {
        this.longitude = 0.0;
      }
      if (initObj.hasOwnProperty('latitude')) {
        this.latitude = initObj.latitude
      }
      else {
        this.latitude = 0.0;
      }
      if (initObj.hasOwnProperty('confidence')) {
        this.confidence = initObj.confidence
      }
      else {
        this.confidence = 0.0;
      }
      if (initObj.hasOwnProperty('type_gt')) {
        this.type_gt = initObj.type_gt
      }
      else {
        this.type_gt = 0;
      }
      if (initObj.hasOwnProperty('size_x_gt')) {
        this.size_x_gt = initObj.size_x_gt
      }
      else {
        this.size_x_gt = 0.0;
      }
      if (initObj.hasOwnProperty('size_y_gt')) {
        this.size_y_gt = initObj.size_y_gt
      }
      else {
        this.size_y_gt = 0.0;
      }
      if (initObj.hasOwnProperty('size_z_gt')) {
        this.size_z_gt = initObj.size_z_gt
      }
      else {
        this.size_z_gt = 0.0;
      }
      if (initObj.hasOwnProperty('heading_gt')) {
        this.heading_gt = initObj.heading_gt
      }
      else {
        this.heading_gt = 0.0;
      }
      if (initObj.hasOwnProperty('speed_gt')) {
        this.speed_gt = initObj.speed_gt
      }
      else {
        this.speed_gt = 0.0;
      }
      if (initObj.hasOwnProperty('x_gt')) {
        this.x_gt = initObj.x_gt
      }
      else {
        this.x_gt = 0.0;
      }
      if (initObj.hasOwnProperty('y_gt')) {
        this.y_gt = initObj.y_gt
      }
      else {
        this.y_gt = 0.0;
      }
      if (initObj.hasOwnProperty('z_gt')) {
        this.z_gt = initObj.z_gt
      }
      else {
        this.z_gt = 0.0;
      }
    }
  }

  static serialize(obj, buffer, bufferOffset) {
    // Serializes a message object of type Object
    // Serialize message field [timestamp]
    bufferOffset = _serializer.float64(obj.timestamp, buffer, bufferOffset);
    // Serialize message field [id]
    bufferOffset = _serializer.int32(obj.id, buffer, bufferOffset);
    // Serialize message field [type]
    bufferOffset = _serializer.int16(obj.type, buffer, bufferOffset);
    // Serialize message field [size_x]
    bufferOffset = _serializer.float64(obj.size_x, buffer, bufferOffset);
    // Serialize message field [size_y]
    bufferOffset = _serializer.float64(obj.size_y, buffer, bufferOffset);
    // Serialize message field [size_z]
    bufferOffset = _serializer.float64(obj.size_z, buffer, bufferOffset);
    // Serialize message field [heading]
    bufferOffset = _serializer.float64(obj.heading, buffer, bufferOffset);
    // Serialize message field [speed]
    bufferOffset = _serializer.float64(obj.speed, buffer, bufferOffset);
    // Serialize message field [x]
    bufferOffset = _serializer.float64(obj.x, buffer, bufferOffset);
    // Serialize message field [y]
    bufferOffset = _serializer.float64(obj.y, buffer, bufferOffset);
    // Serialize message field [z]
    bufferOffset = _serializer.float64(obj.z, buffer, bufferOffset);
    // Serialize message field [longitude]
    bufferOffset = _serializer.float64(obj.longitude, buffer, bufferOffset);
    // Serialize message field [latitude]
    bufferOffset = _serializer.float64(obj.latitude, buffer, bufferOffset);
    // Serialize message field [confidence]
    bufferOffset = _serializer.float64(obj.confidence, buffer, bufferOffset);
    // Serialize message field [type_gt]
    bufferOffset = _serializer.int16(obj.type_gt, buffer, bufferOffset);
    // Serialize message field [size_x_gt]
    bufferOffset = _serializer.float64(obj.size_x_gt, buffer, bufferOffset);
    // Serialize message field [size_y_gt]
    bufferOffset = _serializer.float64(obj.size_y_gt, buffer, bufferOffset);
    // Serialize message field [size_z_gt]
    bufferOffset = _serializer.float64(obj.size_z_gt, buffer, bufferOffset);
    // Serialize message field [heading_gt]
    bufferOffset = _serializer.float64(obj.heading_gt, buffer, bufferOffset);
    // Serialize message field [speed_gt]
    bufferOffset = _serializer.float64(obj.speed_gt, buffer, bufferOffset);
    // Serialize message field [x_gt]
    bufferOffset = _serializer.float64(obj.x_gt, buffer, bufferOffset);
    // Serialize message field [y_gt]
    bufferOffset = _serializer.float64(obj.y_gt, buffer, bufferOffset);
    // Serialize message field [z_gt]
    bufferOffset = _serializer.float64(obj.z_gt, buffer, bufferOffset);
    return bufferOffset;
  }

  static deserialize(buffer, bufferOffset=[0]) {
    //deserializes a message object of type Object
    let len;
    let data = new Object(null);
    // Deserialize message field [timestamp]
    data.timestamp = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [id]
    data.id = _deserializer.int32(buffer, bufferOffset);
    // Deserialize message field [type]
    data.type = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [size_x]
    data.size_x = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [size_y]
    data.size_y = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [size_z]
    data.size_z = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [heading]
    data.heading = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [speed]
    data.speed = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [x]
    data.x = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [y]
    data.y = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [z]
    data.z = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [longitude]
    data.longitude = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [latitude]
    data.latitude = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [confidence]
    data.confidence = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [type_gt]
    data.type_gt = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [size_x_gt]
    data.size_x_gt = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [size_y_gt]
    data.size_y_gt = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [size_z_gt]
    data.size_z_gt = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [heading_gt]
    data.heading_gt = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [speed_gt]
    data.speed_gt = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [x_gt]
    data.x_gt = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [y_gt]
    data.y_gt = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [z_gt]
    data.z_gt = _deserializer.float64(buffer, bufferOffset);
    return data;
  }

  static getMessageSize(object) {
    return 168;
  }

  static datatype() {
    // Returns string type for a message object
    return 'xperception_msgs/Object';
  }

  static md5sum() {
    //Returns md5sum for a message object
    return '2c44886b8e81c73c66565953388c0ff2';
  }

  static messageDefinition() {
    // Returns full string definition for message
    return `
    
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
    
    `;
  }

  static Resolve(msg) {
    // deep-construct a valid message object instance of whatever was passed in
    if (typeof msg !== 'object' || msg === null) {
      msg = {};
    }
    const resolved = new Object(null);
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

    if (msg.type !== undefined) {
      resolved.type = msg.type;
    }
    else {
      resolved.type = 0
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

    if (msg.heading !== undefined) {
      resolved.heading = msg.heading;
    }
    else {
      resolved.heading = 0.0
    }

    if (msg.speed !== undefined) {
      resolved.speed = msg.speed;
    }
    else {
      resolved.speed = 0.0
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

    if (msg.longitude !== undefined) {
      resolved.longitude = msg.longitude;
    }
    else {
      resolved.longitude = 0.0
    }

    if (msg.latitude !== undefined) {
      resolved.latitude = msg.latitude;
    }
    else {
      resolved.latitude = 0.0
    }

    if (msg.confidence !== undefined) {
      resolved.confidence = msg.confidence;
    }
    else {
      resolved.confidence = 0.0
    }

    if (msg.type_gt !== undefined) {
      resolved.type_gt = msg.type_gt;
    }
    else {
      resolved.type_gt = 0
    }

    if (msg.size_x_gt !== undefined) {
      resolved.size_x_gt = msg.size_x_gt;
    }
    else {
      resolved.size_x_gt = 0.0
    }

    if (msg.size_y_gt !== undefined) {
      resolved.size_y_gt = msg.size_y_gt;
    }
    else {
      resolved.size_y_gt = 0.0
    }

    if (msg.size_z_gt !== undefined) {
      resolved.size_z_gt = msg.size_z_gt;
    }
    else {
      resolved.size_z_gt = 0.0
    }

    if (msg.heading_gt !== undefined) {
      resolved.heading_gt = msg.heading_gt;
    }
    else {
      resolved.heading_gt = 0.0
    }

    if (msg.speed_gt !== undefined) {
      resolved.speed_gt = msg.speed_gt;
    }
    else {
      resolved.speed_gt = 0.0
    }

    if (msg.x_gt !== undefined) {
      resolved.x_gt = msg.x_gt;
    }
    else {
      resolved.x_gt = 0.0
    }

    if (msg.y_gt !== undefined) {
      resolved.y_gt = msg.y_gt;
    }
    else {
      resolved.y_gt = 0.0
    }

    if (msg.z_gt !== undefined) {
      resolved.z_gt = msg.z_gt;
    }
    else {
      resolved.z_gt = 0.0
    }

    return resolved;
    }
};

module.exports = Object;
