
(cl:in-package :asdf)

(defsystem "xperception_msgs-msg"
  :depends-on (:roslisp-msg-protocol :roslisp-utils )
  :components ((:file "_package")
    (:file "Object" :depends-on ("_package_Object"))
    (:file "_package_Object" :depends-on ("_package"))
    (:file "ObjectList" :depends-on ("_package_ObjectList"))
    (:file "_package_ObjectList" :depends-on ("_package"))
    (:file "ObjectListCombined" :depends-on ("_package_ObjectListCombined"))
    (:file "_package_ObjectListCombined" :depends-on ("_package"))
  ))