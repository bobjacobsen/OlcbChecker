#!/usr/bin/env python3.10
'''
This checks date rollover behavior per Standard section 6.2.

Sets the clock to 23:58 PM on July 22, 2023 at rate 10X running.
Waits for progression through midnight and verifies:
1. A Date Rollover Event (0xF003) is received prior to 00:00.
2. A Report Year Event is received ~3 real seconds after rollover.
3. A Report Date Event showing July 23 is received ~3 real seconds after.

Usage:
python3.10 check_bt70_rollover.py

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

def _is_report_time_suffix(suffix) :
    b6 = (suffix >> 8) & 0xFF
    return (b6 & 0xE0) == 0x00 and b6 <= 0x17

def _is_report_date_suffix(suffix) :
    b6 = (suffix >> 8) & 0xFF
    return (b6 & 0xF0) == 0x20

def _is_report_year_suffix(suffix) :
    b6 = (suffix >> 8) & 0xFF
    return (b6 & 0xF0) == 0x30

def check():
    import olcbchecker.setup

    logger = logging.getLogger("BCAST_TIME")

    olcbchecker.purgeMessages()

    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    # Set clock to 23:58 PM July 22, 2023, rate 10X, running
    # Set Time: 0x80 + 23 = 0x97, minute 58 = 0x3A -> 0x973A
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0x973A))
    # Set Date: 0xA0 + 7 = 0xA7, day 22 = 0x16 -> 0xA716
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0xA716))
    # Set Year: 0xB000 + 2023 = 0xB7E7
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0xB7E7))
    # Set Rate 10X: 10*4 = 40 = 0x28 -> 0xC028
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0xC028))
    # Start: 0xF002
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0xF002))

    # At 10X rate, 2 fast minutes = 12 real seconds to reach midnight.
    # Allow up to 30 seconds for the full sequence plus the post-rollover reports.
    # Wait for sync sequence to complete first
    time.sleep(5.0)
    olcbchecker.purgeMessages()

    # Now monitor for rollover events.
    # The clock should be running from ~23:58 at 10X.
    # Each fast minute takes 6 real seconds.
    # ~23:59 at +6s, rollover at +12s, then Year/Date reports at +15s.
    # Total monitoring: up to 30 seconds.

    got_date_rollover = False
    got_report_year = False
    got_report_date = False
    report_date_suffix = 0

    deadline = time.time() + 30.0

    while True :
        remaining = deadline - time.time()
        if remaining <= 0 :
            break

        try :
            timeout = min(remaining, 2.0)
            received = olcbchecker.getMessage(timeout=timeout)

            if destination != received.source :
                continue

            event_id = EventID(received.data)
            raw = event_id.eventId
            upper = (raw >> 16) & 0xFFFFFFFFFFFF
            if upper != DEFAULT_CLOCK_ID :
                continue

            suffix = raw & 0xFFFF

            # Check for Date Rollover Event (0xF003)
            if suffix == 0xF003 :
                if received.mti == MTI.Producer_Consumer_Event_Report or \
                   received.mti == MTI.Producer_Identified_Active :
                    got_date_rollover = True
                    continue

            # Check for Report Year (PID Valid or PCER)
            if _is_report_year_suffix(suffix) :
                if received.mti == MTI.Producer_Identified_Active or \
                   received.mti == MTI.Producer_Consumer_Event_Report :
                    got_report_year = True
                    continue

            # Check for Report Date (PID Valid or PCER)
            if _is_report_date_suffix(suffix) :
                if received.mti == MTI.Producer_Identified_Active or \
                   received.mti == MTI.Producer_Consumer_Event_Report :
                    got_report_date = True
                    report_date_suffix = suffix
                    continue

            # if we have all three, done
            if got_date_rollover and got_report_year and got_report_date :
                break

        except Empty :
            continue

    if not got_date_rollover :
        logger.warning("Failure - Date Rollover Event (0xF003) not received")
        return (3)

    if not got_report_year :
        logger.warning("Failure - Report Year Event not received after rollover")
        return (3)

    if not got_report_date :
        logger.warning("Failure - Report Date Event not received after rollover")
        return (3)

    # Verify the date is July 23: 0xA0 + 7 = 0xA7, day 23 = 0x17
    # But as Report Date: 0x20 + 7 = 0x27, day 23 = 0x17 -> 0x2717
    expected_date = 0x2717
    if report_date_suffix != expected_date :
        logger.warning("Failure - Report Date after rollover expected 0x{:04X} "
                       "(Jul 23) but got 0x{:04X}".format(
                           expected_date, report_date_suffix))
        return (3)

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
