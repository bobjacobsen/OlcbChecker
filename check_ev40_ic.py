#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check Identify Consumers messages

Usage:
python3.10 check_ev40_ic.py 

The -h option will display a full list of options.
'''

import sys
import logging

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.pip import PIP
from openlcb.eventid import EventID

from queue import Empty

def check():
    # set up the infrastructure

    import olcbchecker.setup
    logger = logging.getLogger("EVENTS")

    # pull any early received messages
    olcbchecker.purgeMessages()

    # get configured DUT node ID - this uses Verify Global in some cases, but not all
    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    # check if PIP says this is present
    if olcbchecker.isCheckPip() : 
        pipSet = olcbchecker.gatherPIP(destination)
        if pipSet is None:
            logger.warning ("Failed in setup, no PIP information received")
            return (2)
        if not PIP.EVENT_EXCHANGE_PROTOCOL in pipSet :
            logger.info("Passed - due to Event Exchange not in PIP")
            return(0)

    # send an Identify Events Addressed  message to accumulate producers to check
    message = Message(MTI.Identify_Events_Addressed , NodeID(olcbchecker.ownnodeid()), destination)
    olcbchecker.sendMessage(message)

    # does not include range replies
    consumerIdMTIs = [MTI.Consumer_Identified_Unknown, MTI.Consumer_Identified_Active, MTI.Consumer_Identified_Inactive]
    
    consumedEvents = set(())
    
    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # is this a reply?
            if received.mti not in consumerIdMTIs :
                    continue # just skip
                
            if destination != received.source : # check source in message header
                logger.warning ("Failure - Unexpected source of reply message: {} {}".format(received, received.source))
                return(3)

            consumedEvents.add(EventID(received.data))
            
        except Empty:
            # stopped getting messages, proceed
            break

    # have the set to check, proceed to check each one
    fail = False
    for event in consumedEvents :
        message = Message(MTI.Identify_Consumer, NodeID(olcbchecker.ownnodeid()), None, event.toArray())
        olcbchecker.sendMessage(message)

        try:
            while True : # in case we need to skip PCER messages
                received = olcbchecker.getMessage() # timeout if no entries
                # was a range reply received?  If so, warn
                if received.mti == MTI.Consumer_Range_Identified :
                    logger.info("Warning - received Consumer Range Idenfified in response to request")
                    continue
                # is this a reply? Some nodes emit PCER after verify
                if received.mti not in consumerIdMTIs :
                    continue 
                # does the event ID match?
                if EventID(received.data) != event :
                    continue
                break

        except Empty:
            # no reply, error
            logger.warning ("Failure - No reply for event: {}".format(event))
            fail = True
        
    if fail : 
        logger.warning ("Failure - no reply for one or more event IDs")
        return(3)
        
    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
