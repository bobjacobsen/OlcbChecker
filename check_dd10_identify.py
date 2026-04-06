#!/usr/bin/env python3.10
'''
Check that a DCC detector node responds to Identify Events Addressed
with Producer Identified messages whose Event IDs match the detector
format (upper 6 bytes equal to the node's own ID).

Usage:
python3.10 check_dd10_identify.py

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

    # pull any early received messages
    olcbchecker.purgeMessages()

    # get configured DUT node ID
    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    # DCC Detector has no PIP bit, but it requires Event Exchange
    if olcbchecker.isCheckPip() :
        pipSet = olcbchecker.gatherPIP(destination)
        if pipSet is None:
            logger.warning("Failed in setup, no PIP information received")
            return (2)
        if not PIP.EVENT_EXCHANGE_PROTOCOL in pipSet :
            logger.info("Passed - due to Event Exchange not in PIP")
            return(0)

    # send Identify Events Addressed to provoke response
    message = Message(MTI.Identify_Events_Addressed,
                      NodeID(olcbchecker.ownnodeid()), destination)

    producerIdMTIs = [MTI.Producer_Identified_Unknown,
                      MTI.Producer_Identified_Active,
                      MTI.Producer_Identified_Inactive,
                      MTI.Producer_Range_Identified]

    node_id_int = destination.nodeId
    detector_events = []
    other_events = []

    olcbchecker.sendMessage(message)

    while True :
        try :
            received = olcbchecker.getMessage(timeout=2.0)
            if received.mti not in producerIdMTIs :
                continue
            if destination != received.source :
                continue

            event = EventID(received.data)
            if is_detector_event(event.eventId, node_id_int) :
                detector_events.append((event, received.mti))
            else :
                other_events.append((event, received.mti))

        except Empty:
            break

    if len(detector_events) == 0 :
        logger.warning("Failure - No Producer Identified events with detector "
                       "format (upper 6 bytes matching node ID) received")
        return(3)

    logger.info("Found {} detector event(s), {} other event(s)".format(
        len(detector_events), len(other_events)))
    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
