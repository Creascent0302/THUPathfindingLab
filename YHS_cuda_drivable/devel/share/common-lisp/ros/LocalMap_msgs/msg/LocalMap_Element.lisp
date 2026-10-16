; Auto-generated. Do not edit!


(cl:in-package LocalMap_msgs-msg)


;//! \htmlinclude LocalMap_Element.msg.html

(cl:defclass <LocalMap_Element> (roslisp-msg-protocol:ros-message)
  ((x_id
    :reader x_id
    :initarg :x_id
    :type cl:integer
    :initform 0)
   (y_id
    :reader y_id
    :initarg :y_id
    :type cl:integer
    :initform 0)
   (driveable_index
    :reader driveable_index
    :initarg :driveable_index
    :type cl:boolean
    :initform cl:nil)
   (driveable_value
    :reader driveable_value
    :initarg :driveable_value
    :type cl:float
    :initform 0.0)
   (ct_x
    :reader ct_x
    :initarg :ct_x
    :type cl:float
    :initform 0.0)
   (ct_y
    :reader ct_y
    :initarg :ct_y
    :type cl:float
    :initform 0.0))
)

(cl:defclass LocalMap_Element (<LocalMap_Element>)
  ())

(cl:defmethod cl:initialize-instance :after ((m <LocalMap_Element>) cl:&rest args)
  (cl:declare (cl:ignorable args))
  (cl:unless (cl:typep m 'LocalMap_Element)
    (roslisp-msg-protocol:msg-deprecation-warning "using old message class name LocalMap_msgs-msg:<LocalMap_Element> is deprecated: use LocalMap_msgs-msg:LocalMap_Element instead.")))

(cl:ensure-generic-function 'x_id-val :lambda-list '(m))
(cl:defmethod x_id-val ((m <LocalMap_Element>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader LocalMap_msgs-msg:x_id-val is deprecated.  Use LocalMap_msgs-msg:x_id instead.")
  (x_id m))

(cl:ensure-generic-function 'y_id-val :lambda-list '(m))
(cl:defmethod y_id-val ((m <LocalMap_Element>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader LocalMap_msgs-msg:y_id-val is deprecated.  Use LocalMap_msgs-msg:y_id instead.")
  (y_id m))

(cl:ensure-generic-function 'driveable_index-val :lambda-list '(m))
(cl:defmethod driveable_index-val ((m <LocalMap_Element>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader LocalMap_msgs-msg:driveable_index-val is deprecated.  Use LocalMap_msgs-msg:driveable_index instead.")
  (driveable_index m))

(cl:ensure-generic-function 'driveable_value-val :lambda-list '(m))
(cl:defmethod driveable_value-val ((m <LocalMap_Element>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader LocalMap_msgs-msg:driveable_value-val is deprecated.  Use LocalMap_msgs-msg:driveable_value instead.")
  (driveable_value m))

(cl:ensure-generic-function 'ct_x-val :lambda-list '(m))
(cl:defmethod ct_x-val ((m <LocalMap_Element>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader LocalMap_msgs-msg:ct_x-val is deprecated.  Use LocalMap_msgs-msg:ct_x instead.")
  (ct_x m))

(cl:ensure-generic-function 'ct_y-val :lambda-list '(m))
(cl:defmethod ct_y-val ((m <LocalMap_Element>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader LocalMap_msgs-msg:ct_y-val is deprecated.  Use LocalMap_msgs-msg:ct_y instead.")
  (ct_y m))
(cl:defmethod roslisp-msg-protocol:serialize ((msg <LocalMap_Element>) ostream)
  "Serializes a message object of type '<LocalMap_Element>"
  (cl:let* ((signed (cl:slot-value msg 'x_id)) (unsigned (cl:if (cl:< signed 0) (cl:+ signed 4294967296) signed)))
    (cl:write-byte (cl:ldb (cl:byte 8 0) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) unsigned) ostream)
    )
  (cl:let* ((signed (cl:slot-value msg 'y_id)) (unsigned (cl:if (cl:< signed 0) (cl:+ signed 4294967296) signed)))
    (cl:write-byte (cl:ldb (cl:byte 8 0) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) unsigned) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) unsigned) ostream)
    )
  (cl:write-byte (cl:ldb (cl:byte 8 0) (cl:if (cl:slot-value msg 'driveable_index) 1 0)) ostream)
  (cl:let ((bits (roslisp-utils:encode-double-float-bits (cl:slot-value msg 'driveable_value))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 32) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 40) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 48) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 56) bits) ostream))
  (cl:let ((bits (roslisp-utils:encode-double-float-bits (cl:slot-value msg 'ct_x))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 32) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 40) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 48) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 56) bits) ostream))
  (cl:let ((bits (roslisp-utils:encode-double-float-bits (cl:slot-value msg 'ct_y))))
    (cl:write-byte (cl:ldb (cl:byte 8 0) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 8) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 16) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 24) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 32) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 40) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 48) bits) ostream)
    (cl:write-byte (cl:ldb (cl:byte 8 56) bits) ostream))
)
(cl:defmethod roslisp-msg-protocol:deserialize ((msg <LocalMap_Element>) istream)
  "Deserializes a message object of type '<LocalMap_Element>"
    (cl:let ((unsigned 0))
      (cl:setf (cl:ldb (cl:byte 8 0) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) unsigned) (cl:read-byte istream))
      (cl:setf (cl:slot-value msg 'x_id) (cl:if (cl:< unsigned 2147483648) unsigned (cl:- unsigned 4294967296))))
    (cl:let ((unsigned 0))
      (cl:setf (cl:ldb (cl:byte 8 0) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) unsigned) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) unsigned) (cl:read-byte istream))
      (cl:setf (cl:slot-value msg 'y_id) (cl:if (cl:< unsigned 2147483648) unsigned (cl:- unsigned 4294967296))))
    (cl:setf (cl:slot-value msg 'driveable_index) (cl:not (cl:zerop (cl:read-byte istream))))
    (cl:let ((bits 0))
      (cl:setf (cl:ldb (cl:byte 8 0) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 32) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 40) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 48) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 56) bits) (cl:read-byte istream))
    (cl:setf (cl:slot-value msg 'driveable_value) (roslisp-utils:decode-double-float-bits bits)))
    (cl:let ((bits 0))
      (cl:setf (cl:ldb (cl:byte 8 0) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 32) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 40) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 48) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 56) bits) (cl:read-byte istream))
    (cl:setf (cl:slot-value msg 'ct_x) (roslisp-utils:decode-double-float-bits bits)))
    (cl:let ((bits 0))
      (cl:setf (cl:ldb (cl:byte 8 0) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 8) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 16) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 24) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 32) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 40) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 48) bits) (cl:read-byte istream))
      (cl:setf (cl:ldb (cl:byte 8 56) bits) (cl:read-byte istream))
    (cl:setf (cl:slot-value msg 'ct_y) (roslisp-utils:decode-double-float-bits bits)))
  msg
)
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql '<LocalMap_Element>)))
  "Returns string type for a message object of type '<LocalMap_Element>"
  "LocalMap_msgs/LocalMap_Element")
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'LocalMap_Element)))
  "Returns string type for a message object of type 'LocalMap_Element"
  "LocalMap_msgs/LocalMap_Element")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql '<LocalMap_Element>)))
  "Returns md5sum for a message object of type '<LocalMap_Element>"
  "df3f78b67932ffce5c991845c7a225e9")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql 'LocalMap_Element)))
  "Returns md5sum for a message object of type 'LocalMap_Element"
  "df3f78b67932ffce5c991845c7a225e9")
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql '<LocalMap_Element>)))
  "Returns full string definition for message of type '<LocalMap_Element>"
  (cl:format cl:nil "~%int32 x_id    #0,1,2,3,4,... east: +x~%int32 y_id    #0,1,2,3,4,... north: +y~%~%bool driveable_index     #0:not  1: driveable~%float64 driveable_value    #[0,1] 1:best~%~%float64 ct_x      # x of the center of this box~%float64 ct_y      # y of the center of this box~%~%"))
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql 'LocalMap_Element)))
  "Returns full string definition for message of type 'LocalMap_Element"
  (cl:format cl:nil "~%int32 x_id    #0,1,2,3,4,... east: +x~%int32 y_id    #0,1,2,3,4,... north: +y~%~%bool driveable_index     #0:not  1: driveable~%float64 driveable_value    #[0,1] 1:best~%~%float64 ct_x      # x of the center of this box~%float64 ct_y      # y of the center of this box~%~%"))
(cl:defmethod roslisp-msg-protocol:serialization-length ((msg <LocalMap_Element>))
  (cl:+ 0
     4
     4
     1
     8
     8
     8
))
(cl:defmethod roslisp-msg-protocol:ros-message-to-list ((msg <LocalMap_Element>))
  "Converts a ROS message object to a list"
  (cl:list 'LocalMap_Element
    (cl:cons ':x_id (x_id msg))
    (cl:cons ':y_id (y_id msg))
    (cl:cons ':driveable_index (driveable_index msg))
    (cl:cons ':driveable_value (driveable_value msg))
    (cl:cons ':ct_x (ct_x msg))
    (cl:cons ':ct_y (ct_y msg))
))
