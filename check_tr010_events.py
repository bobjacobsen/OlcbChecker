#!/usr/bin/env python3.10
'''
This uses checks a Train node for the isTrain event

Usage:
python3.10 check_tr010_events.py

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
    logger = logging.getLogger("TRAIN_CONTROL")

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
        if not PIP.TRAIN_CONTROL_PROTOCOL in pipSet :
            logger.info("Passed - due to Train Control not in PIP")
            return(0)

    # pull any early received messages
    olcbchecker.purgeMessages()

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
                    logger.warning ("Failure - Unexpected message {}".format(received))
                
            if destination != received.source : # check source in message header
                continue  # just ignore this

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
    
    # check for isTrain received
    for msg in producerReplys :
        if (msg.data == [0x01,0x01,0x00,0x00,0x00,0x00,0x03,0x03]) : # isTrain event
            logger.info("Passed")
            return 0

    logger.warning ("Failure - Did not receive isTrain event")
    return(3)

if __name__ == "__main__":
    sys.exit(check())
