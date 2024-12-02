#!/usr/bin/env python3.10
'''
Check ability to keep up with full-speed operation

Usage:
python3.10 check_fr50_capacity.py

The -h option will display a full list of options.
'''

import sys
import logging

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from queue import Empty

import olcbchecker.setup

def sendCheckMessages(beforeMessage, checkMessage, afterMesage):
    BEFORE_COUNT = 300;
    AFTER_COUNT  = BEFORE_COUNT;
    
    for i in range(0, BEFORE_COUNT) :
        olcbchecker.sendMessage(beforeMessage)

    olcbchecker.sendMessage(checkMessage)
   
    for i in range(0, AFTER_COUNT) :
        olcbchecker.sendMessage(afterMesage)
    return
   

def check():
    # set up the infrastructure

    logger = logging.getLogger("FRAME")

    # pull any early received messages
    olcbchecker.purgeMessages()

    ownnodeid = olcbchecker.setup.configure.ownnodeid
    destination = olcbchecker.getTargetID()

    timeout = 3.0

    localAlias = olcbchecker.setup.canLink.localAlias # just to be shorter

    ###############################
    # checking sequence starts here
    ###############################

    # send 1st check
    beforeMessage = Message(MTI.Producer_Consumer_Event_Report , NodeID(olcbchecker.ownnodeid()), destination, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01])
    checkMessage  = Message(MTI.Verify_NodeID_Number_Addressed  , NodeID(olcbchecker.ownnodeid()), destination)
    afterMesage   = Message(MTI.Producer_Consumer_Event_Report , NodeID(olcbchecker.ownnodeid()), destination, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01])
    sendCheckMessages(beforeMessage, checkMessage, afterMesage)
    
    # check for reply
    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # is this a reply from that node?
            if not received.mti == MTI.Verified_NodeID and not received.mti == MTI.Verified_NodeID_Simple : continue # wait for next
            # this is a Verified Node ID message, success

            if destination != received.source : # check source in message header
                logger.warning ("Failure - Unexpected source of reply message in check 1: {} {}".format(received, received.source))
                return(3)
        
            if len(received.data) < 6:
                logger.warning ("Failure - Unexpected length of reply message in check 1: {} {}".format(received, received.data))
                return(3)

            break
        except Empty:
            logger.warning ("Failure - Did not receive Verified Node ID reply for check 1")
            return(3)

    olcbchecker.purgeMessages()

    # send 2nd check
    
    beforeMessage = Message(MTI.Verify_NodeID_Number_Addressed , NodeID(olcbchecker.ownnodeid()), NodeID(olcbchecker.ownnodeid()), [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01])
    checkMessage  = Message(MTI.Verify_NodeID_Number_Global  , NodeID(olcbchecker.ownnodeid()), None)
    afterMesage   = Message(MTI.Verify_NodeID_Number_Addressed , NodeID(olcbchecker.ownnodeid()), NodeID(olcbchecker.ownnodeid()), [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01])
    sendCheckMessages(beforeMessage, checkMessage, afterMesage)
    
    # check for reply
    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # is this a reply from that node?
            if not received.mti == MTI.Verified_NodeID and not received.mti == MTI.Verified_NodeID_Simple : continue # wait for next
            # this is a Verified Node ID message, from right node?

            if destination != received.source : # check source in message header
                continue # there might be other nodes replying to the global request
        
            if len(received.data) < 6:
                logger.warning ("Failure - Unexpected length of reply message in check 2: {} {}".format(received, received.data))
                return(3)

            break
        except Empty:
            logger.warning ("Failure - Did not receive Verified Node ID reply for check 2")
            return(3)

    olcbchecker.purgeMessages()

    # send 3rd check
    beforeMessage = Message(MTI.Identify_Consumer , NodeID(olcbchecker.ownnodeid()), destination, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01])
    checkMessage  = Message(MTI.Verify_NodeID_Number_Global  , NodeID(olcbchecker.ownnodeid()), None)
    afterMesage   = Message(MTI.Identify_Consumer , NodeID(olcbchecker.ownnodeid()), destination, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01])
    sendCheckMessages(beforeMessage, checkMessage, afterMesage)
    
    # check for reply
    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # is this a reply from that node?
            if not received.mti == MTI.Verified_NodeID and not received.mti == MTI.Verified_NodeID_Simple : continue # wait for next
            # this is a Verified Node ID message, from right node?

            if destination != received.source : # check source in message header
                continue # there might be other nodes replying to the global request
        
            if len(received.data) < 6:
                logger.warning ("Failure - Unexpected length of reply message in check 3: {} {}".format(received, received.data))
                return(3)

            break
        except Empty:
            logger.warning ("Failure - Did not receive Verified Node ID reply for check 3")
            return(3)




    logger.info("Passed")
    return 0
 
if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
