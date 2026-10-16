; Auto-generated. Do not edit!


(cl:in-package xperception_msgs-msg)


;//! \htmlinclude ObjectListCombined.msg.html

(cl:defclass <ObjectListCombined> (roslisp-msg-protocol:ros-message)
  ((timestamp
    :reader timestamp
    :initarg :timestamp
    :type cl:float
    :initform 0.0)
   (edge_cloud_id
    :reader edge_cloud_id
    :initarg :edge_cloud_id
    :type cl:integer
    :initform 0)
   (object_list_combined
    :reader object_list_combined
    :initarg :object_list_combined
    :type (cl:vector xperception_msgs-msg:ObjectList)
   :initform (cl:make-array 0 :element-type 'xperception_msgs-msg:ObjectList :initial-element (cl:make-instance 'xperception_msgs-msg:ObjectList))))
)

(cl:defclass ObjectListCombined (<ObjectListCombined>)
  ())

(cl:defmethod cl:initialize-instance :after ((m <ObjectListCombined>) cl:&rest args)
  (cl:declare (cl:ignorable args))
  (cl:unless (cl:typep m 'ObjectListCombined)
    (roslisp-msg-protocol:msg-deprecation-warning "using old message class name xperception_msgs-msg:<ObjectListCombined> is deprecated: use xperception_msgs-msg:ObjectListCombined instead.")))

(cl:ensure-generic-function 'timestamp-val :lambda-list '(m))
(cl:defmethod timestamp-val ((m <ObjectListCombined>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader xperception_msgs-msg:timestamp-val is deprecated.  Use xperception_msgs-msg:timestamp instead.")
  (timestamp m))

(cl:ensure-generic-function 'edge_cloud_id-val :lambda-list '(m))
(cl:defmethod edge_cloud_id-val ((m <ObjectListCombined>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader xperception_msgs-msg:edge_cloud_id-val is deprecated.  Use xperception_msgs-msg:edge_cloud_id instead.")
  (edge_cloud_id m))

(cl:ensure-generic-function 'object_list_combined-val :lambda-list '(m))
(cl:defmethod object_list_combined-val ((m <ObjectListCombined>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader xperception_msgs-msg:object_list_combined-val is deprecated.  Use xperception_msgs-msg:object_list_combined instead.")
  (object_list_combined m))
(cl:defmethod roslisp-msg-protocol:serialize ((msg <ObjectListCombined>) ostream)
  "Serializes a message object of type '<ObjectListCombined>"
  (cl:let ((bits (roslisp-utils:encode-double-float-bits (cl:slot-value msg 'timestamp))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 32) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 40) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 48) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 56) bits) ostream))
  (cl:let* ((signed (cl:slot-value msg 'edge_cloud_id)) (unsigned (cl:if (cl:< signed 0) (cl:+ signed 4294967296) signed)))
    (cl:write-byte (cl:ldb (cl:byte 8 0) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) unsigned) ostream)
    )
  (cl:let ((__ros_arr_len (cl:length (cl:slot-value msg 'object_list_combined))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) __ros_arr_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) __ros_arr_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) __ros_arr_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) __ros_arr_len) ostream))
  (cl:map cl:nil #'(cl:lambda (ele) (roslisp-msg-protocol:serialize ele ostream))
   (cl:slot-value msg 'object_list_combined))
)
(cl:defmethod roslisp-msg-protocol:deserialize ((msg <ObjectListCombined>) istream)
  "Deserializes a message object of type '<ObjectListCombined>"
    (cl:let ((bits 0))
      (cl:setf (cl:ldb (cl:byte 8 0) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 32) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 40) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 48) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 56) bits) (cl:read-byte istream))
    (cl:setf (cl:slot-value msg 'timestamp) (roslisp-utils:decode-double-float-bits bits)))
    (cl:let ((unsigned 0))
      (cl:setf (cl:ldb (cl:byte 8 0) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) unsigned) (cl:read-byte istream))
      (cl:setf (cl:slot-value msg 'edge_cloud_id) (cl:if (cl:< unsigned 2147483648) unsigned (cl:- unsigned 4294967296))))
  (cl:let ((__ros_arr_len 0))
    (cl:setf (cl:ldb (cl:byte 8 0) __ros_arr_len) (cl:read-byte istream))
    (cl:setf (cl:ldb (cl:byte 8 8) __ros_arr_len) (cl:read-byte istream))
    (cl:setf (cl:ldb (cl:byte 8 16) __ros_arr_len) (cl:read-byte istream))
    (cl:setf (cl:ldb (cl:byte 8 24) __ros_arr_len) (cl:read-byte istream))
  (cl:setf (cl:slot-value msg 'object_list_combined) (cl:make-array __ros_arr_len))
  (cl:let ((vals (cl:slot-value msg 'object_list_combined)))
    (cl:dotimes (i __ros_arr_len)
    (cl:setf (cl:aref vals i) (cl:make-instance 'xperception_msgs-msg:ObjectList))
  (roslisp-msg-protocol:deserialize (cl:aref vals i) istream))))
  msg
)
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql '<ObjectListCombined>)))
  "Returns string type for a message object of type '<ObjectListCombined>"
  "xperception_msgs/ObjectListCombined")
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'ObjectListCombined)))
  "Returns string type for a message object of type 'ObjectListCombined"
  "xperception_msgs/ObjectListCombined")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql '<ObjectListCombined>)))
  "Returns md5sum for a message object of type '<ObjectListCombined>"
  "ed983b95b6bbd77ef3f9fc7491a344ae")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql 'ObjectListCombined)))
  "Returns md5sum for a message object of type 'ObjectListCombined"
  "ed983b95b6bbd77ef3f9fc7491a344ae")
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql '<ObjectListCombined>)))
  "Returns full string definition for message of type '<ObjectListCombined>"
  (cl:format cl:nil "~%float64 timestamp~%int32 edge_cloud_id~%ObjectList[] object_list_combined~%================================================================================~%MSG: xperception_msgs/ObjectList~%~%float64     timestamp~%Object[]    sensor_info~%Object[]    object_list~%================================================================================~%MSG: xperception_msgs/Object~%~%float64 	timestamp~%int32 		id ~%int16 		type~%float64 	size_x~%float64 	size_y~%float64 	size_z~%~%float64 	heading~%float64 	speed~%~%float64 	x ~%float64 	y~%float64 	z~%~%float64 	longitude~%float64 	latitude~%~%float64     confidence~%## ground truth~%int16       type_gt~%float64     size_x_gt~%float64     size_y_gt~%float64     size_z_gt~%float64     heading_gt~%float64     speed_gt~%float64     x_gt~%float64     y_gt~%float64     z_gt~%~%~%"))
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql 'ObjectListCombined)))
  "Returns full string definition for message of type 'ObjectListCombined"
  (cl:format cl:nil "~%float64 timestamp~%int32 edge_cloud_id~%ObjectList[] object_list_combined~%================================================================================~%MSG: xperception_msgs/ObjectList~%~%float64     timestamp~%Object[]    sensor_info~%Object[]    object_list~%================================================================================~%MSG: xperception_msgs/Object~%~%float64 	timestamp~%int32 		id ~%int16 		type~%float64 	size_x~%float64 	size_y~%float64 	size_z~%~%float64 	heading~%float64 	speed~%~%float64 	x ~%float64 	y~%float64 	z~%~%float64 	longitude~%float64 	latitude~%~%float64     confidence~%## ground truth~%int16       type_gt~%float64     size_x_gt~%float64     size_y_gt~%float64     size_z_gt~%float64     heading_gt~%float64     speed_gt~%float64     x_gt~%float64     y_gt~%float64     z_gt~%~%~%"))
(cl:defmethod roslisp-msg-protocol:serialization-length ((msg <ObjectListCombined>))
  (cl:+ 0
     8
     4
     4 (cl:reduce #'cl:+ (cl:slot-value msg 'object_list_combined) :key #'(cl:lambda (ele) (cl:declare (cl:ignorable ele)) (cl:+ (roslisp-msg-protocol:serialization-length ele))))
))
(cl:defmethod roslisp-msg-protocol:ros-message-to-list ((msg <ObjectListCombined>))
  "Converts a ROS message object to a list"
  (cl:list 'ObjectListCombined
    (cl:cons ':timestamp (timestamp msg))
    (cl:cons ':edge_cloud_id (edge_cloud_id msg))
    (cl:cons ':object_list_combined (object_list_combined msg))
))
