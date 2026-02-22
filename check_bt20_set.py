#!/usr/bin/env python3.10
'''
This checks that Clock Set operations result in new clock settings followed by
a Clock Synchronization sequence per Standard sections 6.5 and 6.3.

Sets the clock to 01:23 AM on July 22, 2023 at rate 4X, stopped.
Then waits up to 4 seconds for a synchronization sequence and verifies
the values match what was set.

Usage:
python3.10 check_bt20_set.py

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
    return EventID((clock_id << 16) | suffix)

def _send_event(event_id) :
    '''Send a PCER with the given event ID.'''
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

    # Send Set commands for: 01:23 AM, July 22, 2023, rate 4X, stopped
    # Set Time: byte 6 = 0x80 + hour(1) = 0x81, byte 7 = minute(23) = 0x17
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0x8117))

    # Set Date: byte 6 = 0xA0 + month(7) = 0xA7, byte 7 = day(22) = 0x16
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0xA716))

    # Set Year: 0xB000 + 2023 = 0xB7E7
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0xB7E7))

    # Set Rate: 0xC000 + rate. Rate is fixed-point rrrrrrrrrr.rr
    # 4.00 = 4 * 4 = 16 = 0x0010
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0xC010))

    # Stop: 0xF001
    _send_event(_clock_event(DEFAULT_CLOCK_ID, 0xF001))

    # Now wait up to 4 seconds for the Clock Synchronization sequence
    # and verify the values match what was set.

    # Expected values in the sync sequence:
    # 1. PID Valid for Stop (0xF001)
    # 2. PID Valid for Report Rate = 4X (0x4010)
    # 3. PID Valid for Report Year = 2023 (0x37E7)
    # 4. PID Valid for Report Date = July 22 (0x2716)
    # 5. PID Valid for Report Time = 01:23 (0x0117)
    # 6. PCER for Report Time next minute = 01:24 (0x0118)

    expected_steps = [
        ("Stop",        MTI.Producer_Identified_Active, 0xF001),
        ("Rate 4X",     MTI.Producer_Identified_Active, 0x4010),
        ("Year 2023",   MTI.Producer_Identified_Active, 0x37E7),
        ("Date Jul 22", MTI.Producer_Identified_Active, 0x2716),
        ("Time 01:23",  MTI.Producer_Identified_Active, 0x0117),
        ("Time 01:24",  MTI.Producer_Consumer_Event_Report, 0x0118),
    ]

    step = 0
    while step < len(expected_steps) :
        step_name, expected_mti, expected_suffix = expected_steps[step]
        try :
            received = olcbchecker.getMessage(timeout=5.0)

            if destination != received.source :
                continue

            if received.mti != expected_mti :
                continue

            event_id = EventID(received.data)
            raw = event_id.eventId

            upper = (raw >> 16) & 0xFFFFFFFFFFFF
            if upper != DEFAULT_CLOCK_ID :
                continue

            actual_suffix = raw & 0xFFFF

            if actual_suffix != expected_suffix :
                logger.warning("Failure - step {} ({}) expected suffix 0x{:04X} "
                               "but got 0x{:04X}".format(
                                   step + 1, step_name,
                                   expected_suffix, actual_suffix))
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
