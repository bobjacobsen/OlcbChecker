#!/usr/bin/env python3.10
'''
This checks compatibility with the PCER with Payload messages

Usage:
python3.10 check_ev60_ewp.py

The -h option will display a full list of options.
'''

import sys
import logging

from openlcb.nodeid import NodeID
from openlcb.canbus.canframe import CanFrame
from openlcb.canbus.controlframe import ControlFrame
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.pip import PIP
from openlcb.eventid import EventID

from queue import Empty

def check():
    # set up the infrastructure

    import olcbchecker.setup
    from olcbchecker.utils import checkAgainstIdList

    logger = logging.getLogger("EVENTS")

    # pull any early received frames
    olcbchecker.purgeFrames()

    # get configured DUT node ID - this uses Verify Global in some cases, but not all
    destination = olcbchecker.getTargetID()

    localAlias = olcbchecker.setup.canLink.localAlias # just to be shorter
    
    ###############################
    # checking sequence starts here
    ###############################

    beginMTI = 0x19F16000| localAlias
    midMTI   = 0x19F15000| localAlias
    endMTI   = 0x19F14000| localAlias
    
    thisEID  = NodeID(olcbchecker.ownnodeid()).toArray()
    thisEID.extend([0,0])
    
    frame1 = CanFrame(beginMTI, thisEID)  # header, data
    frame2 = CanFrame(endMTI, [1,2,3,4])
    olcbchecker.setup.sendCanFrame(frame1)
    olcbchecker.setup.sendCanFrame(frame2)

    frame1 = CanFrame(beginMTI, thisEID)  # header, data
    frame2 = CanFrame(endMTI, [1,2,3,4, 5, 6, 7, 8])
    olcbchecker.setup.sendCanFrame(frame1)
    olcbchecker.setup.sendCanFrame(frame2)

    frame1 = CanFrame(beginMTI, thisEID)  # header, data
    frame2 = CanFrame(midMTI, [1,2,3,4, 5, 6, 7, 8])
    frame3 = CanFrame(endMTI, [9,10,11,12])
    olcbchecker.setup.sendCanFrame(frame1)
    olcbchecker.setup.sendCanFrame(frame2)
    olcbchecker.setup.sendCanFrame(frame3)

    frame1 = CanFrame(beginMTI, thisEID)  # header, data
    frame2 = CanFrame(midMTI, [1,2,3,4, 5, 6, 7, 8])
    frame3 = CanFrame(endMTI, [9,10,11,12,13,14,15])
    olcbchecker.setup.sendCanFrame(frame1)
    olcbchecker.setup.sendCanFrame(frame2)
    olcbchecker.setup.sendCanFrame(frame3)

    olcbchecker.setup.sendCanFrame(frame1)
    for i in range(255) :
        olcbchecker.setup.sendCanFrame(frame2)
    olcbchecker.setup.sendCanFrame(frame3)  
    
    # wait for a possible Initialization Complete
    timeout = 30
    while True :
        try :
            received = olcbchecker.getMessage(30) # timeout if no entries

            if destination != received.source : # check source in message header
                # wait might get messages from other nodes, ignore them
                timeout = timeout/2   # don't wait as long this time so we're not stuck in a loop
                continue

            if received.mti == MTI.Initialization_Complete or received.mti == MTI.Initialization_Complete_Simple : 
                # node rebooted, this is a fail
                logger.warning("Failure - node rebooted")
                return (3)
                
        except Empty:
            # stopped getting messages without Initialization Complete, this is a pass
            # ask operator to confirm?
            if not olcbchecker.setup.configure.skip_interactive :
                logger.info("Did the DBC indicate any problems? y or n")
                selection = input(">> ").lower()
                if selection.startswith('y') :
                    logger.warning("Failure - operator indicated issue")
                    return (3)
        
            logger.info("Passed")
            return 0


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
