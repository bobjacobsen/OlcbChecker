#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check Identify Events Global

Usage:
python3.10 check_ev20_idg.py

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

    # send an Identify Events Global  message to provoke response - previously checked to work
    message = Message(MTI.Identify_Events_Global , NodeID(olcbchecker.ownnodeid()), None)
    olcbchecker.sendMessage(message)

    producerIdMTIs = [MTI.Producer_Identified_Unknown, MTI.Producer_Identified_Active, MTI.Producer_Identified_Inactive, MTI.Producer_Range_Identified]
    consumerIdMTIs = [MTI.Consumer_Identified_Unknown, MTI.Consumer_Identified_Active, MTI.Consumer_Identified_Inactive, MTI.Consumer_Range_Identified]
    
    producerReplys = set(())
    producedEvents = set(())
    consumerReplys = set(())
    
    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # is this a reply? - If not, silently ignore it
            if received.mti not in producerIdMTIs and received.mti not in consumerIdMTIs and received.mti != MTI.Producer_Consumer_Event_Report :
                # logger.warning ("Unexpected {}, are extra nodes present?".format(received))
                continue
                
            if destination != received.source : # check source in message header
                # global request might get replies from other nodes; ignore those.
                continue

            if received.mti in producerIdMTIs :
                    producerReplys.add(received)
                    producedEvents.add(EventID(received.data))
                    
            if received.mti in consumerIdMTIs :
                    consumerReplys.add(received)

            # if PCER, check that event ID has been sent
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
        logger.warning ("Failure - Did not received any identify messages")
        return(3)
        
    # now check if addressed gets the same as global. First, get addressed.
    message = Message(MTI.Identify_Events_Addressed , NodeID(olcbchecker.ownnodeid()), destination)
    olcbchecker.sendMessage(message)
    
    producerSeen = set(())
    consumerSeen = set(())
    
    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # is this a reply?
            if received.mti not in producerIdMTIs and received.mti not in consumerIdMTIs :
                    # not message we're checking right now
                    continue
                
            if destination != received.source : # check source in message header
                logger.warning ("Failure - Unexpected source of reply message: {} {}".format(received, received.source))
                return(3)

            if received.mti in producerIdMTIs :
                if received in producerReplys :
                    producerSeen.add(received)
                    continue
                else :
                    logger.warning ("Failure - Identify Producer not in global result {} {}".format(received, EventID(received.data)))
                    
            if received.mti in consumerIdMTIs :
                if received in consumerReplys :
                    consumerSeen.add(received)
                    continue
                else :
                    logger.warning ("Failure - Identify Consumer not in global result {} {}".format(received, EventID(received.data)))
                    
        except Empty:
            # stopped getting messages, proceed
            break

    if len(producerReplys) != len(producerSeen) or len(consumerReplys) !=len(consumerSeen) :
        logger.warning ("Failure - missing identify messages")
        return(3)
    
    
    logger.info("Passed")
    return 0

if __name__ == "__main__":
    import olcbchecker
    result = check()
    olcbchecker.setup.interface.close()
    sys.exit(result)
