#!/usr/bin/env python3.10
'''
This checks that a Clock Query results in a Clock Synchronization sequence
per Standard sections 6.4 and 6.3.

Usage:
python3.10 check_bt10_query.py

The -h option will display a full list of options.
'''

import sys
import logging

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.eventid import EventID

from queue import Empty

# Default Fast Clock upper 6 bytes
DEFAULT_CLOCK_ID = 0x010100000100

def _clock_event(clock_id, suffix) :
    '''Build an 8-byte event ID from a 6-byte clock ID and a 2-byte suffix.'''
    return EventID((clock_id << 16) | suffix)

def _is_report_time(event_id) :
    '''Return True if the event encodes a Report Time (byte 6 upper nibble 0 or 1).'''
    b6 = (event_id >> 8) & 0xFF
    return (b6 & 0xE0) == 0x00 and b6 <= 0x17

def _is_report_date(event_id) :
    '''Return True if the event encodes a Report Date (byte 6 upper nibble 2).'''
    b6 = (event_id >> 8) & 0xFF
    return (b6 & 0xF0) == 0x20

def _is_report_year(event_id) :
    '''Return True if the event encodes a Report Year (byte 6 upper nibble 3).'''
    b6 = (event_id >> 8) & 0xFF
    return (b6 & 0xF0) == 0x30

def _is_report_rate(event_id) :
    '''Return True if the event encodes a Report Rate (byte 6 upper nibble 4).'''
    b6 = (event_id >> 8) & 0xFF
    return (b6 & 0xF0) == 0x40

def _is_start_or_stop(event_id) :
    '''Return True if the event is a Start (0xF002) or Stop (0xF001) event.'''
    suffix = event_id & 0xFFFF
    return suffix == 0xF001 or suffix == 0xF002

def check():
    import olcbchecker.setup

    logger = logging.getLogger("BCAST_TIME")

    # pull any early received messages
    olcbchecker.purgeMessages()

    # get configured DUT node ID
    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    # send a Query Event to provoke the synchronization sequence
    query_event = _clock_event(DEFAULT_CLOCK_ID, 0xF000)
    message = Message(MTI.Producer_Consumer_Event_Report,
                      NodeID(olcbchecker.ownnodeid()), None,
                      query_event.toArray())
    olcbchecker.sendMessage(message)

    # We expect the following sequence per Standard section 6.3:
    # 1. Producer Identified Valid for Start or Stop Event ID
    # 2. Producer Identified Valid for Report Rate event
    # 3. Producer Identified Valid for Report Year event
    # 4. Producer Identified Valid for Report Date event
    # 5. Producer Identified Valid for Report Time event
    # 6. Producer/Consumer Event Report for Report Time event

    expected_steps = [
        ("Start or Stop",    MTI.Producer_Identified_Active, _is_start_or_stop),
        ("Report Rate",      MTI.Producer_Identified_Active, _is_report_rate),
        ("Report Year",      MTI.Producer_Identified_Active, _is_report_year),
        ("Report Date",      MTI.Producer_Identified_Active, _is_report_date),
        ("Report Time",      MTI.Producer_Identified_Active, _is_report_time),
        ("Report Time PCER", MTI.Producer_Consumer_Event_Report, _is_report_time),
    ]

    step = 0
    while step < len(expected_steps) :
        step_name, expected_mti, event_check = expected_steps[step]
        try :
            received = olcbchecker.getMessage(timeout=5.0)

            # ignore messages not from the DUT
            if destination != received.source :
                continue

            # check for correct MTI
            if received.mti != expected_mti :
                # allow skipping unrelated messages
                continue

            # check the event ID matches the expected type
            event_id = EventID(received.data)
            raw = event_id.eventId

            # verify this event belongs to the clock
            upper = (raw >> 16) & 0xFFFFFFFFFFFF
            if upper != DEFAULT_CLOCK_ID :
                continue

            if not event_check(raw) :
                logger.warning("Failure - step {} expected {} but got event {}".format(
                    step + 1, step_name, event_id))
                return (3)

            step += 1

        except Empty :
            logger.warning("Failure - timed out waiting for step {} ({})".format(
                step + 1, expected_steps[step][0]))
            return (3)

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
