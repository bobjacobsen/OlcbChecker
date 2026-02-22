#!/usr/bin/env python3.10
'''
This checks that a Report Time Event is produced when requested via
Consumer Identified, per Standard section 6.2 bullet 2.

Sends a Consumer Identified for 01:24 AM July 22, 2023.
Sets the clock to 01:23 AM July 22, 2023 at rate 5X running.
Waits up to 30 seconds for the 01:24 AM Report Time Event.

Usage:
python3.10 check_bt60_requested.py

The -h option will display a full list of options.
'''

import sys
import logging

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.eventid import EventID

from queue import Empty

DEFAULT_CLOCK_ID = 0x010100000100

def _clock_event(clock_id, suffix) :
    return EventID((clock_id << 16) | suffix)

def _send_event(event_id) :
    import olcbchecker
    message = Message(MTI.Producer_Consumer_Event_Report,
                      NodeID(olcbchecker.ownnodeid()), None,
                      event_id.toArray())
    olcbchecker.sendMessage(message)

def check():
    import olcbchecker.setup

    logger = logging.getLogger("BCAST_TIME")

    olcbchecker.purgeMessages()

    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    # Send Consumer Identified for 01:24 AM
    # Report Time 01:24 = byte 6: 0x01, byte 7: 0x18 -> suffix 0x0118
    requested_event = _clock_event(DEFAULT_CLOCK_ID, 0x0118)
    message = Message(MTI.Consumer_Identified_Active,
                      NodeID(olcbchecker.ownnodeid()), None,
                      requested_event.toArray())
    olcbchecker.sendMessage(message)

    # Set clock to 01:23 AM July 22, 2023 at rate 5X, running
    # Set Time: 0x80 + 1 = 0x81, minute 23 = 0x17 -> 0x8117
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0x8117))
    # Set Date: 0xA0 + 7 = 0xA7, day 22 = 0x16 -> 0xA716
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0xA716))
    # Set Year: 0xB000 + 2023 = 0xB7E7
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0xB7E7))
    # Set Rate 5X: 5*4 = 20 = 0x14 -> 0xC014
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0xC014))
    # Start: 0xF002
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0xF002))

    # Wait up to 30 seconds for the 01:24 AM Report Time Event (PCER)
    # At 5X rate, 1 fast minute = 12 real seconds, so should arrive in ~12s
    expected_suffix = 0x0118  # Report Time 01:24

    while True :
        try :
            received = olcbchecker.getMessage(timeout=30.0)

            if destination != received.source :
                continue

            if received.mti != MTI.Producer_Consumer_Event_Report :
                continue

            event_id = EventID(received.data)
            raw = event_id.eventId
            upper = (raw >> 16) & 0xFFFFFFFFFFFF
            if upper != DEFAULT_CLOCK_ID :
                continue

            suffix = raw & 0xFFFF
            if suffix == expected_suffix :
                logger.info("Passed")
                return 0

        except Empty :
            logger.warning("Failure - did not receive requested 01:24 AM "
                           "Report Time Event within 30 seconds")
            return (3)

    logger.warning("Failure - unexpected exit from receive loop")
    return (3)

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
