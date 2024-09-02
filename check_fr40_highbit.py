#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check response to an AME frame with a zaero high bit

Usage:
python3.10 check_fr40_highbit.py

The -h option will display a full list of options.
'''

import sys
import logging

from openlcb.nodeid import NodeID
from openlcb.canbus.canframe import CanFrame
from openlcb.canbus.controlframe import ControlFrame
from queue import Empty

import olcbchecker.setup

def check():
    # set up the infrastructure

    logger = logging.getLogger("FRAME")

    ownnodeid = olcbchecker.setup.configure.ownnodeid
    targetnodeid = olcbchecker.setup.configure.targetnodeid

    timeout = 0.3
    
    olcbchecker.purgeFrames()

    localAlias = olcbchecker.setup.canLink.localAlias # just to be shorter

    ###############################
    # checking sequence starts here
    ###############################

    # send the AME frame to start the exchange
    frame = CanFrame(ControlFrame.AME.value, localAlias)
    # remove the high bit from the header
    frame.header = frame.header & 0xF_FFF_FFF
    # and send the modified frame
    olcbchecker.setup.sendCanFrame(frame)
    
    try :
       # loop for an AMD from DBC or at least not from us
        while True :
            # check for AMD frame
            frame = olcbchecker.getFrame(1.0)
            if (frame.header & 0xFF_FFF_000) != 0x10_701_000 :
                logger.warning ("Failure - frame was not AMD frame in first part")
                return 3
        
            # check it carries a node ID
            if len(frame.data) < 6 :
                logger.warning ("Failure - AMD frame did not carry node ID")
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
        logger.warning ("Failure - did not receive expected frame")
        return 3

    logger.info("Passed")
    return 0
 
if __name__ == "__main__":
    result = check()
    olcbchecker.setup.interface.close()
    sys.exit(result)
    
