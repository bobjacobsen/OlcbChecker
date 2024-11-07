#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check Identify Events Addressed

Usage:
python3.10 check_ev10_ida.py

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

    # send an Identify Events Addressed  message to provoke response
    message = Message(MTI.Identify_Events_Addressed , NodeID(olcbchecker.ownnodeid()), destination)
    olcbchecker.sendMessage(message)

    producerIdMTIs = [MTI.Producer_Identified_Unknown, MTI.Producer_Identified_Active, MTI.Producer_Identified_Inactive, MTI.Producer_Range_Identified]
    consumerIdMTIs = [MTI.Consumer_Identified_Unknown, MTI.Consumer_Identified_Active, MTI.Consumer_Identified_Inactive, MTI.Consumer_Range_Identified]
    
    producerReplys = set(())
    producedEvents = set(())
    consumerReplys = set(())
    
    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # is this a reply?
            if received.mti not in producerIdMTIs and received.mti not in consumerIdMTIs and received.mti != MTI.Producer_Consumer_Event_Report :
                logger.warning ("Unexpected message {}, are extra nodes present?".format(received))
                
            if destination != received.source : # check source in message header
                logger.warning ("Failure - Unexpected source of reply message: {} {}".format(received, received.source))
                return(3)

            if received.mti in producerIdMTIs :
                    producerReplys.add(received)
                    producedEvents.add(EventID(received.data))
                    
            if received.mti in consumerIdMTIs :
                    consumerReplys.add(received)

            # if PCER, check that event ID has been produced
            if received.mti is MTI.Producer_Consumer_Event_Report :
                eventID = EventID(received.data)
                # TODO:  the following does not properly check against a Producer Range Identified
                if eventID not in producedEvents :
                    logger.warning ("Failure - PCER without Producer Identified: {}".format(eventID))
                    return(3)
        except Empty:
            # stopped getting messages, proceed
            break

    if len(producerReplys) == 0 and len(consumerReplys) == 0 :
        logger.warning ("Warning - Did not receive any Identify messages.")
        logger.warning ("          Check node documentation to see if it")
        logger.warning("           should be producing or consuming events.")
        return(1)
        
    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    olcbchecker.setup.interface.close()
    sys.exit(result)
