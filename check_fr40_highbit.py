#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check response to an AME frame with a zaero high bit

Usage:
python3.10 check_fr20_ame.py

The -h option will display a full list of options.
'''

import sys

from openlcb.nodeid import NodeID
from openlcb.canbus.canframe import CanFrame
from openlcb.canbus.controlframe import ControlFrame
from queue import Empty

import olcbchecker.setup

def getFrame(timeout=0.3) :
    return olcbchecker.setup.frameQueue.get(True, timeout)

def purgeFrames(timeout=0.3):
    while True :
        try :
            received = getFrame(timeout) # timeout if no entries
        except Empty:
             break

def check():
    # set up the infrastructure

    trace = olcbchecker.setup.trace # just to be shorter
    ownnodeid = olcbchecker.setup.configure.ownnodeid
    targetnodeid = olcbchecker.setup.configure.targetnodeid

    timeout = 0.3
    
    purgeFrames()

    ###############################
    # checking sequence starts here
    ###############################

    # send the AME frame to start the exchange
    frame = CanFrame(ControlFrame.AME.value, 0x001)  # bogus alias
    # remove the high bit from the header
    frame.header = frame.header & 0xF_FFF_FFF
    # and send the modified frame
    olcbchecker.setup.sendCanFrame(frame)
    
    try :
       # loop for an AMD from DBC or at least not from us
        while True :
            # check for AMD frame
            frame = getFrame(1.0)
            if (frame.header & 0xFF_FFF_000) != 0x10_701_000 :
                print ("Failure - frame was not AMD frame in first part")
                return 3
        
            # check it carries a node ID
            if len(frame.data) < 6 :
                print ("Failure - AMD frame did not carry node ID")
                return 3

            if targetnodeid is None :
                # we'll take the first one not from us
                if NodeID(frame.data) != NodeID(ownnodeid) :
                    break
            else :  # here we have a node ID to match
                if NodeID(frame.data) == NodeID(targetnodeid) :
                    break
        
            # loop to try again                
        
    except Empty:
        print ("Failure - did not receive expected frame")
        return 3

    if trace >= 10 : print("Passed")
    return 0
 
if __name__ == "__main__":
    sys.exit(check())
    
