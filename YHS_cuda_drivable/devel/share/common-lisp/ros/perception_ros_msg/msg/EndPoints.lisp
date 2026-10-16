; Auto-generated. Do not edit!


(cl:in-package perception_ros_msg-msg)


;//! \htmlinclude EndPoints.msg.html

(cl:defclass <EndPoints> (roslisp-msg-protocol:ros-message)
  ((start
    :reader start
    :initarg :start
    :type perception_ros_msg-msg:Point2f
    :initform (cl:make-instance 'perception_ros_msg-msg:Point2f))
   (end
    :reader end
    :initarg :end
    :type perception_ros_msg-msg:Point2f
    :initform (cl:make-instance 'perception_ros_msg-msg:Point2f)))
)

(cl:defclass EndPoints (<EndPoints>)
  ())

(cl:defmethod cl:initialize-instance :after ((m <EndPoints>) cl:&rest args)
  (cl:declare (cl:ignorable args))
  (cl:unless (cl:typep m 'EndPoints)
    (roslisp-msg-protocol:msg-deprecation-warning "using old message class name perception_ros_msg-msg:<EndPoints> is deprecated: use perception_ros_msg-msg:EndPoints instead.")))

(cl:ensure-generic-function 'start-val :lambda-list '(m))
(cl:defmethod start-val ((m <EndPoints>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader perception_ros_msg-msg:start-val is deprecated.  Use perception_ros_msg-msg:start instead.")
  (start m))

(cl:ensure-generic-function 'end-val :lambda-list '(m))
(cl:defmethod end-val ((m <EndPoints>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader perception_ros_msg-msg:end-val is deprecated.  Use perception_ros_msg-msg:end instead.")
  (end m))
(cl:defmethod roslisp-msg-protocol:serialize ((msg <EndPoints>) ostream)
  "Serializes a message object of type '<EndPoints>"
  (roslisp-msg-protocol:serialize (cl:slot-value msg 'start) ostream)
  (roslisp-msg-protocol:serialize (cl:slot-value msg 'end) ostream)
)
(cl:defmethod roslisp-msg-protocol:deserialize ((msg <EndPoints>) istream)
  "Deserializes a message object of type '<EndPoints>"
  (roslisp-msg-protocol:deserialize (cl:slot-value msg 'start) istream)
  (roslisp-msg-protocol:deserialize (cl:slot-value msg 'end) istream)
  msg
)
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql '<EndPoints>)))
  "Returns string type for a message object of type '<EndPoints>"
  "perception_ros_msg/EndPoints")
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'EndPoints)))
  "Returns string type for a message object of type 'EndPoints"
  "perception_ros_msg/EndPoints")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql '<EndPoints>)))
  "Returns md5sum for a message object of type '<EndPoints>"
  "8837e560fc11e0ded6ca2f9a297edb61")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql 'EndPoints)))
  "Returns md5sum for a message object of type 'EndPoints"
  "8837e560fc11e0ded6ca2f9a297edb61")
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql '<EndPoints>)))
  "Returns full string definition for message of type '<EndPoints>"
  (cl:format cl:nil "Point2f start ~%Point2f end ~%~%================================================================================~%MSG: perception_ros_msg/Point2f~%std_msgs/Float32 x ~%std_msgs/Float32 y ~%~%================================================================================~%MSG: std_msgs/Float32~%float32 data~%~%"))
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql 'EndPoints)))
  "Returns full string definition for message of type 'EndPoints"
  (cl:format cl:nil "Point2f start ~%Point2f end ~%~%================================================================================~%MSG: perception_ros_msg/Point2f~%std_msgs/Float32 x ~%std_msgs/Float32 y ~%~%================================================================================~%MSG: std_msgs/Float32~%float32 data~%~%"))
(cl:defmethod roslisp-msg-protocol:serialization-length ((msg <EndPoints>))
  (cl:+ 0
     (roslisp-msg-protocol:serialization-length (cl:slot-value msg 'start))
     (roslisp-msg-protocol:serialization-length (cl:slot-value msg 'end))
))
(cl:defmethod roslisp-msg-protocol:ros-message-to-list ((msg <EndPoints>))
  "Converts a ROS message object to a list"
  (cl:list 'EndPoints
    (cl:cons ':start (start msg))
    (cl:cons ':end (end msg))
))
