; Auto-generated. Do not edit!


(cl:in-package perception_ros_msg-msg)


;//! \htmlinclude Objects.msg.html

(cl:defclass <Objects> (roslisp-msg-protocol:ros-message)
  ((objects
    :reader objects
    :initarg :objects
    :type (cl:vector perception_ros_msg-msg:Object)
   :initform (cl:make-array 0 :element-type 'perception_ros_msg-msg:Object :initial-element (cl:make-instance 'perception_ros_msg-msg:Object))))
)

(cl:defclass Objects (<Objects>)
  ())

(cl:defmethod cl:initialize-instance :after ((m <Objects>) cl:&rest args)
  (cl:declare (cl:ignorable args))
  (cl:unless (cl:typep m 'Objects)
    (roslisp-msg-protocol:msg-deprecation-warning "using old message class name perception_ros_msg-msg:<Objects> is deprecated: use perception_ros_msg-msg:Objects instead.")))

(cl:ensure-generic-function 'objects-val :lambda-list '(m))
(cl:defmethod objects-val ((m <Objects>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader perception_ros_msg-msg:objects-val is deprecated.  Use perception_ros_msg-msg:objects instead.")
  (objects m))
(cl:defmethod roslisp-msg-protocol:serialize ((msg <Objects>) ostream)
  "Serializes a message object of type '<Objects>"
  (cl:let ((__ros_arr_len (cl:length (cl:slot-value msg 'objects))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) __ros_arr_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) __ros_arr_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) __ros_arr_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) __ros_arr_len) ostream))
  (cl:map cl:nil #'(cl:lambda (ele) (roslisp-msg-protocol:serialize ele ostream))
   (cl:slot-value msg 'objects))
)
(cl:defmethod roslisp-msg-protocol:deserialize ((msg <Objects>) istream)
  "Deserializes a message object of type '<Objects>"
  (cl:let ((__ros_arr_len 0))
    (cl:setf (cl:ldb (cl:byte 8 0) __ros_arr_len) (cl:read-byte istream))
    (cl:setf (cl:ldb (cl:byte 8 8) __ros_arr_len) (cl:read-byte istream))
    (cl:setf (cl:ldb (cl:byte 8 16) __ros_arr_len) (cl:read-byte istream))
    (cl:setf (cl:ldb (cl:byte 8 24) __ros_arr_len) (cl:read-byte istream))
  (cl:setf (cl:slot-value msg 'objects) (cl:make-array __ros_arr_len))
  (cl:let ((vals (cl:slot-value msg 'objects)))
    (cl:dotimes (i __ros_arr_len)
    (cl:setf (cl:aref vals i) (cl:make-instance 'perception_ros_msg-msg:Object))
  (roslisp-msg-protocol:deserialize (cl:aref vals i) istream))))
  msg
)
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql '<Objects>)))
  "Returns string type for a message object of type '<Objects>"
  "perception_ros_msg/Objects")
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'Objects)))
  "Returns string type for a message object of type 'Objects"
  "perception_ros_msg/Objects")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql '<Objects>)))
  "Returns md5sum for a message object of type '<Objects>"
  "af808db5c14ee51e1e18c9cd6b126641")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql 'Objects)))
  "Returns md5sum for a message object of type 'Objects"
  "af808db5c14ee51e1e18c9cd6b126641")
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql '<Objects>)))
  "Returns full string definition for message of type '<Objects>"
  (cl:format cl:nil "Object[]         objects~%================================================================================~%MSG: perception_ros_msg/Object~%CoreInfo coreinfo~%std_msgs/Bool  hassupplmentinfo ~%SupplementInfo supplementinfo ~%~%================================================================================~%MSG: perception_ros_msg/CoreInfo~%std_msgs/Float64 timestamp~%~%std_msgs/Int32 priority_id~%std_msgs/Float32 exist_confidence ~%Point3f          center ~%Point3f          center_cov ~%Point3f          size ~%Point3f          size_cov ~%Point3f          direction ~%Point3f          direction_cov         ~%std_msgs/Int32   type ~%std_msgs/Float32 type_confidence ~%std_msgs/Int32   attention_type ~%std_msgs/Int32   motion_state~%std_msgs/Int32   lane_pos~%std_msgs/Int32   trakcer_id ~%std_msgs/Float64 age ~%Point3f          velocity ~%Point3f          velocity_cov ~%Point3f          acceleration ~%Point3f          acceleration_cov ~%std_msgs/Float32 angle_velocity ~%std_msgs/Float32 angle_velocity_cov ~%std_msgs/Float32 angle_acceleration ~%std_msgs/Float32 angle_acceleration_cov  ~%Point3f          anchor ~%Point3f          nearest_point ~%~%~%================================================================================~%MSG: std_msgs/Float64~%float64 data~%================================================================================~%MSG: std_msgs/Int32~%int32 data~%================================================================================~%MSG: std_msgs/Float32~%float32 data~%================================================================================~%MSG: perception_ros_msg/Point3f~%std_msgs/Float32 x ~%std_msgs/Float32 y ~%std_msgs/Float32 z ~%================================================================================~%MSG: std_msgs/Bool~%bool data~%================================================================================~%MSG: perception_ros_msg/SupplementInfo~%std_msgs/UInt32     unique_id~%~%Point3f[]           polygon~%std_msgs/Int32      left_point_index ~%std_msgs/Int32      right_point_index ~%~%std_msgs/Int32[]    cloud_indices~%~%std_msgs/Float32[]  latent_types~%std_msgs/Int32      size_type ~%std_msgs/Int32      mode ~%std_msgs/Bool       in_roi ~%std_msgs/Int32      tracking_state~%Point3f             geo_center ~%Point3f             geo_size ~%~%~%~%Point3f[]           trajectory ~%Point3f[]           history_velocity~%std_msgs/Int32[]    history_type ~%std_msgs/Int32      gps_mode ~%Point3d             gps_info ~%~%================================================================================~%MSG: std_msgs/UInt32~%uint32 data~%================================================================================~%MSG: perception_ros_msg/Point3d~%std_msgs/Float64 x ~%std_msgs/Float64 y ~%std_msgs/Float64 z ~%~%~%"))
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql 'Objects)))
  "Returns full string definition for message of type 'Objects"
  (cl:format cl:nil "Object[]         objects~%================================================================================~%MSG: perception_ros_msg/Object~%CoreInfo coreinfo~%std_msgs/Bool  hassupplmentinfo ~%SupplementInfo supplementinfo ~%~%================================================================================~%MSG: perception_ros_msg/CoreInfo~%std_msgs/Float64 timestamp~%~%std_msgs/Int32 priority_id~%std_msgs/Float32 exist_confidence ~%Point3f          center ~%Point3f          center_cov ~%Point3f          size ~%Point3f          size_cov ~%Point3f          direction ~%Point3f          direction_cov         ~%std_msgs/Int32   type ~%std_msgs/Float32 type_confidence ~%std_msgs/Int32   attention_type ~%std_msgs/Int32   motion_state~%std_msgs/Int32   lane_pos~%std_msgs/Int32   trakcer_id ~%std_msgs/Float64 age ~%Point3f          velocity ~%Point3f          velocity_cov ~%Point3f          acceleration ~%Point3f          acceleration_cov ~%std_msgs/Float32 angle_velocity ~%std_msgs/Float32 angle_velocity_cov ~%std_msgs/Float32 angle_acceleration ~%std_msgs/Float32 angle_acceleration_cov  ~%Point3f          anchor ~%Point3f          nearest_point ~%~%~%================================================================================~%MSG: std_msgs/Float64~%float64 data~%================================================================================~%MSG: std_msgs/Int32~%int32 data~%================================================================================~%MSG: std_msgs/Float32~%float32 data~%================================================================================~%MSG: perception_ros_msg/Point3f~%std_msgs/Float32 x ~%std_msgs/Float32 y ~%std_msgs/Float32 z ~%================================================================================~%MSG: std_msgs/Bool~%bool data~%================================================================================~%MSG: perception_ros_msg/SupplementInfo~%std_msgs/UInt32     unique_id~%~%Point3f[]           polygon~%std_msgs/Int32      left_point_index ~%std_msgs/Int32      right_point_index ~%~%std_msgs/Int32[]    cloud_indices~%~%std_msgs/Float32[]  latent_types~%std_msgs/Int32      size_type ~%std_msgs/Int32      mode ~%std_msgs/Bool       in_roi ~%std_msgs/Int32      tracking_state~%Point3f             geo_center ~%Point3f             geo_size ~%~%~%~%Point3f[]           trajectory ~%Point3f[]           history_velocity~%std_msgs/Int32[]    history_type ~%std_msgs/Int32      gps_mode ~%Point3d             gps_info ~%~%================================================================================~%MSG: std_msgs/UInt32~%uint32 data~%================================================================================~%MSG: perception_ros_msg/Point3d~%std_msgs/Float64 x ~%std_msgs/Float64 y ~%std_msgs/Float64 z ~%~%~%"))
(cl:defmethod roslisp-msg-protocol:serialization-length ((msg <Objects>))
  (cl:+ 0
     4 (cl:reduce #'cl:+ (cl:slot-value msg 'objects) :key #'(cl:lambda (ele) (cl:declare (cl:ignorable ele)) (cl:+ (roslisp-msg-protocol:serialization-length ele))))
))
(cl:defmethod roslisp-msg-protocol:ros-message-to-list ((msg <Objects>))
  "Converts a ROS message object to a list"
  (cl:list 'Objects
    (cl:cons ':objects (objects msg))
))
