#!/usr/bin/env python3.10
'''
Check whether a DCC detector advertises the track-empty sentinel (0x3800).
This is info-only per the spec -- a detector may but does not have to
use the track-empty event.  This check never fails on absence.

Usage:
python3.10 check_dd40_track_empty.py

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
                                                 is_track_empty,
                                                 extract_direction,
                                                 DIRECTION_NAMES)

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
    track_empty_events = []

    while True :
        try :
            received = olcbchecker.getMessage()
            if received.mti not in producerIdMTIs :
                continue
            if destination != received.source :
                continue

            event = EventID(received.data)
            if is_detector_event(event.eventId, node_id_int) :
                if is_track_empty(event.eventId) :
                    direction = extract_direction(event.eventId)
                    dir_name = DIRECTION_NAMES.get(direction,
                                                   "unknown(0x{:02X})".format(direction))
                    track_empty_events.append((event, dir_name))

        except Empty:
            break

    if len(track_empty_events) == 0 :
        logger.info("Info - Detector does not advertise track-empty sentinel "
                    "(this is permitted by the spec)")
    else :
        logger.info("Info - Detector advertises {} track-empty event(s):".format(
            len(track_empty_events)))
        for event, dir_name in track_empty_events :
            logger.info("  {} - {}".format(event, dir_name))

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
