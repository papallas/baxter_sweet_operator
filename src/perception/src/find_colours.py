#!/usr/bin/env python

# data for blue Sweets
# 1,48,139,37,255,255,255,6

# data for green sweets
# 1,46,61,0,106,198,218,5

import rospy
import numpy as np
import cv2
import baxter_interface
import math

from std_msgs.msg import String
from sensor_msgs.msg import Image
from geometry_msgs.msg import Point

from manipulation.srv import *
from manipulation.srv import LookForSweets
from collections import OrderedDict

from cv_bridge import CvBridge, CvBridgeError

import tf

from sensor_msgs.msg import Image
import baxter_interface
#from moveit_commander import conversions
from geometry_msgs.msg import PoseStamped, Pose, Point, Quaternion, PointStamped
from std_msgs.msg import Header
import std_srvs.srv
from baxter_core_msgs.srv import SolvePositionIK, SolvePositionIKRequest

sweetArea = 0
backgroundImage = 0

global totalSweets
global centrelist
global PAGECENTREPOINT
PAGECENTREPOINT = 0

# RED, GREEN, BLUE
global colourAmounts

global sweetarea
global foundsquare

global enableAnalyse
enableAnalyse = True

global pointlist
global tl

global anglelist

global pageCentre

global sweetMask
sweetMask = "nil"

#Thresholds image and stores position of object in (x,y) coordinates of the camera's frame, with origin at center.
def callback(message):
    #Capturing image of web camera
    br = CvBridge()	# Create a black image, a window

    #img = br.imgmsg_to_cv2(message, desired_encoding="passthrough")
    cv_image = br.imgmsg_to_cv2(message, "bgr8")
    # Take each frame
    simg = cv2.GaussianBlur(cv_image,(5,5),0)

    global PAGECENTREPOINT

    if enableAnalyse == True:
        # print lab
        tl = tf.TransformListener()

        try:
            tl.waitForTransform("right_hand_camera", "torso", rospy.Time(0), rospy.Duration(10))
            # (trans,rot) = tl.lookupTransform('right_hand_camera', 'torso', rospy.Time(0))
        except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
            pass

        # find sweet rectangular area for sweets
        global sweetarea, foundsquare, pageCentre, tl, sweetMask
        foundsquare = False
        if (sweetMask == "nil"):
            sweetMask, areafound = find_background(simg)
            print "Finding sweet area"

        #with open('colours.data', 'a') as file:

        # Convert BGR to HS
        sweetarea = cv2.bitwise_and(simg, simg, mask=sweetMask)

        #cv2.imshow("sweetMask", sweetarea)

        circleimg = cv2.cvtColor(sweetarea, cv2.COLOR_BGR2GRAY);

        edges = cv2.Canny(circleimg,50,200,apertureSize = 3)

        kernel = np.ones((5,5),np.uint8)
        dilation = cv2.dilate(edges,kernel,iterations = 1)

        #cv2.imshow("dilated image", dilation)

        dilation2 = dilation

        contours,hier = cv2.findContours(dilation,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        #cv2.drawContours(cv_image, contours, -1, (255,0,0), 3)

        mask = np.zeros(circleimg.shape,dtype="uint8")
        centrepoints = []
        for cont in contours:
            area = cv2.contourArea(cont)
            # cut out large border of page contours
            if area < 50000:
                cv2.drawContours(mask, [cont], -1, 255, -1)

        mask2 = cv2.erode(mask, None, iterations=1)

        #cv2.imshow("ERODED MASK",mask2)

        mask = mask2

        cv2.imshow("MASK 2", mask2)

        newcontours,newhier = cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        # cv2.drawContours(cv_image, newcontours, -1, (255,0,0), 3)

        global colourAmounts
        colourAmounts = [0,0,0]

        redcentres = []
        greencentres = []
        bluecentres = []
        redangles = []
        greenangles = []
        blueangles = []

        greenWeights = np.array([366.1219, -463.8519, 63.0028, 8.5000])

        blueWeights = np.array([-42.2808, 25.3629, 30.6613, 6.7000])

        redWeights = np.array([3.4025, 11.9616, -17.8766, 6.9000])



        overallmask = np.zeros(circleimg.shape,dtype="uint8")

        extracontours = []
        for cont in newcontours:
            area = cv2.contourArea(cont)
            # PROCESSING COLLISION TYPES
            if 1500 < area:
                print area

                print "Collision area: ",area
                #peri = cv2.arcLength(cont, True)
                #approx = cv2.approxPolyDP(cont, 0.02 * peri, True)

                rect = cv2.minAreaRect(cont)
                box = cv2.cv.BoxPoints(rect)
                box = np.int0(box)

                x,y,w,h = cv2.boundingRect(cont)
                #cv2.rectangle(img,(x,y),(x+w,y+h),(0,255,0),2)

                #print rect[1][0]
                print "Box width = ",rect[1][0],", box height = ",rect[1][1]

                #cv2.drawContours(cv_image,[newbox],0,(0,255,0),3)


                collisionmask = np.zeros(circleimg.shape,dtype="uint8")
                #cv2.drawContours(collisionmask, [newbox], -1, 255, -1)
                cv2.rectangle(cv_image,(x,y),(x+w,y+h),(0,255,0),2)

                kernel1 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (20, 20))

                #kernel2 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 5))
                morph = cv2.morphologyEx(mask2, cv2.MORPH_OPEN, kernel1)

                #morph = cv2.morphologyEx(morph, cv2.MORPH_GRADIENT, kernel2)
                dist = cv2.distanceTransform(morph, cv2.cv.CV_DIST_L2, cv2.cv.CV_DIST_MASK_PRECISE)

                cv2.imshow('dist', dist)

                borderSize = 50
                distborder = cv2.copyMakeBorder(dist, borderSize, borderSize, borderSize, borderSize,
                                                cv2.BORDER_CONSTANT | cv2.BORDER_ISOLATED, 0)
                gap = 10
                kernel2 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (50, 30))
                kernel2 = cv2.copyMakeBorder(kernel2, gap, gap, gap, gap,
                                                cv2.BORDER_CONSTANT | cv2.BORDER_ISOLATED, 0)
                distTempl = cv2.distanceTransform(kernel2, cv2.cv.CV_DIST_L2, cv2.cv.CV_DIST_MASK_PRECISE)
                cv2.imshow('disttempl', distTempl)

                nxcor = cv2.matchTemplate(distborder, distTempl, cv2.TM_CCOEFF_NORMED)
                mn, mx, _, _ = cv2.minMaxLoc(nxcor)
                th, peaks = cv2.threshold(nxcor, mx*0.5, 255, cv2.THRESH_BINARY)
                peaks8u = cv2.convertScaleAbs(peaks)
                contours, hierarchy = cv2.findContours(peaks8u, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
                peaks8u = cv2.convertScaleAbs(peaks)    # to use as mask
                for i in range(len(contours)):
                    x, y, w, h = cv2.boundingRect(contours[i])
                    _, mx, _, mxloc = cv2.minMaxLoc(dist[y:y+h, x:x+w], peaks8u[y:y+h, x:x+w])
                    cv2.circle(cv_image, (int(mxloc[0]+x), int(mxloc[1]+y)), int(mx), (255, 0, 0), 2)
                    cv2.rectangle(cv_image, (x, y), (x+w, y+h), (0, 255, 255), 2)
                    cv2.drawContours(cv_image, contours, i, (0, 0, 255), 2)

                cv2.imshow('circles', cv_image)


        #newcontours,newhier = cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

        #         gap = 20
        #
        #         width = 0
        #         height = 0
        #         if rect[1][0] < rect[1][1]:
        #             width = rect[1][0]
        #             height = rect[1][1]
        #         # if rect[1][0] > rect[1][1]:
        #         #     longside = rect[1][0]
        #         #     shortside = rect[1][1]
        #
        #             newrect = ((rect[0][0]+width/2+gap, rect[0][1]), (rect[1][0], height/2), rect[2])
        #             newbox = cv2.cv.BoxPoints(newrect)
        #             newbox = np.int0(newbox)
        #
        #             collisionmask = np.zeros(circleimg.shape,dtype="uint8")
        #             cv2.drawContours(collisionmask, [newbox], -1, 255, -1)
        #
        #             #cv2.drawContours(cv_image,[newbox],0,(0,0,0),2)
        #
        #
        #             overallmask = overallmask + collisionmask
        #
        #             collisionimage = cv2.bitwise_and(simg, simg, mask=collisionmask)
        #             ret,thresh5 = cv2.threshold(collisionimage,127,255,cv2.THRESH_TOZERO_INV)
        #             edges = cv2.Canny(thresh5,50,200,apertureSize = 3)
        #             dilation = cv2.dilate(edges,kernel,iterations = 1)
        #             contours,hier = cv2.findContours(dilation,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        #
        #             for i in range(0,len(contours)):
        #                 if 50 < (cv2.arcLength(contours[i], True)) < 300:
        #                     extracontours.append(contours[i])
        #
        #             newrect = ((rect[0][0]-width/2-gap, rect[0][1]), (rect[1][0], height/2), rect[2])
        #             newbox = cv2.cv.BoxPoints(newrect)
        #             newbox = np.int0(newbox)
        #
        #             collisionmask = np.zeros(circleimg.shape,dtype="uint8")
        #             cv2.drawContours(collisionmask, [newbox], -1, 255, -1)
        #
        #             #cv2.drawContours(cv_image,[newbox],0,(0,0,0),2)
        #
        #
        #             overallmask = overallmask + collisionmask
        #
        #             collisionimage = cv2.bitwise_and(simg, simg, mask=collisionmask)
        #             ret,thresh5 = cv2.threshold(collisionimage,127,255,cv2.THRESH_TOZERO_INV)
        #             edges = cv2.Canny(thresh5,50,200,apertureSize = 3)
        #             dilation = cv2.dilate(edges,kernel,iterations = 1)
        #             contours,hier = cv2.findContours(dilation,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        #
        #             for i in range(0,len(contours)):
        #                 if 50 < (cv2.arcLength(contours[i], True)) < 300:
        #                     extracontours.append(contours[i])
        #
        #
        #         if rect[1][0] > rect[1][1]:
        #             width = rect[1][0]
        #             height = rect[1][1]
        #         # if rect[1][0] > rect[1][1]:
        #         #     longside = rect[1][0]
        #         #     shortside = rect[1][1]
        #
        #             #rect.center.y = rect[0][1] + height/2
        #             #rect.set_width(width/2)
        #             newrect = ((rect[0][0], rect[0][1]+height/2+gap), (width/2, rect[1][1]), rect[2])
        #             newbox = cv2.cv.BoxPoints(newrect)
        #             newbox = np.int0(newbox)
        #
        #             collisionmask = np.zeros(circleimg.shape,dtype="uint8")
        #             cv2.drawContours(collisionmask, [newbox], -1, 255, -1)
        #
        #             #cv2.drawContours(cv_image,[newbox],0,(0,0,0),2)
        #
        #             overallmask = overallmask + collisionmask
        #
        #             collisionimage = cv2.bitwise_and(simg, simg, mask=collisionmask)
        #             ret,thresh5 = cv2.threshold(collisionimage,127,255,cv2.THRESH_TOZERO_INV)
        #             edges = cv2.Canny(thresh5,50,200,apertureSize = 3)
        #             dilation = cv2.dilate(edges,kernel,iterations = 1)
        #             contours,hier = cv2.findContours(dilation,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        #
        #             for i in range(0,len(contours)):
        #                 if 50 < (cv2.arcLength(contours[i], True)) < 300:
        #                     extracontours.append(contours[i])
        #
        #             newrect = ((rect[0][0], rect[0][1]-height/2-gap), (width/2, rect[1][1]), rect[2])
        #             newbox = cv2.cv.BoxPoints(newrect)
        #             newbox = np.int0(newbox)
        #
        #             collisionmask = np.zeros(circleimg.shape,dtype="uint8")
        #             cv2.drawContours(collisionmask, [newbox], -1, 255, -1)
        #
        #             collisionimage = cv2.bitwise_and(simg, simg, mask=collisionmask)
        #             ret,thresh5 = cv2.threshold(collisionimage,127,255,cv2.THRESH_TOZERO_INV)
        #             edges = cv2.Canny(thresh5,50,200,apertureSize = 3)
        #             dilation = cv2.dilate(edges,kernel,iterations = 1)
        #             contours,hier = cv2.findContours(dilation,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        #
        #             cv2.imshow("contourdilation", dilation)
        #
        #             for i in range(0,len(contours)):
        #                 print (cv2.contourArea(contours[i]))
        #                 print (cv2.arcLength(contours[i], True))
        #
        #                 #if cv2.contourArea(contours[i]) > 30:
        #                 #    extracontours.append(contours[i])
        #                 if 50 < (cv2.arcLength(contours[i], True)) < 300:
        #                     extracontours.append(contours[i])
        #
        #             #cv2.drawContours(cv_image,[newbox],0,(0,0,0),2)
        #
        #
        #             overallmask = overallmask + collisionmask
        #
        # for i in range(0,len(extracontours)):
        #     newcontours.append(extracontours[i])


        for cont in newcontours:
            area = cv2.contourArea(cont)
            # cut out large border of page contours
            #print area

            if 500 < area < 1500:
                print "Sweet area: ",area

                newmask = np.zeros(circleimg.shape,dtype="uint8")
                cv2.drawContours(newmask, [cont], -1, 255, -1)

                newmask = cv2.erode(newmask, None, iterations=1)
                mean = cv2.mean(cv_image, mask=newmask)[:3]

                meanarray = np.array([mean[0], mean[1], mean[2], 1])

                rows,cols = cv_image.shape[:2]
                [vx,vy,x,y] = cv2.fitLine(cont, cv2.cv.CV_DIST_L2,0,0.01,0.01)
                lefty = int((-x*vy/vx) + y)
                righty = int(((cols-x)*vy/vx)+y)
                M = cv2.moments(cont)
                cx = int(M['m10']/M['m00'])
                cy = int(M['m01']/M['m00'])

                if np.dot(redWeights,meanarray) < 0:
                    #print "This is red"
                    cv2.drawContours(cv_image, [cont], -1, (0,0,255), 3)
                    colourAmounts[0] = colourAmounts[0] + 1
                    redangles.append(math.atan2(righty - lefty, cols-1 - 0))
                    redcentres.append((cx, cy))

                elif np.dot(greenWeights,meanarray) < 0:
                    #print "This is green"
                    cv2.drawContours(cv_image, [cont], -1, (0,255,0), 3)
                    colourAmounts[1] = colourAmounts[1] + 1
                    greenangles.append(math.atan2(righty - lefty, cols-1 - 0))
                    greencentres.append((cx, cy))

                elif np.dot(blueWeights,meanarray) < 0:
                    #print "This is blue"
                    cv2.drawContours(cv_image, [cont], -1, (255,0,0), 3)
                    colourAmounts[2] = colourAmounts[2] + 1
                    blueangles.append(math.atan2(righty - lefty, cols-1 - 0))
                    bluecentres.append((cx, cy))



                print rect



                #cv2.drawContours(cv_image,[box],0,(0,0,255),2)

                #cv2.drawContours(cv_image, [approx], -1, (0,0,0), 3)

        collisionimage = cv2.bitwise_and(simg, simg, mask=overallmask)
        for i in range(0,len(extracontours)):
            cv2.drawContours(collisionimage, [extracontours[i]], -1, (255,0,0), 3)
        cv2.imshow("CONTOUR IMAGE: ", collisionimage)


        centres = []
        angles = []

        for i in range(0,len(redcentres)):
            centres.append(redcentres[i])
            angles.append(redangles[i])
        for i in range(0,len(greencentres)):
            centres.append(greencentres[i])
            angles.append(greenangles[i])
        for i in range(0,len(bluecentres)):
            centres.append(bluecentres[i])
            angles.append(blueangles[i])

        cv2.imshow("IMAGE",cv_image)

        global enableAnalyse
        enableAnalyse = False

        overallcentres = centres
        centrepoints = []
        for centre in overallcentres:
            [x, y] = pixel_to_baxter(centre[0], centre[1])
            #newcoords.append((x,y))
            point = PointStamped()
            point.header.frame_id = "right_hand_camera"
            point.point.x = x
            point.point.y = y
            point.point.z = 0.45
            centrepoints.append(point)

        global pointlist
        pointlist = []
        # global collisionslist
        # collisionslist = []
        global anglelist
        anglelist = []


        for i in range(0,len(centrepoints)):
            newpoint = tl.transformPoint("torso", centrepoints[i])
            pointlist.append(newpoint)
            anglelist.append(angles[i])

        print anglelist

    k = cv2.waitKey(1)
    global enableAnalyse
    enableAnalyse = False


    pub = rospy.Publisher("pageCenre", PointStamped, queue_size=10)
    pub.publish(PAGECENTREPOINT)



def find_background(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    #gray = cv2.bilateralFilter(hsv, 11, 17, 17)
    edges = cv2.Canny(hsv,30,200,apertureSize = 3)
    # DILATE EDGE LINES
    kernel = np.ones((5,5),np.uint8)
    dilation = cv2.dilate(edges,kernel,iterations = 1)
    # FIND 10 LARGEST CONTOURS IN IMAGE
    (cnts, _) = cv2.findContours(dilation, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    cns = sorted(cnts, key = cv2.contourArea, reverse = True)[:10]
    mask = np.zeros(img.shape[:2], dtype="uint8") * 25

    global foundsquare, pageCentre, tl, PAGECENTREPOINT

    foundsquare = False
    # FIND RECTANGLE IN IMAGE AND SEGMENT - WHAT IF MULTIPLE RECTANGLES?
    for cont in cns:
        peri = cv2.arcLength(cont, True)
        approx = cv2.approxPolyDP(cont, 0.02 * peri, True)
        #cv2.drawContours(img, [cont], -1, (255,0,0), 3)
        if len(approx) == 4:
            if cv2.contourArea(cont) > 70000:
                foundsquare = True
                cv2.drawContours(mask, [cont], -1, 1, -1)

                M = cv2.moments(cont)
                cx = int(M['m10']/M['m00'])
                cy = int(M['m01']/M['m00'])
                [x, y] = pixel_to_baxter(cx, cy)
                #newcoords.append((x,y))
                point = PointStamped()
                point.header.frame_id = "right_hand_camera"
                point.point.x = x
                point.point.y = y
                point.point.z = 0.45
                PAGECENTREPOINT = tl.transformPoint("torso", point)
                pageCentre = [PAGECENTREPOINT.point.x, PAGECENTREPOINT.point.y, PAGECENTREPOINT.point.z]
                print cv2.contourArea(cont)

    #img = cv2.bitwise_and(img, img, mask=mask)

    #cv2.imshow("squarecontours", img)

    if (foundsquare == False):
        print "sweet area is not found"

    return mask, foundsquare

def find_sweets(hsv, colour, r1, g1, b1, r2, g2, b2, area, size):
    lower = np.array([r1,g1,b1])
    upper = np.array([r2,g2,b2])

    #cv2.imshow("HSV", hsv)

    mask = cv2.inRange(hsv, lower, upper)

    # filter and fill the mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(size, size))
    mask2 = cv2.morphologyEx(mask,cv2.MORPH_OPEN,kernel)

    contour,hier = cv2.findContours(mask2,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

    sweetCount = 0
    sweetcontours = []
    sweetcentres = []

    global collisions
    collisions = "False"

    sweetangles = []

    for cnt in contour:
        if (cv2.contourArea(cnt) > area):
            if cv2.contourArea(cnt) < 1500:
                rows,cols = hsv.shape[:2]
                [vx,vy,x,y] = cv2.fitLine(cnt, cv2.cv.CV_DIST_L2,0,0.01,0.01)
                lefty = int((-x*vy/vx) + y)
                righty = int(((cols-x)*vy/vx)+y)
                sweetangles.append(math.atan2(righty - lefty, cols-1 - 0))
                # cv2.line(hsv,(cols-1,righty),(0,lefty),(0,255,0),2)
                # print "Angle is ",rect[2]

                cv2.drawContours(mask2, [cnt], 0, 255, 3)
                sweetcontours.append(cnt)
                sweetCount = sweetCount + 1
                M = cv2.moments(cnt)
                cx = int(M['m10']/M['m00'])
                cy = int(M['m01']/M['m00'])
                sweetcentres.append((cx, cy))

    print "There are "+str(sweetCount)+" "+colour+" sweets"


    #cv2.imshow("bluemask", mask2)

    # return mask2, sweetcontours, sweetCount, sweetcentres, collisioncontours, collisionCount, collisionCentres, sweetangles

    return mask2, sweetcontours, sweetCount, sweetcentres, sweetangles


# convert image pixel to Baxter point
def pixel_to_baxter(imagex, imagey):
    # FROM CAMERA_INFO ROSTOPIC
    # INTRINSIC CAMERA MATRIX (fx, 0, cx)
                            # (0, fy, cy)
                            # (0, 0, 1)
    # K: [407.366831078, 0.0, 642.166170111, 0.0, 407.366831078, 387.185928717, 0.0, 0.0, 1.0]

    fx = 407.366831078
    fy = 407.366831078
    cx = 642.166170111
    cy = 387.185928717

    # USING DISTANCE S FROM TABLE AND THE FACT THE 3D CAMERA COORD IS s*((u-cx)/fx, (v-cy)/fy, 1)

    u = imagex
    v = imagey
    xl = (u - cx)/fx
    yl = (v - cy)/fy

    s = 0.45
    x = xl * s
    y = yl * s

    return (x, y)

def publish_sweet_handle(req):
    print "request has string "+req.A
    global centrelist, colourAmounts, pointlist, pageCentre
    global anglelist
    centrelist = []
    # collisionCentre = []
    for i in range(0, len(pointlist)):
        centrelist.append(pointlist[i].point.x)
        centrelist.append(pointlist[i].point.y)
        centrelist.append(pointlist[i].point.z)
    print colourAmounts
    return RequestSweetInfoResponse(colourAmounts, centrelist, anglelist, pageCentre)

def handle_reset_sweets(req):
    print "Returning ",req.reset
    global enableAnalyse
    # rospy.sleep(4)
    rospy.sleep(2)
    enableAnalyse = True
    while enableAnalyse == True:
        rospy.sleep(1)
    return LookForSweetsResponse("OK")

global subscribeCounter
subscribeCounter = 0
#Subscribes to left hand camera image feed
def main():
    rospy.init_node('view_sweet_cam', anonymous = True)

    # cv2.namedWindow('IMAGE', flags=0)
    # cv2.namedWindow('HSV', flags=0)


    # buffer_size = rospy.get_param("/cameras/right_hand_camera/buffer_size")
    # rospy.Subscriber(image_topic, Image, callback,  queue_size = 1, buff_size=2**24)
    global subscribeCounter
    subscribeCounter = subscribeCounter + 1

    if (enableAnalyse == True):
        image_topic = rospy.resolve_name("/cameras/right_hand_camera/image")
        # rospy.Subscriber(image_topic, Image, callback, queue_size = 1, buff_size=int(1024000))
        rospy.Subscriber(image_topic, Image, callback)

    s = rospy.Service('publish_sweet_info', RequestSweetInfo, publish_sweet_handle)

    t = rospy.Service('reset_sweets', LookForSweets, handle_reset_sweets)


    #Keep from exiting until this node is stopped
    rospy.spin()

if __name__ == '__main__':
     main()
