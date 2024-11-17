#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check response to standard (not extended) frames

Usage:
python3.10 check_fr60_standard.py

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

    timeout = 0.01
    
    olcbchecker.purgeFrames()

    localAlias = olcbchecker.setup.canLink.localAlias # just to be shorter

    ###############################
    # checking sequence starts here
    ###############################

    # pull any early received messages
    olcbchecker.purgeMessages()

    for i in range(0, 2047) :
    
        # send a standard frame in format :S1234N;
        frame = ":S{:04X}N;".format(i)
        olcbchecker.setup.sendToSocket(frame)
        
        # see if there's been a response - this could be done at the end to save time?
        try :
            frame = olcbchecker.getFrame(timeout)
            logger.warning ("Frame received in response")
            return 3
                    
        except Empty:
            pass    # this is normal

    logger.info("Passed")
    return 0
 
if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
