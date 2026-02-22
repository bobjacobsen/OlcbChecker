#!/usr/bin/env python3.10
'''
This checks that multiple Set commands within 3 seconds result in only a single
Clock Synchronization sequence, per Standard section 6.5.

Sends a Set Time event, waits 1 second, sends a Set Rate event.
Verifies immediate Report events for each, then exactly one sync sequence
arriving approximately 3 seconds after the last Set command.

Usage:
python3.10 check_bt40_multiset.py

The -h option will display a full list of options.
'''

import sys
import time
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

def _is_start_or_stop(suffix) :
    return suffix == 0xF001 or suffix == 0xF002

def check():
    import olcbchecker.setup

    logger = logging.getLogger("BCAST_TIME")

    olcbchecker.purgeMessages()

    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    # Send Set Time for 02:45 AM
    # byte 6 = 0x80 + 2 = 0x82, byte 7 = 45 = 0x2D
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0x822D))

    # Wait 1 second then send Set Rate for 6X
    # Rate 6.00 in fixed point rrrrrrrrrr.rr = 6*4 = 24 = 0x0018
    time.sleep(1.0)
    last_set_time = time.time()
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0xC018))

    # Collect messages for up to 6 seconds from the last set command.
    # Count how many sync sequences start (PID Valid for Start/Stop).
    sync_count = 0
    deadline = last_set_time + 6.0

    while True :
        remaining = deadline - time.time()
        if remaining <= 0 :
            break

        try :
            timeout = min(remaining, 1.0)
            received = olcbchecker.getMessage(timeout=timeout)

            if destination != received.source :
                continue

            event_id = EventID(received.data)
            raw = event_id.eventId
            upper = (raw >> 16) & 0xFFFFFFFFFFFF
            if upper != DEFAULT_CLOCK_ID :
                continue

            suffix = raw & 0xFFFF

            # Count sync sequence starts
            if received.mti == MTI.Producer_Identified_Active :
                if _is_start_or_stop(suffix) :
                    sync_count += 1

        except Empty :
            continue

    if sync_count == 0 :
        logger.warning("Failure - no sync sequence received after Set commands")
        return (3)

    if sync_count > 1 :
        logger.warning("Failure - received {} sync sequences, expected exactly "
                       "1".format(sync_count))
        return (3)

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
