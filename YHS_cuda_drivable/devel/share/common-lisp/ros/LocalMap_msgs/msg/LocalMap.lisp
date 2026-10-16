; Auto-generated. Do not edit!


(cl:in-package LocalMap_msgs-msg)


;//! \htmlinclude LocalMap.msg.html

(cl:defclass <LocalMap> (roslisp-msg-protocol:ros-message)
  ((timestamp
    :reader timestamp
    :initarg :timestamp
    :type cl:float
    :initform 0.0)
   (box_size_x
    :reader box_size_x
    :initarg :box_size_x
    :type cl:float
    :initform 0.0)
   (box_size_y
    :reader box_size_y
    :initarg :box_size_y
    :type cl:float
    :initform 0.0)
   (boxes_num_x
    :reader boxes_num_x
    :initarg :boxes_num_x
    :type cl:fixnum
    :initform 0)
   (boxes_num_y
    :reader boxes_num_y
    :initarg :boxes_num_y
    :type cl:fixnum
    :initform 0)
   (map_cx
    :reader map_cx
    :initarg :map_cx
    :type cl:float
    :initform 0.0)
   (map_cy
    :reader map_cy
    :initarg :map_cy
    :type cl:float
    :initform 0.0)
   (local_map
    :reader local_map
    :initarg :local_map
    :type (cl:vector LocalMap_msgs-msg:LocalMap_Element)
   :initform (cl:make-array 0 :element-type 'LocalMap_msgs-msg:LocalMap_Element :initial-element (cl:make-instance 'LocalMap_msgs-msg:LocalMap_Element))))
)

(cl:defclass LocalMap (<LocalMap>)
  ())

(cl:defmethod cl:initialize-instance :after ((m <LocalMap>) cl:&rest args)
  (cl:declare (cl:ignorable args))
  (cl:unless (cl:typep m 'LocalMap)
    (roslisp-msg-protocol:msg-deprecation-warning "using old message class name LocalMap_msgs-msg:<LocalMap> is deprecated: use LocalMap_msgs-msg:LocalMap instead.")))

(cl:ensure-generic-function 'timestamp-val :lambda-list '(m))
(cl:defmethod timestamp-val ((m <LocalMap>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader LocalMap_msgs-msg:timestamp-val is deprecated.  Use LocalMap_msgs-msg:timestamp instead.")
  (timestamp m))

(cl:ensure-generic-function 'box_size_x-val :lambda-list '(m))
(cl:defmethod box_size_x-val ((m <LocalMap>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader LocalMap_msgs-msg:box_size_x-val is deprecated.  Use LocalMap_msgs-msg:box_size_x instead.")
  (box_size_x m))

(cl:ensure-generic-function 'box_size_y-val :lambda-list '(m))
(cl:defmethod box_size_y-val ((m <LocalMap>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader LocalMap_msgs-msg:box_size_y-val is deprecated.  Use LocalMap_msgs-msg:box_size_y instead.")
  (box_size_y m))

(cl:ensure-generic-function 'boxes_num_x-val :lambda-list '(m))
(cl:defmethod boxes_num_x-val ((m <LocalMap>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader LocalMap_msgs-msg:boxes_num_x-val is deprecated.  Use LocalMap_msgs-msg:boxes_num_x instead.")
  (boxes_num_x m))

(cl:ensure-generic-function 'boxes_num_y-val :lambda-list '(m))
(cl:defmethod boxes_num_y-val ((m <LocalMap>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader LocalMap_msgs-msg:boxes_num_y-val is deprecated.  Use LocalMap_msgs-msg:boxes_num_y instead.")
  (boxes_num_y m))

(cl:ensure-generic-function 'map_cx-val :lambda-list '(m))
(cl:defmethod map_cx-val ((m <LocalMap>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader LocalMap_msgs-msg:map_cx-val is deprecated.  Use LocalMap_msgs-msg:map_cx instead.")
  (map_cx m))

(cl:ensure-generic-function 'map_cy-val :lambda-list '(m))
(cl:defmethod map_cy-val ((m <LocalMap>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader LocalMap_msgs-msg:map_cy-val is deprecated.  Use LocalMap_msgs-msg:map_cy instead.")
  (map_cy m))

(cl:ensure-generic-function 'local_map-val :lambda-list '(m))
(cl:defmethod local_map-val ((m <LocalMap>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader LocalMap_msgs-msg:local_map-val is deprecated.  Use LocalMap_msgs-msg:local_map instead.")
  (local_map m))
(cl:defmethod roslisp-msg-protocol:serialize ((msg <LocalMap>) ostream)
  "Serializes a message object of type '<LocalMap>"
  (cl:let ((bits (roslisp-utils:encode-double-float-bits (cl:slot-value msg 'timestamp))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 32) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 40) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 48) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 56) bits) ostream))
  (cl:let ((bits (roslisp-utils:encode-double-float-bits (cl:slot-value msg 'box_size_x))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 32) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 40) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 48) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 56) bits) ostream))
  (cl:let ((bits (roslisp-utils:encode-double-float-bits (cl:slot-value msg 'box_size_y))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 32) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 40) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 48) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 56) bits) ostream))
  (cl:let* ((signed (cl:slot-value msg 'boxes_num_x)) (unsigned (cl:if (cl:< signed 0) (cl:+ signed 65536) signed)))
    (cl:write-byte (cl:ldb (cl:byte 8 0) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) unsigned) ostream)
    )
  (cl:let* ((signed (cl:slot-value msg 'boxes_num_y)) (unsigned (cl:if (cl:< signed 0) (cl:+ signed 65536) signed)))
    (cl:write-byte (cl:ldb (cl:byte 8 0) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) unsigned) ostream)
    )
  (cl:let ((bits (roslisp-utils:encode-double-float-bits (cl:slot-value msg 'map_cx))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 32) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 40) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 48) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 56) bits) ostream))
  (cl:let ((bits (roslisp-utils:encode-double-float-bits (cl:slot-value msg 'map_cy))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 32) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 40) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 48) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 56) bits) ostream))
  (cl:let ((__ros_arr_len (cl:length (cl:slot-value msg 'local_map))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) __ros_arr_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) __ros_arr_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) __ros_arr_len) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) __ros_arr_len) ostream))
  (cl:map cl:nil #'(cl:lambda (ele) (roslisp-msg-protocol:serialize ele ostream))
   (cl:slot-value msg 'local_map))
)
(cl:defmethod roslisp-msg-protocol:deserialize ((msg <LocalMap>) istream)
  "Deserializes a message object of type '<LocalMap>"
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
    (cl:let ((bits 0))
      (cl:setf (cl:ldb (cl:byte 8 0) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 32) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 40) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 48) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 56) bits) (cl:read-byte istream))
    (cl:setf (cl:slot-value msg 'box_size_x) (roslisp-utils:decode-double-float-bits bits)))
    (cl:let ((bits 0))
      (cl:setf (cl:ldb (cl:byte 8 0) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 32) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 40) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 48) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 56) bits) (cl:read-byte istream))
    (cl:setf (cl:slot-value msg 'box_size_y) (roslisp-utils:decode-double-float-bits bits)))
    (cl:let ((unsigned 0))
      (cl:setf (cl:ldb (cl:byte 8 0) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) unsigned) (cl:read-byte istream))
      (cl:setf (cl:slot-value msg 'boxes_num_x) (cl:if (cl:< unsigned 32768) unsigned (cl:- unsigned 65536))))
    (cl:let ((unsigned 0))
      (cl:setf (cl:ldb (cl:byte 8 0) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) unsigned) (cl:read-byte istream))
      (cl:setf (cl:slot-value msg 'boxes_num_y) (cl:if (cl:< unsigned 32768) unsigned (cl:- unsigned 65536))))
    (cl:let ((bits 0))
      (cl:setf (cl:ldb (cl:byte 8 0) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 32) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 40) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 48) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 56) bits) (cl:read-byte istream))
    (cl:setf (cl:slot-value msg 'map_cx) (roslisp-utils:decode-double-float-bits bits)))
    (cl:let ((bits 0))
      (cl:setf (cl:ldb (cl:byte 8 0) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 32) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 40) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 48) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 56) bits) (cl:read-byte istream))
    (cl:setf (cl:slot-value msg 'map_cy) (roslisp-utils:decode-double-float-bits bits)))
  (cl:let ((__ros_arr_len 0))
    (cl:setf (cl:ldb (cl:byte 8 0) __ros_arr_len) (cl:read-byte istream))
    (cl:setf (cl:ldb (cl:byte 8 8) __ros_arr_len) (cl:read-byte istream))
    (cl:setf (cl:ldb (cl:byte 8 16) __ros_arr_len) (cl:read-byte istream))
    (cl:setf (cl:ldb (cl:byte 8 24) __ros_arr_len) (cl:read-byte istream))
  (cl:setf (cl:slot-value msg 'local_map) (cl:make-array __ros_arr_len))
  (cl:let ((vals (cl:slot-value msg 'local_map)))
    (cl:dotimes (i __ros_arr_len)
    (cl:setf (cl:aref vals i) (cl:make-instance 'LocalMap_msgs-msg:LocalMap_Element))
  (roslisp-msg-protocol:deserialize (cl:aref vals i) istream))))
  msg
)
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql '<LocalMap>)))
  "Returns string type for a message object of type '<LocalMap>"
  "LocalMap_msgs/LocalMap")
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'LocalMap)))
  "Returns string type for a message object of type 'LocalMap"
  "LocalMap_msgs/LocalMap")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql '<LocalMap>)))
  "Returns md5sum for a message object of type '<LocalMap>"
  "40731d50e6751621f77683a18a42cf49")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql 'LocalMap)))
  "Returns md5sum for a message object of type 'LocalMap"
  "40731d50e6751621f77683a18a42cf49")
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql '<LocalMap>)))
  "Returns full string definition for message of type '<LocalMap>"
  (cl:format cl:nil "~%##timestamp, ros time or utc time~%float64     timestamp~%~%float64 box_size_x  #size of each box~%float64 box_size_y  #size of each box~%~%int16 boxes_num_x   #how many boxes in x~%int16 boxes_num_y   #how many boxes in y~%~%float64 map_cx  #ct of the local map~%float64 map_cy  #ct of the local map~%~%LocalMap_Element[] local_map~%================================================================================~%MSG: LocalMap_msgs/LocalMap_Element~%~%int32 x_id    #0,1,2,3,4,... east: +x~%int32 y_id    #0,1,2,3,4,... north: +y~%~%bool driveable_index     #0:not  1: driveable~%float64 driveable_value    #[0,1] 1:best~%~%float64 ct_x      # x of the center of this box~%float64 ct_y      # y of the center of this box~%~%"))
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql 'LocalMap)))
  "Returns full string definition for message of type 'LocalMap"
  (cl:format cl:nil "~%##timestamp, ros time or utc time~%float64     timestamp~%~%float64 box_size_x  #size of each box~%float64 box_size_y  #size of each box~%~%int16 boxes_num_x   #how many boxes in x~%int16 boxes_num_y   #how many boxes in y~%~%float64 map_cx  #ct of the local map~%float64 map_cy  #ct of the local map~%~%LocalMap_Element[] local_map~%================================================================================~%MSG: LocalMap_msgs/LocalMap_Element~%~%int32 x_id    #0,1,2,3,4,... east: +x~%int32 y_id    #0,1,2,3,4,... north: +y~%~%bool driveable_index     #0:not  1: driveable~%float64 driveable_value    #[0,1] 1:best~%~%float64 ct_x      # x of the center of this box~%float64 ct_y      # y of the center of this box~%~%"))
(cl:defmethod roslisp-msg-protocol:serialization-length ((msg <LocalMap>))
  (cl:+ 0
     8
     8
     8
     2
     2
     8
     8
     4 (cl:reduce #'cl:+ (cl:slot-value msg 'local_map) :key #'(cl:lambda (ele) (cl:declare (cl:ignorable ele)) (cl:+ (roslisp-msg-protocol:serialization-length ele))))
))
(cl:defmethod roslisp-msg-protocol:ros-message-to-list ((msg <LocalMap>))
  "Converts a ROS message object to a list"
  (cl:list 'LocalMap
    (cl:cons ':timestamp (timestamp msg))
    (cl:cons ':box_size_x (box_size_x msg))
    (cl:cons ':box_size_y (box_size_y msg))
    (cl:cons ':boxes_num_x (boxes_num_x msg))
    (cl:cons ':boxes_num_y (boxes_num_y msg))
    (cl:cons ':map_cx (map_cx msg))
    (cl:cons ':map_cy (map_cy msg))
    (cl:cons ':local_map (local_map msg))
))
