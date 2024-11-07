#!/usr/bin/env python3.10
'''
This checks the section-2 reserved search bytes in the Train Search protocol

Usage:
python3.10 check_ts30_reserved2.py

The -h option will display a full list of options.
'''

import sys
import logging
import olcbchecker

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.pip import PIP
from openlcb.eventid import EventID

from queue import Empty

def check():
    # set up the infrastructure

    import olcbchecker.setup
    logger = logging.getLogger("TRAIN_SEARCH")

    # pull any early received messages
    olcbchecker.purgeMessages()

    # get configured DUT node ID - this uses Verify Global in some cases, but not all
    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    # pull any early received messages
    olcbchecker.purgeMessages()

    # Ensure that train node 12 exists
    # Send a search Identify Producer with search nibbles 0x12.FF.FF and 
    # Allocate, Exact, Address Only, Any/Default protocol 0xE0.
    message = Message(MTI.Identify_Producer , NodeID(olcbchecker.ownnodeid()), destination,
                [0x09,0x00,0x99,0xFF,   0xFF, 0xFF, 0x12, 0xE0])
    olcbchecker.sendMessage(message)

    try :
        received = olcbchecker.getMessage(1.0) # timeout if no entries
        # we expect a reply Producer Identified Valid
        while True :
            # if PIV, check that event ID has been produced
            if received.mti is MTI.Producer_Identified_Active :
                eventID = EventID(received.data)
                if eventID != EventID([0x09,0x00,0x99,0xFF,   0xFF, 0xFF, 0x12, 0xE0]) :
                    logger.warning ("Failure - PCER without Producer Identified: {}".format(eventID))
                    return(3)
                else :
                    break # all OK
            # go around again
            received = olcbchecker.getMessage(1.0) # timeout if no entries
        # here, we have found reply, continue to next part  
                 
    except Empty:
        logger.warning ("Failure - Did not receive answer when creating node")
        return(3)

    olcbchecker.purgeMessages()
      
    # Send a search Identify Producer with search nibbles 0xFF.FF.FC and 
    # Allocate, Exact, Address Only, Any/Default protocol 0xE0.
    message = Message(MTI.Identify_Producer , NodeID(olcbchecker.ownnodeid()), destination,
                [0x09,0x00,0x99,0xFF,   0xFF, 0xFF, 0xFC, 0xE0])
    olcbchecker.sendMessage(message)

    try:
        received = olcbchecker.getMessage(1.0) # timeout if no entries
        # we expect no reply Producer Identified Valid
        while True :
            # if PIV, check that event ID has been produced
            if received.mti is MTI.Producer_Identified_Active :
                eventID = EventID(received.data)
                if eventID == EventID([0x09,0x00,0x99,0xFF,   0xFF, 0xFF, 0xFC, 0xE0]) :
                    logger.warning ("Failure - 0x0B request resulted in train node match")
                    return(3)
            # go around again
            received = olcbchecker.getMessage(1.0) # timeout if no entries
                 
    except Empty:
        # no message, this is OK
        pass
        
    # success!
    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    olcbchecker.setup.interface.close()
    sys.exit(result)
