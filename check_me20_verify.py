#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check Verify message exchange

Usage:
python3.10 check_me20_verify.py

The -h option will display a full list of options.
'''

import sys
import logging

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.pip import PIP

from queue import Empty

def check():
    # set up the infrastructure

    import olcbchecker.setup
    logger = logging.getLogger("MESSAGE")

    # pull any early received messages
    olcbchecker.purgeMessages()

    # get configured DUT node ID - this uses Verify Global in some cases, but not all
    destination = olcbchecker.getTargetID()

    # Will we be checking PIP?
    pipSet = olcbchecker.gatherPIP(destination, always=True)
    if pipSet is None:
        logger.warning("Failure - PIP reply is required for this check")
        return (1)

    ###############################
    # checking sequence starts here
    ###############################

    # send a Verify Nodes Global message
    message = Message(MTI.Verify_NodeID_Number_Global, NodeID(olcbchecker.ownnodeid()), None)
    olcbchecker.sendMessage(message)

    # pull the received frames and get the source ID from first as remote NodeID
    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries

            if received.mti != MTI.Verified_NodeID :
                continue # ignore other messages

            if destination != received.source : # check source in message header
                continue # allow other nodes to reply to this global request
        
            if len(received.data) != 6 :
                logger.warning ("Failure - Unexpected length of reply message: {}".format(received))
                return(3)
            
            if destination != NodeID(received.data) :
                logger.warning ("Failure - Unexpected contents of reply message: {}".format(received))
                return(3)
            
            # check against PIP
            simple = PIP.SIMPLE_PROTOCOL in pipSet
            if simple and received.mti == MTI.Verified_NodeID :
                logger.warning ("Failure - PIP says Simple Node but didn't receive correct MTI")
                return(3) 
            elif (not simple) and received.mti == MTI.Verified_NodeID_Simple :
                logger.warning ("Failure - PIP says not Simple Node but didn't receive correct MTI")
                return(3) 

            break
        except Empty:
            logger.warning ("Failure - did not get response to global")
            return(3)

    olcbchecker.purgeMessages()

    # send an addressed verify to this node and check for answer
    message = Message(MTI.Verify_NodeID_Number_Addressed, NodeID(olcbchecker.ownnodeid()), destination)
    olcbchecker.sendMessage(message)

    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # is this a valid reply?
            if received.mti != MTI.Verified_NodeID and received.mti != MTI.Verified_NodeID_Simple: continue # wait for next
        
            if destination != received.source : # check source in message header
                logger.warning ("Failure - Unexpected source of reply message: {} {}".format(received, received.source))
                return(3)
        
            if len(received.data) != 6 :
                logger.warning ("Failure - Unexpected length of reply message: {}".format(received))
                return(3)
            
            if destination != NodeID(received.data) :
                logger.warning ("Failure - Unexpected contents of reply message: {}".format(received))
                return(3)
            
            # check against PIP
            if pipSet is not None :
                simple = PIP.SIMPLE_PROTOCOL in pipSet
                if simple and received.mti == MTI.Verified_NodeID :
                    logger.warning ("Failure - PIP says Simple Node but didn't receive correct MTI")
                    return(3) 
                elif (not simple) and received.mti == MTI.Verified_NodeID_Simple :
                    logger.warning ("Failure - PIP says not Simple Node but didn't receive correct MTI")
                    return(3) 
            break
        except Empty:
            logger.warning ("Failure - no reply to Verify Node Addressed request")
            return(3) 

    # pull any early received messages
    olcbchecker.purgeMessages()

    # send an addressed verify to a different node (the origin node) and check for lack of answer
    message = Message(MTI.Verify_NodeID_Number_Addressed, NodeID(olcbchecker.ownnodeid()), NodeID(olcbchecker.ownnodeid()))
    olcbchecker.sendMessage(message)

    try :
        received = olcbchecker.getMessage() # timeout if no entries
        # is this a pip reply?
        if received.mti == MTI.Verified_NodeID: # wait for next
            logger.warning ("Failure - Should not have gotten a reply {}".format(received))
            return(3) 
        logger.warning ("Failure - Unexpected message {}".format(received))
        return(3)  
    except Empty:
        # this is success
        pass

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
