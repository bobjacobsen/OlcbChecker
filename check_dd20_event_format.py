#!/usr/bin/env python3.10
'''
Check that all DCC detector Event IDs have valid encoding:
direction bits in [0..3], address prefix not in reserved range (0x3A-0x3F),
short/consist addresses in range 0-127.

Usage:
python3.10 check_dd20_event_format.py

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
    import olcbchecker.setup
    from olcbchecker.dcc_detector_utils import (is_detector_event,
                                                 is_valid_event_id,
                                                 describe_event)

    logger = logging.getLogger("DCC_DETECTOR")

    olcbchecker.purgeMessages()

    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    if olcbchecker.isCheckPip() :
        pipSet = olcbchecker.gatherPIP(destination)
        if pipSet is None:
            logger.warning("Failed in setup, no PIP information received")
            return (2)
        if not PIP.EVENT_EXCHANGE_PROTOCOL in pipSet :
            logger.info("Passed - due to Event Exchange not in PIP")
            return(0)

    # send Identify Events Addressed
    message = Message(MTI.Identify_Events_Addressed,
                      NodeID(olcbchecker.ownnodeid()), destination)
    olcbchecker.sendMessage(message)

    producerIdMTIs = [MTI.Producer_Identified_Unknown,
                      MTI.Producer_Identified_Active,
                      MTI.Producer_Identified_Inactive]

    node_id_int = destination.nodeId
    detector_events = []

    while True :
        try :
            received = olcbchecker.getMessage()
            if received.mti not in producerIdMTIs :
                continue
            if destination != received.source :
                continue

            event = EventID(received.data)
            if is_detector_event(event.eventId, node_id_int) :
                detector_events.append(event)

        except Empty:
            break

    if len(detector_events) == 0 :
        logger.warning("Failure - No detector events found to validate")
        return(3)

    # validate each detector event
    fail = False
    for event in detector_events :
        ok, reason = is_valid_event_id(event.eventId)
        if not ok :
            logger.warning("Failure - Invalid event {}: {}".format(event, reason))
            fail = True
        else :
            if olcbchecker.trace() >= 20 :
                logger.debug("  Valid: {}".format(describe_event(event.eventId)))

    if fail :
        return(3)

    logger.info("All {} detector event(s) have valid encoding".format(
        len(detector_events)))
    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
