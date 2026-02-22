#!/usr/bin/env python3.10
'''
This checks the producer startup sequence per Standard section 6.1.

The node is manually restarted. The resulting traffic is checked for:
1. Producer Range Identified and Consumer Range Identified messages.
2. A Clock Synchronization sequence (section 6.3) with all six messages.

Usage:
python3.10 check_bt80_startup.py

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

def _is_in_clock_range(event_id_raw, clock_id) :
    '''Check if the event ID upper 6 bytes match the clock ID.'''
    upper = (event_id_raw >> 16) & 0xFFFFFFFFFFFF
    return upper == clock_id

def _is_report_time(suffix) :
    b6 = (suffix >> 8) & 0xFF
    return (b6 & 0xE0) == 0x00 and b6 <= 0x17

def _is_report_rate(suffix) :
    b6 = (suffix >> 8) & 0xFF
    return (b6 & 0xF0) == 0x40

def _is_report_year(suffix) :
    b6 = (suffix >> 8) & 0xFF
    return (b6 & 0xF0) == 0x30

def _is_report_date(suffix) :
    b6 = (suffix >> 8) & 0xFF
    return (b6 & 0xF0) == 0x20

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

    # If not running interactive checks, this is considered to pass
    if olcbchecker.setup.configure.skip_interactive :
        logger.info("Interactive check skipped")
        return 0

    # prompt operator to restart node
    print("Please reset/restart the clock producer node now")

    # wait for Initialization Complete
    while True :
        try :
            received = olcbchecker.getMessage(30)

            if destination != received.source :
                continue

            if received.mti == MTI.Initialization_Complete :
                break
            if received.mti == MTI.Initialization_Complete_Simple :
                break

        except Empty :
            logger.warning("Failure - Did not see node initialize")
            return (3)

    # Now collect messages and check for required elements
    got_producer_range = False
    got_consumer_range = False

    # Sync sequence tracking
    sync_steps_seen = [False] * 6  # 6 steps per section 6.3
    sync_step = 0

    while True :
        try :
            received = olcbchecker.getMessage(timeout=5.0)

            if destination != received.source :
                continue

            # Check for Producer Range Identified
            if received.mti == MTI.Producer_Range_Identified :
                event_id = EventID(received.data)
                raw = event_id.eventId
                if _is_in_clock_range(raw, DEFAULT_CLOCK_ID) :
                    got_producer_range = True
                continue

            # Check for Consumer Range Identified
            if received.mti == MTI.Consumer_Range_Identified :
                event_id = EventID(received.data)
                raw = event_id.eventId
                if _is_in_clock_range(raw, DEFAULT_CLOCK_ID) :
                    got_consumer_range = True
                continue

            # Check sync sequence messages
            event_id = EventID(received.data)
            raw = event_id.eventId
            if not _is_in_clock_range(raw, DEFAULT_CLOCK_ID) :
                continue

            suffix = raw & 0xFFFF

            if received.mti == MTI.Producer_Identified_Active :
                if sync_step == 0 and _is_start_or_stop(suffix) :
                    sync_steps_seen[0] = True
                    sync_step = 1
                elif sync_step == 1 and _is_report_rate(suffix) :
                    sync_steps_seen[1] = True
                    sync_step = 2
                elif sync_step == 2 and _is_report_year(suffix) :
                    sync_steps_seen[2] = True
                    sync_step = 3
                elif sync_step == 3 and _is_report_date(suffix) :
                    sync_steps_seen[3] = True
                    sync_step = 4
                elif sync_step == 4 and _is_report_time(suffix) :
                    sync_steps_seen[4] = True
                    sync_step = 5

            elif received.mti == MTI.Producer_Consumer_Event_Report :
                if sync_step == 5 and _is_report_time(suffix) :
                    sync_steps_seen[5] = True
                    sync_step = 6
                    break  # done

        except Empty :
            break

    if not got_producer_range :
        logger.warning("Failure - no Producer Range Identified for clock")
        return (3)

    if not got_consumer_range :
        logger.warning("Failure - no Consumer Range Identified for clock")
        return (3)

    if not all(sync_steps_seen) :
        missing = []
        names = ["Start/Stop", "Rate", "Year", "Date", "Time PID",
                 "Time PCER"]
        for i, seen in enumerate(sync_steps_seen) :
            if not seen :
                missing.append(names[i])
        logger.warning("Failure - sync sequence incomplete, missing: "
                       "{}".format(", ".join(missing)))
        return (3)

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
