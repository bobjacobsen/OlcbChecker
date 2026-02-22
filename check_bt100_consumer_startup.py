#!/usr/bin/env python3.10
'''
This checks the consumer startup behavior per Standard section 6.1.

The node is manually restarted. The resulting traffic is checked for
Consumer Range Identified or Consumer Identified messages for the
clock's event ID range.

Usage:
python3.10 check_bt90_consumer_startup.py

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
    print("Please reset/restart the clock consumer node now")

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

    # Collect messages and check for Consumer Range Identified or
    # Consumer Identified messages for the clock range
    consumerIdMTIs = [MTI.Consumer_Identified_Unknown,
                      MTI.Consumer_Identified_Active,
                      MTI.Consumer_Identified_Inactive,
                      MTI.Consumer_Range_Identified]

    got_consumer_id = False

    while True :
        try :
            received = olcbchecker.getMessage(timeout=5.0)

            if destination != received.source :
                continue

            if received.mti not in consumerIdMTIs :
                continue

            event_id = EventID(received.data)
            raw = event_id.eventId
            if _is_in_clock_range(raw, DEFAULT_CLOCK_ID) :
                got_consumer_id = True
                break

        except Empty :
            break

    if not got_consumer_id :
        logger.warning("Failure - no Consumer Range Identified or Consumer "
                       "Identified messages received for clock range")
        return (3)

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
