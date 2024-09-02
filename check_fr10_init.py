#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check CAN alias reservation at startup

Usage:
python3.10 check_fr10_init.py

The -h option will display a full list of options.
'''

import sys
import logging

from openlcb.nodeid import NodeID

from queue import Empty

import olcbchecker.setup

def check():
    # set up the infrastructure

    logger = logging.getLogger("FRAME")

    timeout = 0.3

    olcbchecker.purgeFrames()
  
    ###############################
    # checking sequence starts here
    ###############################
    
    if olcbchecker.setup.configure.skip_interactive :
        logger.info("Interactive test skipped")
        return 0
        
    # prompt operator to restart node to start process
    print("Please reset/restart the checked node now")

    try :
        # check for four CID
        frame = olcbchecker.getFrame(30)  # wait for operator to start check
        if (frame.header & 0xFF_000_000) != 0x170_00_000 :
            logger.warning ("Failure - frame was not 1st CID frame")
            return 3
        cid1 = (frame.header & 0xFFF000) >> 12
        alias = frame.header & 0xFFF
        
        if alias == 0 :
            logger.warning("Failure - Zero alias not permitted")
            return 3
    
        frame = olcbchecker.getFrame()
        if (frame.header & 0xFF_000_000) != 0x16_000_000 :
            logger.warning ("Failure - frame was not 2nd CID frame")
            return 3
        if alias != frame.header & 0xFFF :
            logger.warning ("failure - alias did not match in 2nd CID frame")
            return 3
        cid2 = (frame.header & 0xFFF000) >> 12
    
        frame = olcbchecker.getFrame()
        if (frame.header & 0xFF_000_000) != 0x15_000_000 :
            logger.warning ("Failure - frame was not 3rd CID frame")
            return 3
        if alias != frame.header & 0xFFF :
            logger.warning ("failure - alias did not match in 3rd CID frame")
            return 3
        cid3 = (frame.header & 0xFFF000) >> 12
    
        frame = olcbchecker.getFrame()
        if (frame.header & 0xFF_000_000) != 0x14_000_000 :
            logger.warning ("Failure - frame was not 4th CID frame")
            return 3
        if alias != frame.header & 0xFFF :
            logger.warning ("failure - alias did not match in 4th CID frame")
            return 3
        cid4 = (frame.header & 0xFFF000) >> 12
    
        # check for RID frame
        frame = olcbchecker.getFrame(0.7)  # might be delayed
        if (frame.header & 0xFF_FFF_000) != 0x10_700_000 :
            logger.warning ("Failure - frame was not RID frame")
            return 3
        if alias != frame.header & 0xFFF :
            logger.warning ("failure to match alias in RID frame")
            return 3
    
        # check for AMD frame
        frame = olcbchecker.getFrame(0.7) # might be delayed
        if (frame.header & 0xFF_FFF_000) != 0x10_701_000 :
            logger.warning ("Failure - frame was not AMD frame")
            return 3
        if alias != frame.header & 0xFFF :
            logger.warning ("Failure - did not match alias in RID frame")
            return 3
    
        nodeId = (cid1 << 36) | (cid2 << 24) | (cid3 << 12) | cid4
        if nodeId == 0:
            logger.warning ("Failure - Zero Node ID not permitted")
            return 3
            
        if NodeID(nodeId) != NodeID(frame.data) :
            logger.warning("Failure - Node ID mismatch:{} {}".format(NodeID(nodeId), NodeID(frame.data)))
            return 3
        
    except Empty:
        logger.warning ("Failure - did not receive expected frame")
        return 3

    logger.info("Passed")
    return 0
 
if __name__ == "__main__":
    result = check()
    olcbchecker.setup.interface.close()
    sys.exit(result)
