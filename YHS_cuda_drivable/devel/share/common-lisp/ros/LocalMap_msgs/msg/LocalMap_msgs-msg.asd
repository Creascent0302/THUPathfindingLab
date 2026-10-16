
(cl:in-package :asdf)

(defsystem "LocalMap_msgs-msg"
  :depends-on (:roslisp-msg-protocol :roslisp-utils )
  :components ((:file "_package")
    (:file "LocalMap" :depends-on ("_package_LocalMap"))
    (:file "_package_LocalMap" :depends-on ("_package"))
    (:file "LocalMap_Element" :depends-on ("_package_LocalMap_Element"))
    (:file "_package_LocalMap_Element" :depends-on ("_package"))
  ))