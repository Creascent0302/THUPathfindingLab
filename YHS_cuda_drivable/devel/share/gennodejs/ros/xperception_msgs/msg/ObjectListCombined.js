// Auto-generated. Do not edit!

// (in-package xperception_msgs.msg)


"use strict";

const _serializer = _ros_msg_utils.Serialize;
const _arraySerializer = _serializer.Array;
const _deserializer = _ros_msg_utils.Deserialize;
const _arrayDeserializer = _deserializer.Array;
const _finder = _ros_msg_utils.Find;
const _getByteLength = _ros_msg_utils.getByteLength;
let ObjectList = require('./ObjectList.js');

//-----------------------------------------------------------

class ObjectListCombined {
  constructor(initObj={}) {
    if (initObj === null) {
      // initObj === null is a special case for deserialization where we don't initialize fields
      this.timestamp = null;
      this.edge_cloud_id = null;
      this.object_list_combined = null;
    }
    else {
      if (initObj.hasOwnProperty('timestamp')) {
        this.timestamp = initObj.timestamp
      }
      else {
        this.timestamp = 0.0;
      }
      if (initObj.hasOwnProperty('edge_cloud_id')) {
        this.edge_cloud_id = initObj.edge_cloud_id
      }
      else {
        this.edge_cloud_id = 0;
      }
      if (initObj.hasOwnProperty('object_list_combined')) {
        this.object_list_combined = initObj.object_list_combined
      }
      else {
        this.object_list_combined = [];
      }
    }
  }

  static serialize(obj, buffer, bufferOffset) {
    // Serializes a message object of type ObjectListCombined
    // Serialize message field [timestamp]
    bufferOffset = _serializer.float64(obj.timestamp, buffer, bufferOffset);
    // Serialize message field [edge_cloud_id]
    bufferOffset = _serializer.int32(obj.edge_cloud_id, buffer, bufferOffset);
    // Serialize message field [object_list_combined]
    // Serialize the length for message field [object_list_combined]
    bufferOffset = _serializer.uint32(obj.object_list_combined.length, buffer, bufferOffset);
    obj.object_list_combined.forEach((val) => {
      bufferOffset = ObjectList.serialize(val, buffer, bufferOffset);
    });
    return bufferOffset;
  }

  static deserialize(buffer, bufferOffset=[0]) {
    //deserializes a message object of type ObjectListCombined
    let len;
    let data = new ObjectListCombined(null);
    // Deserialize message field [timestamp]
    data.timestamp = _deserializer.float64(buffer, bufferOffset);
    // Deserialize message field [edge_cloud_id]
    data.edge_cloud_id = _deserializer.int32(buffer, bufferOffset);
    // Deserialize message field [object_list_combined]
    // Deserialize array length for message field [object_list_combined]
    len = _deserializer.uint32(buffer, bufferOffset);
    data.object_list_combined = new Array(len);
    for (let i = 0; i < len; ++i) {
      data.object_list_combined[i] = ObjectList.deserialize(buffer, bufferOffset)
    }
    return data;
  }

  static getMessageSize(object) {
    let length = 0;
    object.object_list_combined.forEach((val) => {
      length += ObjectList.getMessageSize(val);
    });
    return length + 16;
  }

  static datatype() {
    // Returns string type for a message object
    return 'xperception_msgs/ObjectListCombined';
  }

  static md5sum() {
    //Returns md5sum for a message object
    return 'ed983b95b6bbd77ef3f9fc7491a344ae';
  }

  static messageDefinition() {
    // Returns full string definition for message
    return `
    
    float64 timestamp
    int32 edge_cloud_id
    ObjectList[] object_list_combined
    ================================================================================
    MSG: xperception_msgs/ObjectList
    
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
    const resolved = new ObjectListCombined(null);
    if (msg.timestamp !== undefined) {
      resolved.timestamp = msg.timestamp;
    }
    else {
      resolved.timestamp = 0.0
    }

    if (msg.edge_cloud_id !== undefined) {
      resolved.edge_cloud_id = msg.edge_cloud_id;
    }
    else {
      resolved.edge_cloud_id = 0
    }

    if (msg.object_list_combined !== undefined) {
      resolved.object_list_combined = new Array(msg.object_list_combined.length);
      for (let i = 0; i < resolved.object_list_combined.length; ++i) {
        resolved.object_list_combined[i] = ObjectList.Resolve(msg.object_list_combined[i]);
      }
    }
    else {
      resolved.object_list_combined = []
    }

    return resolved;
    }
};

module.exports = ObjectListCombined;
