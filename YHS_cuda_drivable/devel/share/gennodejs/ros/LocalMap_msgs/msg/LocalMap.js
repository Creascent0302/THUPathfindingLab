// Auto-generated. Do not edit!

// (in-package LocalMap_msgs.msg)


"use strict";

const _serializer = _ros_msg_utils.Serialize;
const _arraySerializer = _serializer.Array;
const _deserializer = _ros_msg_utils.Deserialize;
const _arrayDeserializer = _deserializer.Array;
const _finder = _ros_msg_utils.Find;
const _getByteLength = _ros_msg_utils.getByteLength;
let LocalMap_Element = require('./LocalMap_Element.js');

//-----------------------------------------------------------

class LocalMap {
  constructor(initObj={}) {
    if (initObj === null) {
      // initObj === null is a special case for deserialization where we don't initialize fields
      this.timestamp = null;
      this.box_size_x = null;
      this.box_size_y = null;
      this.boxes_num_x = null;
      this.boxes_num_y = null;
      this.map_cx = null;
      this.map_cy = null;
      this.local_map = null;
    }
    else {
      if (initObj.hasOwnProperty('timestamp')) {
        this.timestamp = initObj.timestamp
      }
      else {
        this.timestamp = 0.0;
      }
      if (initObj.hasOwnProperty('box_size_x')) {
        this.box_size_x = initObj.box_size_x
      }
      else {
        this.box_size_x = 0.0;
      }
      if (initObj.hasOwnProperty('box_size_y')) {
        this.box_size_y = initObj.box_size_y
      }
      else {
        this.box_size_y = 0.0;
      }
      if (initObj.hasOwnProperty('boxes_num_x')) {
        this.boxes_num_x = initObj.boxes_num_x
      }
      else {
        this.boxes_num_x = 0;
      }
      if (initObj.hasOwnProperty('boxes_num_y')) {
        this.boxes_num_y = initObj.boxes_num_y
      }
      else {
        this.boxes_num_y = 0;
      }
      if (initObj.hasOwnProperty('map_cx')) {
        this.map_cx = initObj.map_cx
      }
      else {
        this.map_cx = 0.0;
      }
      if (initObj.hasOwnProperty('map_cy')) {
        this.map_cy = initObj.map_cy
      }
      else {
        this.map_cy = 0.0;
      }
      if (initObj.hasOwnProperty('local_map')) {
        this.local_map = initObj.local_map
      }
      else {
        this.local_map = [];
      }
    }
  }

  static serialize(obj, buffer, bufferOffset) {
    // Serializes a message object of type LocalMap
    // Serialize message field [timestamp]
    bufferOffset = _serializer.float64(obj.timestamp, buffer, bufferOffset);
    // Serialize message field [box_size_x]
    bufferOffset = _serializer.float64(obj.box_size_x, buffer, bufferOffset);
    // Serialize message field [box_size_y]
    bufferOffset = _serializer.float64(obj.box_size_y, buffer, bufferOffset);
    // Serialize message field [boxes_num_x]
    bufferOffset = _serializer.int16(obj.boxes_num_x, buffer, bufferOffset);
    // Serialize message field [boxes_num_y]
    bufferOffset = _serializer.int16(obj.boxes_num_y, buffer, bufferOffset);
    // Serialize message field [map_cx]
    bufferOffset = _serializer.float64(obj.map_cx, buffer, bufferOffset);
    // Serialize message field [map_cy]
    bufferOffset = _serializer.float64(obj.map_cy, buffer, bufferOffset);
    // Serialize message field [local_map]
    // Serialize the length for message field [local_map]
    bufferOffset = _serializer.uint32(obj.local_map.length, buffer, bufferOffset);
    obj.local_map.forEach((val) => {
      bufferOffset = LocalMap_Element.serialize(val, buffer, bufferOffset);
    });
    return bufferOffset;
  }

  static deserialize(buffer, bufferOffset=[0]) {
    //deserializes a message object of type LocalMap
    let len;
    let data = new LocalMap(null);
    // Deserialize message field [timestamp]
    data.timestamp = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [box_size_x]
    data.box_size_x = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [box_size_y]
    data.box_size_y = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [boxes_num_x]
    data.boxes_num_x = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [boxes_num_y]
    data.boxes_num_y = _deserializer.int16(buffer, bufferOffset);
    // Deserialize message field [map_cx]
    data.map_cx = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [map_cy]
    data.map_cy = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [local_map]
    // Deserialize array length for message field [local_map]
    len = _deserializer.uint32(buffer, bufferOffset);
    data.local_map = new Array(len);
    for (let i = 0; i < len; ++i) {
      data.local_map[i] = LocalMap_Element.deserialize(buffer, bufferOffset)
    }
    return data;
  }

  static getMessageSize(object) {
    let length = 0;
    length += 33 * object.local_map.length;
    return length + 48;
  }

  static datatype() {
    // Returns string type for a message object
    return 'LocalMap_msgs/LocalMap';
  }

  static md5sum() {
    //Returns md5sum for a message object
    return '40731d50e6751621f77683a18a42cf49';
  }

  static messageDefinition() {
    // Returns full string definition for message
    return `
    
    ##timestamp, ros time or utc time
    float64     timestamp
    
    float64 box_size_x  #size of each box
    float64 box_size_y  #size of each box
    
    int16 boxes_num_x   #how many boxes in x
    int16 boxes_num_y   #how many boxes in y
    
    float64 map_cx  #ct of the local map
    float64 map_cy  #ct of the local map
    
    LocalMap_Element[] local_map
    ================================================================================
    MSG: LocalMap_msgs/LocalMap_Element
    
    int32 x_id    #0,1,2,3,4,... east: +x
    int32 y_id    #0,1,2,3,4,... north: +y
    
    bool driveable_index     #0:not  1: driveable
    float64 driveable_value    #[0,1] 1:best
    
    float64 ct_x      # x of the center of this box
    float64 ct_y      # y of the center of this box
    `;
  }

  static Resolve(msg) {
    // deep-construct a valid message object instance of whatever was passed in
    if (typeof msg !== 'object' || msg === null) {
      msg = {};
    }
    const resolved = new LocalMap(null);
    if (msg.timestamp !== undefined) {
      resolved.timestamp = msg.timestamp;
    }
    else {
      resolved.timestamp = 0.0
    }

    if (msg.box_size_x !== undefined) {
      resolved.box_size_x = msg.box_size_x;
    }
    else {
      resolved.box_size_x = 0.0
    }

    if (msg.box_size_y !== undefined) {
      resolved.box_size_y = msg.box_size_y;
    }
    else {
      resolved.box_size_y = 0.0
    }

    if (msg.boxes_num_x !== undefined) {
      resolved.boxes_num_x = msg.boxes_num_x;
    }
    else {
      resolved.boxes_num_x = 0
    }

    if (msg.boxes_num_y !== undefined) {
      resolved.boxes_num_y = msg.boxes_num_y;
    }
    else {
      resolved.boxes_num_y = 0
    }

    if (msg.map_cx !== undefined) {
      resolved.map_cx = msg.map_cx;
    }
    else {
      resolved.map_cx = 0.0
    }

    if (msg.map_cy !== undefined) {
      resolved.map_cy = msg.map_cy;
    }
    else {
      resolved.map_cy = 0.0
    }

    if (msg.local_map !== undefined) {
      resolved.local_map = new Array(msg.local_map.length);
      for (let i = 0; i < resolved.local_map.length; ++i) {
        resolved.local_map[i] = LocalMap_Element.Resolve(msg.local_map[i]);
      }
    }
    else {
      resolved.local_map = []
    }

    return resolved;
    }
};

module.exports = LocalMap;
