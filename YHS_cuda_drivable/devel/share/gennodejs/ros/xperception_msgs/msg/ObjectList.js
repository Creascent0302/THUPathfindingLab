// Auto-generated. Do not edit!

// (in-package xperception_msgs.msg)


"use strict";

const _serializer = _ros_msg_utils.Serialize;
const _arraySerializer = _serializer.Array;
const _deserializer = _ros_msg_utils.Deserialize;
const _arrayDeserializer = _deserializer.Array;
const _finder = _ros_msg_utils.Find;
const _getByteLength = _ros_msg_utils.getByteLength;
let Object = require('./Object.js');

//-----------------------------------------------------------

class ObjectList {
  constructor(initObj={}) {
    if (initObj === null) {
      // initObj === null is a special case for deserialization where we don't initialize fields
      this.timestamp = null;
      this.sensor_info = null;
      this.object_list = null;
    }
    else {
      if (initObj.hasOwnProperty('timestamp')) {
        this.timestamp = initObj.timestamp
      }
      else {
        this.timestamp = 0.0;
      }
      if (initObj.hasOwnProperty('sensor_info')) {
        this.sensor_info = initObj.sensor_info
      }
      else {
        this.sensor_info = [];
      }
      if (initObj.hasOwnProperty('object_list')) {
        this.object_list = initObj.object_list
      }
      else {
        this.object_list = [];
      }
    }
  }

  static serialize(obj, buffer, bufferOffset) {
    // Serializes a message object of type ObjectList
    // Serialize message field [timestamp]
    bufferOffset = _serializer.float64(obj.timestamp, buffer, bufferOffset);
    // Serialize message field [sensor_info]
    // Serialize the length for message field [sensor_info]
    bufferOffset = _serializer.uint32(obj.sensor_info.length, buffer, bufferOffset);
    obj.sensor_info.forEach((val) => {
      bufferOffset = Object.serialize(val, buffer, bufferOffset);
    });
    // Serialize message field [object_list]
    // Serialize the length for message field [object_list]
    bufferOffset = _serializer.uint32(obj.object_list.length, buffer, bufferOffset);
    obj.object_list.forEach((val) => {
      bufferOffset = Object.serialize(val, buffer, bufferOffset);
    });
    return bufferOffset;
  }

  static deserialize(buffer, bufferOffset=[0]) {
    //deserializes a message object of type ObjectList
    let len;
    let data = new ObjectList(null);
    // Deserialize message field [timestamp]
    data.timestamp = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [sensor_info]
    // Deserialize array length for message field [sensor_info]
    len = _deserializer.uint32(buffer, bufferOffset);
    data.sensor_info = new Array(len);
    for (let i = 0; i < len; ++i) {
      data.sensor_info[i] = Object.deserialize(buffer, bufferOffset)
    }
    // Deserialize message field [object_list]
    // Deserialize array length for message field [object_list]
    len = _deserializer.uint32(buffer, bufferOffset);
    data.object_list = new Array(len);
    for (let i = 0; i < len; ++i) {
      data.object_list[i] = Object.deserialize(buffer, bufferOffset)
    }
    return data;
  }

  static getMessageSize(object) {
    let length = 0;
    length += 168 * object.sensor_info.length;
    length += 168 * object.object_list.length;
    return length + 16;
  }

  static datatype() {
    // Returns string type for a message object
    return 'xperception_msgs/ObjectList';
  }

  static md5sum() {
    //Returns md5sum for a message object
    return '1412027a16f3faa1ede2a385fdedbb80';
  }

  static messageDefinition() {
    // Returns full string definition for message
    return `
    
    float64     timestamp
    Object[]    sensor_info
    Object[]    object_list
    ================================================================================
    MSG: xperception_msgs/Object
    
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
    const resolved = new ObjectList(null);
    if (msg.timestamp !== undefined) {
      resolved.timestamp = msg.timestamp;
    }
    else {
      resolved.timestamp = 0.0
    }

    if (msg.sensor_info !== undefined) {
      resolved.sensor_info = new Array(msg.sensor_info.length);
      for (let i = 0; i < resolved.sensor_info.length; ++i) {
        resolved.sensor_info[i] = Object.Resolve(msg.sensor_info[i]);
      }
    }
    else {
      resolved.sensor_info = []
    }

    if (msg.object_list !== undefined) {
      resolved.object_list = new Array(msg.object_list.length);
      for (let i = 0; i < resolved.object_list.length; ++i) {
        resolved.object_list[i] = Object.Resolve(msg.object_list[i]);
      }
    }
    else {
      resolved.object_list = []
    }

    return resolved;
    }
};

module.exports = ObjectList;
