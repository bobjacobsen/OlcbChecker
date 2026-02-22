#!/usr/bin/env python3.10
'''
This checks the consumer's response to a rate change during operation.

Sends a sync sequence for 01:23 AM July 22, 2023 at rate 1X, running.
Then sends a Report Rate event for 8X and queries the consumer to verify
it reports consuming both rate events.

Note: consumers using Consumer Range Identified (per Standard section
6.1) will reply Consumer Identified Unknown for range-matched events.
Consumers that register individual events may reply Active.  Both
are valid.

Usage:
python3.10 check_bt120_consumer_rate.py

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

def _send_pid_valid(event_id) :
    import olcbchecker
    message = Message(MTI.Producer_Identified_Active,
                      NodeID(olcbchecker.ownnodeid()), None,
                      event_id.toArray())
    olcbchecker.sendMessage(message)

def _send_pcer(event_id) :
    import olcbchecker
    message = Message(MTI.Producer_Consumer_Event_Report,
                      NodeID(olcbchecker.ownnodeid()), None,
                      event_id.toArray())
    olcbchecker.sendMessage(message)

def _query_consumer_state(event_id, destination, logger) :
    '''Send an Identify Consumer for the given event ID and look for
    a Consumer Identified reply from the DUT.
    Returns "active", "inactive", "unknown", or None if no reply.'''
    import olcbchecker

    message = Message(MTI.Identify_Consumer,
                      NodeID(olcbchecker.ownnodeid()), None,
                      event_id.toArray())
    olcbchecker.sendMessage(message)

    consumerIdMTIs = {
        MTI.Consumer_Identified_Active   : "active",
        MTI.Consumer_Identified_Inactive : "inactive",
        MTI.Consumer_Identified_Unknown  : "unknown",
    }

    while True :
        try :
            received = olcbchecker.getMessage(timeout=3.0)

            if destination != received.source :
                continue

            if received.mti not in consumerIdMTIs :
                continue

            reply_event = EventID(received.data)
            if reply_event.eventId != event_id.eventId :
                continue

            return consumerIdMTIs[received.mti]

        except Empty :
            return None

def check():
    import olcbchecker.setup

    logger = logging.getLogger("BCAST_TIME")

    olcbchecker.purgeMessages()

    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    rate_1x_event = _clock_event(DEFAULT_CLOCK_ID, 0x4004)  # 1*4=4=0x04
    rate_8x_event = _clock_event(DEFAULT_CLOCK_ID, 0x4020)  # 8*4=32=0x20

    # Send sync sequence for 01:23 AM July 22, 2023, rate 1X, running
    # 1. PID Valid for Start (0xF002)
    _send_pid_valid(_clock_event(DEFAULT_CLOCK_ID, 0xF002))
    # 2. PID Valid for Report Rate 1X (0x4004)
    _send_pid_valid(rate_1x_event)
    # 3. PID Valid for Report Year 2023 (0x37E7)
    _send_pid_valid(_clock_event(DEFAULT_CLOCK_ID, 0x37E7))
    # 4. PID Valid for Report Date July 22 (0x2716)
    _send_pid_valid(_clock_event(DEFAULT_CLOCK_ID, 0x2716))
    # 5. PID Valid for Report Time 01:23 (0x0117)
    _send_pid_valid(_clock_event(DEFAULT_CLOCK_ID, 0x0117))
    # 6. PCER for Report Time 01:24 (0x0118)
    _send_pcer(_clock_event(DEFAULT_CLOCK_ID, 0x0118))

    # Allow the consumer time to process the sync sequence
    time.sleep(1.0)
    olcbchecker.purgeMessages()

    valid_states = ("active", "unknown")

    # Verify the consumer reports consuming Rate 1X after sync
    state = _query_consumer_state(rate_1x_event, destination, logger)
    if state is None :
        logger.warning("Failure - no Consumer Identified reply for "
                       "Rate 1X (0x4004) after sync")
        return (3)
    if state not in valid_states :
        logger.warning("Failure - Rate 1X (0x4004) reported as {} after "
                       "sync (expected active or unknown)"
                       .format(state))
        return (3)

    olcbchecker.purgeMessages()

    # Send Report Rate for 8X as a PCER
    _send_pcer(rate_8x_event)

    time.sleep(0.5)
    olcbchecker.purgeMessages()

    # Verify the consumer reports consuming Rate 8X after rate change
    state = _query_consumer_state(rate_8x_event, destination, logger)
    if state is None :
        logger.warning("Failure - no Consumer Identified reply for "
                       "Rate 8X (0x4020) after rate change")
        return (3)
    if state not in valid_states :
        logger.warning("Failure - Rate 8X (0x4020) reported as {} after "
                       "rate change (expected active or unknown)"
                       .format(state))
        return (3)

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
