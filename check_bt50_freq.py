#!/usr/bin/env python3.10
'''
This checks the timing constraints on Report Time Events per Standard
section 6.2: no more than once per real world minute and no less than
once per real world hour.

Sets the clock to 01:00 AM at rate 4X running, then monitors for Report
Time Events over at least 2 real world minutes.

Usage:
python3.10 check_bt50_freq.py

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

def check():
    import olcbchecker.setup

    logger = logging.getLogger("BCAST_TIME")

    olcbchecker.purgeMessages()

    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    # Set clock to 01:00 AM, rate 4X, running
    # Set Time: 0x80 + 1 = 0x81, minute 0 = 0x00 -> 0x8100
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0x8100))
    # Set Rate 4X: 4*4=16=0x10 -> 0xC010
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0xC010))
    # Start: 0xF002
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0xF002))

    # Wait for the sync sequence to complete before monitoring
    # (3 seconds + time for sync messages)
    time.sleep(5.0)
    olcbchecker.purgeMessages()

    # Monitor for Report Time PCER events over 130 seconds (~2+ real minutes)
    monitor_duration = 130.0
    start_time = time.time()
    deadline = start_time + monitor_duration

    report_times = []  # list of real-world timestamps when Report Time PCERs arrive

    logger.info("Monitoring Report Time events for ~{:.0f} seconds...".format(
        monitor_duration))

    while True :
        remaining = deadline - time.time()
        if remaining <= 0 :
            break

        try :
            timeout = min(remaining, 2.0)
            received = olcbchecker.getMessage(timeout=timeout)

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
            if _is_report_time_suffix(suffix) :
                report_times.append(time.time())

        except Empty :
            continue

    # Check: at least one Report Time Event received
    if len(report_times) == 0 :
        logger.warning("Failure - no Report Time Events received during "
                       "{:.0f} second monitoring period".format(monitor_duration))
        return (3)

    # Check: no two Report Time Events less than 1 real minute apart
    for i in range(1, len(report_times)) :
        gap = report_times[i] - report_times[i - 1]
        if gap < 55.0 :  # allow 5 second tolerance
            logger.warning("Failure - Report Time Events received {:.1f}s apart "
                           "(minimum is 60s real time)".format(gap))
            return (3)

    logger.info("Passed - received {} Report Time Events".format(
        len(report_times)))
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
