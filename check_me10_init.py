#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check for initialization

Usage:
python3.10 check_me10_init.py

The -h option will display a full list of options.
'''

import sys
import logging

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.eventid import EventID

from queue import Empty

def check():
    # set up the infrastructure

    import olcbchecker.setup
    logger = logging.getLogger("MESSAGE")

    # pull any early received messages
    olcbchecker.purgeMessages()

    # get configured DUT node ID - this uses Verify Global in some cases, but not all
    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    if olcbchecker.setup.configure.skip_interactive :
        logger.info("Interactive test skipped")
        return 0  

    # prompt operator to restart node
    print("Please reset/restart the device being checked now")

    while True :
        try :
            received = olcbchecker.getMessage(15) # long reset timeout to wait for manual restart
            # is this a reply from that node?
            if received.mti == MTI.Initialization_Complete or received.mti == MTI.Initialization_Complete_Simple :
                # this is an init message, check source
                if destination != received.source : 
                    logger.warning("Failure - source address not correct")
                    return(3)
                # check that it's carrying enough data to be a node ID
                if len(received.data) != 6 :
                    logger.warning("Failure - not correct data length, not carrying a Node ID")
                    return 3
                # check that the data is the source node ID
                nodeID = NodeID(received.data)
                if nodeID != received.source :
                    logger.warning("Failure - Node ID in data does not match source ID")
                    return 3                
                # success
                break                
       
            logger.warning("Failure - received unexpected message type: {}".format(received))
        
        except Empty:
            logger.warning ("Failure - Did not receive Initialization Complete message")
            return(3)

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    sys.exit(check())
