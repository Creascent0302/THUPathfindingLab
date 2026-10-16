// Auto-generated. Do not edit!

// (in-package LocalMap_msgs.msg)


"use strict";

const _serializer = _ros_msg_utils.Serialize;
const _arraySerializer = _serializer.Array;
const _deserializer = _ros_msg_utils.Deserialize;
const _arrayDeserializer = _deserializer.Array;
const _finder = _ros_msg_utils.Find;
const _getByteLength = _ros_msg_utils.getByteLength;

//-----------------------------------------------------------

class LocalMap_Element {
  constructor(initObj={}) {
    if (initObj === null) {
      // initObj === null is a special case for deserialization where we don't initialize fields
      this.x_id = null;
      this.y_id = null;
      this.driveable_index = null;
      this.driveable_value = null;
      this.ct_x = null;
      this.ct_y = null;
    }
    else {
      if (initObj.hasOwnProperty('x_id')) {
        this.x_id = initObj.x_id
      }
      else {
        this.x_id = 0;
      }
      if (initObj.hasOwnProperty('y_id')) {
        this.y_id = initObj.y_id
      }
      else {
        this.y_id = 0;
      }
      if (initObj.hasOwnProperty('driveable_index')) {
        this.driveable_index = initObj.driveable_index
      }
      else {
        this.driveable_index = false;
      }
      if (initObj.hasOwnProperty('driveable_value')) {
        this.driveable_value = initObj.driveable_value
      }
      else {
        this.driveable_value = 0.0;
      }
      if (initObj.hasOwnProperty('ct_x')) {
        this.ct_x = initObj.ct_x
      }
      else {
        this.ct_x = 0.0;
      }
      if (initObj.hasOwnProperty('ct_y')) {
        this.ct_y = initObj.ct_y
      }
      else {
        this.ct_y = 0.0;
      }
    }
  }

  static serialize(obj, buffer, bufferOffset) {
    // Serializes a message object of type LocalMap_Element
    // Serialize message field [x_id]
    bufferOffset = _serializer.int32(obj.x_id, buffer, bufferOffset);
    // Serialize message field [y_id]
    bufferOffset = _serializer.int32(obj.y_id, buffer, bufferOffset);
    // Serialize message field [driveable_index]
    bufferOffset = _serializer.bool(obj.driveable_index, buffer, bufferOffset);
    // Serialize message field [driveable_value]
    bufferOffset = _serializer.float64(obj.driveable_value, buffer, bufferOffset);
    // Serialize message field [ct_x]
    bufferOffset = _serializer.float64(obj.ct_x, buffer, bufferOffset);
    // Serialize message field [ct_y]
    bufferOffset = _serializer.float64(obj.ct_y, buffer, bufferOffset);
    return bufferOffset;
  }

  static deserialize(buffer, bufferOffset=[0]) {
    //deserializes a message object of type LocalMap_Element
    let len;
    let data = new LocalMap_Element(null);
    // Deserialize message field [x_id]
    data.x_id = _deserializer.int32(buffer, bufferOffset);
    // Deserialize message field [y_id]
    data.y_id = _deserializer.int32(buffer, bufferOffset);
    // Deserialize message field [driveable_index]
    data.driveable_index = _deserializer.bool(buffer, bufferOffset);
    // Deserialize message field [driveable_value]
    data.driveable_value = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [ct_x]
    data.ct_x = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [ct_y]
    data.ct_y = _deserializer.float64(buffer, bufferOffset);
    return data;
  }

  static getMessageSize(object) {
    return 33;
  }

  static datatype() {
    // Returns string type for a message object
    return 'LocalMap_msgs/LocalMap_Element';
  }

  static md5sum() {
    //Returns md5sum for a message object
    return 'df3f78b67932ffce5c991845c7a225e9';
  }

  static messageDefinition() {
    // Returns full string definition for message
    return `
    
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
    const resolved = new LocalMap_Element(null);
    if (msg.x_id !== undefined) {
      resolved.x_id = msg.x_id;
    }
    else {
      resolved.x_id = 0
    }

    if (msg.y_id !== undefined) {
      resolved.y_id = msg.y_id;
    }
    else {
      resolved.y_id = 0
    }

    if (msg.driveable_index !== undefined) {
      resolved.driveable_index = msg.driveable_index;
    }
    else {
      resolved.driveable_index = false
    }

    if (msg.driveable_value !== undefined) {
      resolved.driveable_value = msg.driveable_value;
    }
    else {
      resolved.driveable_value = 0.0
    }

    if (msg.ct_x !== undefined) {
      resolved.ct_x = msg.ct_x;
    }
    else {
      resolved.ct_x = 0.0
    }

    if (msg.ct_y !== undefined) {
      resolved.ct_y = msg.ct_y;
    }
    else {
      resolved.ct_y = 0.0
    }

    return resolved;
    }
};

module.exports = LocalMap_Element;
