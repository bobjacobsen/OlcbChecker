#!/usr/bin/env python3.10
'''
This checks that Clock Set operations produce immediate Report events
before the 3-second delayed synchronization sequence, per Standard section 6.5.

Sends a Set Time event for 05:30 AM and verifies a Report Time event for
05:30 AM is received within 1 second, before the full sync sequence.

Usage:
python3.10 check_bt30_immediate.py

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

# Default Fast Clock upper 6 bytes
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

    # Send Set Time for 05:30 AM
    # byte 6 = 0x80 + 5 = 0x85, byte 7 = 30 = 0x1E
    send_time = time.time()
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0x851E))

    # Wait for an immediate Report Time event (PCER) for 05:30 AM
    # Report Time: byte 6 = 0x05, byte 7 = 0x1E -> suffix 0x051E
    expected_report_suffix = 0x051E
    got_immediate_report = False

    while True :
        try :
            received = olcbchecker.getMessage(timeout=1.5)

            if destination != received.source :
                continue

            event_id = EventID(received.data)
            raw = event_id.eventId
            upper = (raw >> 16) & 0xFFFFFFFFFFFF
            if upper != DEFAULT_CLOCK_ID :
                continue

            suffix = raw & 0xFFFF

            # Check for the immediate Report Time PCER
            if received.mti == MTI.Producer_Consumer_Event_Report :
                if suffix == expected_report_suffix :
                    elapsed = time.time() - send_time
                    if elapsed > 2.0 :
                        logger.warning("Failure - Report Time received but took "
                                       "{:.1f}s (expected within ~1s, before "
                                       "3-second sync)".format(elapsed))
                        return (3)
                    got_immediate_report = True
                    break

            # A PID Valid for Report Time also acceptable as immediate report
            if received.mti == MTI.Producer_Identified_Active :
                if suffix == expected_report_suffix :
                    elapsed = time.time() - send_time
                    if elapsed > 2.0 :
                        logger.warning("Failure - Report Time PID received but "
                                       "took {:.1f}s".format(elapsed))
                        return (3)
                    got_immediate_report = True
                    break

        except Empty :
            logger.warning("Failure - did not receive immediate Report Time "
                           "event within timeout")
            return (3)

    if not got_immediate_report :
        logger.warning("Failure - no immediate Report Time event received")
        return (3)

    # Now verify the full sync sequence arrives approximately 3 seconds
    # after the Set command. We just need to see the sync start
    # (PID Valid for Start/Stop).
    got_sync = False
    while True :
        try :
            received = olcbchecker.getMessage(timeout=5.0)

            if destination != received.source :
                continue

            if received.mti != MTI.Producer_Identified_Active :
                continue

            event_id = EventID(received.data)
            raw = event_id.eventId
            upper = (raw >> 16) & 0xFFFFFFFFFFFF
            if upper != DEFAULT_CLOCK_ID :
                continue

            suffix = raw & 0xFFFF
            if suffix == 0xF001 or suffix == 0xF002 :
                got_sync = True
                break

        except Empty :
            logger.warning("Failure - did not receive sync sequence after "
                           "immediate report")
            return (3)

    if not got_sync :
        logger.warning("Failure - sync sequence not received")
        return (3)

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
