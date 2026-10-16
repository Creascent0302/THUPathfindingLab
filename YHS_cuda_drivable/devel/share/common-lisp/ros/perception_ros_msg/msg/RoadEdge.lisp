; Auto-generated. Do not edit!


(cl:in-package perception_ros_msg-msg)


;//! \htmlinclude RoadEdge.msg.html

(cl:defclass <RoadEdge> (roslisp-msg-protocol:ros-message)
  ((roadedge_id
    :reader roadedge_id
    :initarg :roadedge_id
    :type std_msgs-msg:Int32
    :initform (cl:make-instance 'std_msgs-msg:Int32))
   (curve
    :reader curve
    :initarg :curve
    :type perception_ros_msg-msg:Curve
    :initform (cl:make-instance 'perception_ros_msg-msg:Curve))
   (end_points
    :reader end_points
    :initarg :end_points
    :type perception_ros_msg-msg:EndPoints
    :initform (cl:make-instance 'perception_ros_msg-msg:EndPoints))
   (measure_status
    :reader measure_status
    :initarg :measure_status
    :type std_msgs-msg:Int32
    :initform (cl:make-instance 'std_msgs-msg:Int32))
   (confidence
    :reader confidence
    :initarg :confidence
    :type std_msgs-msg:Float32
    :initform (cl:make-instance 'std_msgs-msg:Float32)))
)

(cl:defclass RoadEdge (<RoadEdge>)
  ())

(cl:defmethod cl:initialize-instance :after ((m <RoadEdge>) cl:&rest args)
  (cl:declare (cl:ignorable args))
  (cl:unless (cl:typep m 'RoadEdge)
    (roslisp-msg-protocol:msg-deprecation-warning "using old message class name perception_ros_msg-msg:<RoadEdge> is deprecated: use perception_ros_msg-msg:RoadEdge instead.")))

(cl:ensure-generic-function 'roadedge_id-val :lambda-list '(m))
(cl:defmethod roadedge_id-val ((m <RoadEdge>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader perception_ros_msg-msg:roadedge_id-val is deprecated.  Use perception_ros_msg-msg:roadedge_id instead.")
  (roadedge_id m))

(cl:ensure-generic-function 'curve-val :lambda-list '(m))
(cl:defmethod curve-val ((m <RoadEdge>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader perception_ros_msg-msg:curve-val is deprecated.  Use perception_ros_msg-msg:curve instead.")
  (curve m))

(cl:ensure-generic-function 'end_points-val :lambda-list '(m))
(cl:defmethod end_points-val ((m <RoadEdge>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader perception_ros_msg-msg:end_points-val is deprecated.  Use perception_ros_msg-msg:end_points instead.")
  (end_points m))

(cl:ensure-generic-function 'measure_status-val :lambda-list '(m))
(cl:defmethod measure_status-val ((m <RoadEdge>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader perception_ros_msg-msg:measure_status-val is deprecated.  Use perception_ros_msg-msg:measure_status instead.")
  (measure_status m))

(cl:ensure-generic-function 'confidence-val :lambda-list '(m))
(cl:defmethod confidence-val ((m <RoadEdge>))
  (roslisp-msg-protocol:msg-deprecation-warning "Using old-style slot reader perception_ros_msg-msg:confidence-val is deprecated.  Use perception_ros_msg-msg:confidence instead.")
  (confidence m))
(cl:defmethod roslisp-msg-protocol:serialize ((msg <RoadEdge>) ostream)
  "Serializes a message object of type '<RoadEdge>"
  (roslisp-msg-protocol:serialize (cl:slot-value msg 'roadedge_id) ostream)
  (roslisp-msg-protocol:serialize (cl:slot-value msg 'curve) ostream)
  (roslisp-msg-protocol:serialize (cl:slot-value msg 'end_points) ostream)
  (roslisp-msg-protocol:serialize (cl:slot-value msg 'measure_status) ostream)
  (roslisp-msg-protocol:serialize (cl:slot-value msg 'confidence) ostream)
)
(cl:defmethod roslisp-msg-protocol:deserialize ((msg <RoadEdge>) istream)
  "Deserializes a message object of type '<RoadEdge>"
  (roslisp-msg-protocol:deserialize (cl:slot-value msg 'roadedge_id) istream)
  (roslisp-msg-protocol:deserialize (cl:slot-value msg 'curve) istream)
  (roslisp-msg-protocol:deserialize (cl:slot-value msg 'end_points) istream)
  (roslisp-msg-protocol:deserialize (cl:slot-value msg 'measure_status) istream)
  (roslisp-msg-protocol:deserialize (cl:slot-value msg 'confidence) istream)
  msg
)
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql '<RoadEdge>)))
  "Returns string type for a message object of type '<RoadEdge>"
  "perception_ros_msg/RoadEdge")
(cl:defmethod roslisp-msg-protocol:ros-datatype ((msg (cl:eql 'RoadEdge)))
  "Returns string type for a message object of type 'RoadEdge"
  "perception_ros_msg/RoadEdge")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql '<RoadEdge>)))
  "Returns md5sum for a message object of type '<RoadEdge>"
  "18d874dc862d1be92aa83f7d5c965158")
(cl:defmethod roslisp-msg-protocol:md5sum ((type (cl:eql 'RoadEdge)))
  "Returns md5sum for a message object of type 'RoadEdge"
  "18d874dc862d1be92aa83f7d5c965158")
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql '<RoadEdge>)))
  "Returns full string definition for message of type '<RoadEdge>"
  (cl:format cl:nil "std_msgs/Int32   roadedge_id  ~%Curve            curve ~%EndPoints        end_points ~%std_msgs/Int32   measure_status  ~%std_msgs/Float32 confidence ~%~%================================================================================~%MSG: std_msgs/Int32~%int32 data~%================================================================================~%MSG: perception_ros_msg/Curve~%std_msgs/Float32 x_start ~%std_msgs/Float32 x_end ~%std_msgs/Float32 a ~%std_msgs/Float32 b ~%std_msgs/Float32 c ~%std_msgs/Float32 d ~%================================================================================~%MSG: std_msgs/Float32~%float32 data~%================================================================================~%MSG: perception_ros_msg/EndPoints~%Point2f start ~%Point2f end ~%~%================================================================================~%MSG: perception_ros_msg/Point2f~%std_msgs/Float32 x ~%std_msgs/Float32 y ~%~%~%"))
(cl:defmethod roslisp-msg-protocol:message-definition ((type (cl:eql 'RoadEdge)))
  "Returns full string definition for message of type 'RoadEdge"
  (cl:format cl:nil "std_msgs/Int32   roadedge_id  ~%Curve            curve ~%EndPoints        end_points ~%std_msgs/Int32   measure_status  ~%std_msgs/Float32 confidence ~%~%================================================================================~%MSG: std_msgs/Int32~%int32 data~%================================================================================~%MSG: perception_ros_msg/Curve~%std_msgs/Float32 x_start ~%std_msgs/Float32 x_end ~%std_msgs/Float32 a ~%std_msgs/Float32 b ~%std_msgs/Float32 c ~%std_msgs/Float32 d ~%================================================================================~%MSG: std_msgs/Float32~%float32 data~%================================================================================~%MSG: perception_ros_msg/EndPoints~%Point2f start ~%Point2f end ~%~%================================================================================~%MSG: perception_ros_msg/Point2f~%std_msgs/Float32 x ~%std_msgs/Float32 y ~%~%~%"))
(cl:defmethod roslisp-msg-protocol:serialization-length ((msg <RoadEdge>))
  (cl:+ 0
     (roslisp-msg-protocol:serialization-length (cl:slot-value msg 'roadedge_id))
     (roslisp-msg-protocol:serialization-length (cl:slot-value msg 'curve))
     (roslisp-msg-protocol:serialization-length (cl:slot-value msg 'end_points))
     (roslisp-msg-protocol:serialization-length (cl:slot-value msg 'measure_status))
     (roslisp-msg-protocol:serialization-length (cl:slot-value msg 'confidence))
))
(cl:defmethod roslisp-msg-protocol:ros-message-to-list ((msg <RoadEdge>))
  "Converts a ROS message object to a list"
  (cl:list 'RoadEdge
    (cl:cons ':roadedge_id (roadedge_id msg))
    (cl:cons ':curve (curve msg))
    (cl:cons ':end_points (end_points msg))
    (cl:cons ':measure_status (measure_status msg))
    (cl:cons ':confidence (confidence msg))
))
