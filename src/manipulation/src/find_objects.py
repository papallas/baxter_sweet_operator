#!/usr/bin/env python
#The structure of this file was taken from the baxter_stocking_stuffer project by students in Northwestern's MSR program - Josh Marino, Sabeen Admani, Andrew Turchina and Chu-Chu Igbokwe
# Message published - opencv/center_of_object - contains x,y,z coordinates as a Point message

import rospy
import numpy as np
import cv2
import baxter_interface

from std_msgs.msg import String
from sensor_msgs.msg import Image
from geometry_msgs.msg import Point

from cv_bridge import CvBridge, CvBridgeError

from sensor_msgs.msg import Image
import baxter_interface
#from moveit_commander import conversions
from geometry_msgs.msg import PoseStamped, Pose, Point, Quaternion
from std_msgs.msg import Header
import std_srvs.srv
from baxter_core_msgs.srv import SolvePositionIK, SolvePositionIKRequest


#green
low_h  = 60
high_h = 90
low_s  = 85
high_s = 175
low_v  = 70
high_v = 255

#blue
low_h  = 105
high_h = 115
low_s  = 135
high_s = 160
low_v  = 20
high_v = 60


#Create publisher to publish center of object detected
pub = rospy.Publisher('opencv/center_of_object', Point, queue_size = 1)

#Thresholds image and stores position of object in (x,y) coordinates of the camera's frame, with origin at center.
def callback(message):
    #Capturing image of web camera
    bridge = CvBridge()

    cv_image = bridge.imgmsg_to_cv2(message, "bgr8")
    height, width, depth = cv_image.shape

    # CONVERT AND PREPROCESS IMAGE
    hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(hsv, 11, 17, 17)
    edges = cv2.Canny(gray,30,200,apertureSize = 3)
    # DILATE EDGE LINES
    kernel = np.ones((5,5),np.uint8)
    dilation = cv2.dilate(edges,kernel,iterations = 1)
    # FIND 10 LARGEST CONTOURS IN IMAGE
    (cnts, _) = cv2.findContours(dilation, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    cns = sorted(cnts, key = cv2.contourArea, reverse = True)[:10]
    mask = np.zeros(cv_image.shape[:2], dtype="uint8") * 25

    # FIND RECTANGLE IN IMAGE AND SEGMENT - WHAT IF MULTIPLE RECTANGLES?
    for cont in cns:
        peri = cv2.arcLength(cont, True)
        approx = cv2.approxPolyDP(cont, 0.02 * peri, True)
    	if len(approx) == 4:
            #print("square is found")
            cv2.drawContours(cv_image, cont, -1, (0,255,0), thickness = 3)
    	    cv2.drawContours(mask, [cont], -1, 1, -1)
            break

    cv_image = cv2.bitwise_and(cv_image, cv_image, mask=mask)
    cv2.imshow("Box", cv_image)

    # SEGMENTING OF SWEETS

    cv_copy = cv_image
    hsv = cv2.cvtColor(cv_copy, cv2.COLOR_BGR2GRAY)
    hsv = (255 - hsv)

    mask = cv2.inRange(hsv, 1,254)
    hsv = cv2.bitwise_and(hsv, hsv,mask =mask)
    ret,hsv2 = cv2.threshold(hsv,180,255,cv2.THRESH_BINARY)

    contour,hier = cv2.findContours(hsv2,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

    mask2 = np.zeros(cv_image.shape[:2], dtype="uint8") * 25
    for cnt in contour:
        #cv2.drawContours(des,[cnt],0,255,-1)
        cv2.drawContours(mask2, [cnt], 0, 255, -1)

    kernel = np.ones((5,5),np.uint8)
    mask2 = cv2.erode(mask2,kernel,iterations = 1)
    mask2 = cv2.dilate(mask2,kernel,iterations = 2)


    ret,hsv3 = cv2.threshold(hsv,180,255,cv2.THRESH_BINARY)
    hsv3 = (255 - hsv3)
    new_image = cv2.bitwise_and(hsv3, hsv3, mask=mask2)


    sweetcontours,hier = cv2.findContours(mask2,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

    cv2.drawContours(cv_copy, sweetcontours, -1, (255,0,0), thickness = 3)

    print len(sweetcontours)


    cv2.imshow("HSV", new_image)
    cv2.imshow("Edges", hsv3)
    cv2.imshow("Blur", mask2)

    cv2.imshow("Sweets", cv_copy)

        # loop over the contours
    # for c in cnts2:
    #     if cv2.contourArea(c) < 50 and cv2.contourArea(c) > 10:
    #     	# draw the contour and show it
    #     	cv2.drawContours(cv_copy, [c], -1, (0, 255, 0), 2)
    #cv2.drawContours(cv_copy, cnts2, -1, (255,0,0), thickness = 3)

    # for cont in cnts:
    #     cv2.drawContours(cv_copy, [cont], -1, (255,0,0), thickness = 2)
    #     break
    #cv2.drawContours(cv_image, cnts, -1, (0,255,0), thickness = 3)
    #print len(cnts)

    # Setup SimpleBlobDetector parameters.
    # params = cv2.SimpleBlobDetector_Params()
    #
    # # Filter by Area.
    # params.filterByArea = True
    # params.minArea = 5
    #
    # detector = cv2.SimpleBlobDetector(params)
    # #detector = cv2.SimpleBlobDetector_create(params)
    # #detector = cv2.SimpleBlobDetector()
    # keypoints = detector.detect(hsv)
    #
    # im_with_keypoints = cv2.drawKeypoints(hsv, keypoints, np.array([]), \
    # (0,0,255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)




    cv2.waitKey(3)

def getContourStat(contour,image):
  mask = np.zeros(image.shape,dtype="uint8")
  cv2.drawContours(mask, [contour], -1, 255, -1)
  mean,stddev = cv2.meanStdDev(image,mask=mask)
  return mean, stddev, mask

#Subscribes to left hand camera image feed
def main():

    try:
        head_camera = baxter_interface.CameraController("head_camera")
        print ("Attempting to turn off the head camera...")
        head_camera.close()
    except Exception:
        pass

    camera = baxter_interface.CameraController("right_hand_camera")

    camera.open()
    camera.resolution = [1280, 800]
    camera.gain = 0
    camera.exposure = 60

    #Create names for OpenCV images and orient them appropriately
    cv2.namedWindow("Box", 1)
    cv2.namedWindow("Final",2)
    cv2.namedWindow("HSV",3)
    cv2.namedWindow("Blur",4)
    cv2.namedWindow("Thresh",5)
    cv2.namedWindow("Edges",6)




    #Initiate node for left hand camera
    rospy.init_node('right_hand_camera', anonymous=True)

    #Subscribe to left hand camera image
    rospy.Subscriber("/cameras/right_hand_camera/image", Image, callback)

    #Keep from exiting until this node is stopped
    rospy.spin()

if __name__ == '__main__':
     main()