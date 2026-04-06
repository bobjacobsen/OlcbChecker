#!/usr/bin/env python3.10
'''
Check that a DCC detector responds to Identify Producer for each of its
detector Event IDs, as required by the DCC Detection Working Note section 2.6:
"A detector, acting as a producer, must reply to Verify Events and Identify
Producers messages with the appropriate event(s) or range."

Usage:
python3.10 check_dd30_identify_producer.py

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
    from olcbchecker.dcc_detector_utils import is_detector_event

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

    # first, gather all detector events via Identify Events Addressed
    message = Message(MTI.Identify_Events_Addressed,
                      NodeID(olcbchecker.ownnodeid()), destination)
    olcbchecker.sendMessage(message)

    # does not include range replies -- we check individual events
    producerIdMTIs = [MTI.Producer_Identified_Unknown,
                      MTI.Producer_Identified_Active,
                      MTI.Producer_Identified_Inactive]

    node_id_int = destination.nodeId
    detector_events = set()

    while True :
        try :
            received = olcbchecker.getMessage()
            if received.mti not in producerIdMTIs :
                continue
            if destination != received.source :
                continue

            event = EventID(received.data)
            if is_detector_event(event.eventId, node_id_int) :
                detector_events.add(event)

        except Empty:
            break

    if len(detector_events) == 0 :
        logger.warning("Failure - No detector events found to check")
        return(3)

    # now send Identify Producer for each detector event and check for reply
    fail = False
    for event in detector_events :
        message = Message(MTI.Identify_Producer,
                          NodeID(olcbchecker.ownnodeid()), None,
                          event.toArray())
        olcbchecker.sendMessage(message)

        try:
            while True :
                received = olcbchecker.getMessage()
                # a range reply is acceptable per spec ("appropriate event(s) or range")
                if received.mti == MTI.Producer_Range_Identified :
                    break
                # skip non-producer-identified replies (e.g. PCER)
                if received.mti not in producerIdMTIs :
                    continue
                # check if this is a matching reply
                if EventID(received.data) != event :
                    continue
                break

        except Empty:
            logger.warning("Failure - No Producer Identified reply for "
                           "event: {}".format(event))
            fail = True

    if fail :
        return(3)

    logger.info("All {} detector event(s) received Identify Producer "
                "replies".format(len(detector_events)))
    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
