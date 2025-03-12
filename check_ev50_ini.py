#!/usr/bin/env python3.10
'''
This checks event identification after startup

Usage:
python3.10 check_ev50_ini.py

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
    from olcbchecker.utils import checkAgainstIdList

    logger = logging.getLogger("EVENTS")

    # pull any early received messages
    olcbchecker.purgeMessages()

    # get configured DUT node ID - this uses Verify Global in some cases, but not all
    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    # If not running interactive checks, this is considered to pass
    
    if olcbchecker.setup.configure.skip_interactive :
        logger.info("Interactive check skipped")
        return 0
        
    # prompt operator to restart node to start process
    print("Please reset/restart the checked node now")

    # wait for Initialization Complete
    
    timeout = 30
    while True :
        try :
            received = olcbchecker.getMessage(30) # timeout if no entries

            if destination != received.source : # check source in message header
                # wait might get messages from other nodes, ignore them
                timeout = timeout/2   # don't wait as long this time so we're not stuck in a loop
                continue

            if received.mti == MTI.Initialization_Complete : break  # move on to checks
            if received.mti == MTI.Initialization_Complete_Simple : break  # move on to checks
        
        except Empty:
            # stopped getting messages, this is a fail
            logger.warning("Failure - Did not see node initialize")
            return (3)

    # then do the checks
    producerIdMTIs = [MTI.Producer_Identified_Unknown, MTI.Producer_Identified_Active, MTI.Producer_Identified_Inactive, MTI.Producer_Range_Identified]
    consumerIdMTIs = [MTI.Consumer_Identified_Unknown, MTI.Consumer_Identified_Active, MTI.Consumer_Identified_Inactive, MTI.Consumer_Range_Identified]
    
    # sets of received Event IDs
    producerReplys = set(())
    producedRanges = set(())
    consumerReplys = set(())
    consumerRanges = set(())
    
    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # is this a reply? - If not, silently ignore it
            if received.mti not in producerIdMTIs and received.mti not in consumerIdMTIs and received.mti != MTI.Producer_Consumer_Event_Report :
                #logger.warning ("Unexpected {}, are extra nodes present?".format(received))
                continue
                
            if destination != received.source : # check source in message header
                # global request might get replies from other nodes; ignore those.
                continue
                
            if received.mti in producerIdMTIs :
                if received.mti ==  MTI.Producer_Range_Identified :
                    producedRanges.add(EventID(received.data))
                else :
                    producerReplys.add(EventID(received.data))
                    
            if received.mti in consumerIdMTIs :
                if received.mti ==  MTI.Consumer_Range_Identified :
                    consumerRanges.add(EventID(received.data))
                else :
                    consumerReplys.add(EventID(received.data))

            # if PCER, check that event ID has been produced
            if received.mti is MTI.Producer_Consumer_Event_Report :
                eventID = EventID(received.data)
                if not checkAgainstIdList(producerReplys, producedRanges, eventID) :
                    logger.warning ("Failure - PCER without Producer Identified: {}".format(eventID))
                    return(3)
        except Empty:
            # stopped getting messages, proceed
            break

    if len(producerReplys) == 0 and len(producedRanges) == 0 and len(consumerReplys) == 0 and len(consumerRanges) == 0 :
        logger.warning ("Failure - Did not received any identify messages")
        return(3)
        
    # remove individual IDs that are within a range as redundant
    trimmedset = set(())
    for p in producerReplys :
        if not checkAgainstIdList([], producedRanges, p) :
            trimmedset.add(p)
    producerReplys = trimmedset
    trimmedset = set(())
    for p in consumerReplys :
        if not checkAgainstIdList([], consumerRanges, p) :
            trimmedset.add(p)
    consumerReplys = trimmedset
        
    # now check if addressed gets the same as global. First, get addressed.
    message = Message(MTI.Identify_Events_Addressed , NodeID(olcbchecker.ownnodeid()), destination)
    olcbchecker.sendMessage(message)
    
    producerSeen = set(())
    proRangeSeen = set(())
    consumerSeen = set(())
    conRangeSeen = set(())
    
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
                if received.mti == MTI.Producer_Range_Identified :
                    proRangeSeen.add(EventID(received.data))
                else :
                    producerSeen.add(EventID(received.data))
                    if checkAgainstIdList(producerReplys, producedRanges, EventID(received.data)) : 
                        continue
                    else :
                        logger.warning ("Failure - Identify Producer not in global result {} {}".format(received, EventID(received.data)))
                    
            if received.mti in consumerIdMTIs :
                if received.mti == MTI.Consumer_Range_Identified :
                    conRangeSeen.add(EventID(received.data))
                else :
                    consumerSeen.add(EventID(received.data))
                    if checkAgainstIdList(consumerReplys, consumerRanges, EventID(received.data)) : 
                        continue
                    else :
                        logger.warning ("Failure - Identify Consumer not in global result {} {}".format(received, EventID(received.data)))
                    
        except Empty:
            # stopped getting messages, proceed
            break

    # remove individual IDs that are within a range as redundant
    trimmedset = set(())
    for p in producerSeen :
        if not checkAgainstIdList([], producedRanges, p) :
            trimmedset.add(p)
    producerSeen = trimmedset
    trimmedset = set(())
    for p in consumerSeen :
        if not checkAgainstIdList([], consumerRanges, p) :
            trimmedset.add(p)
    consumerSeen = trimmedset

    # cross check the individual results
    if producerReplys != producerSeen or consumerReplys != consumerSeen :
        logger.warning ("Failure - missing identify messages")
        return(3)
    if producedRanges != proRangeSeen or consumerRanges != conRangeSeen :
        logger.warning ("Failure - missing identify range messages")
        return(3)
    
    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
