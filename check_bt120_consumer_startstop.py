#!/usr/bin/env python3.10
'''
This checks the consumer's response to Stop and Start events.

First sends a sync sequence for 01:23 AM July 22, 2023 at rate 4X, running.
Then sends a Stop Event and queries the consumer to verify it still
reports consuming the Stop event.
Then sends a Start Event and queries the consumer to verify it still
reports consuming the Start event.

Note: consumers using Consumer Range Identified (per Standard section
6.1) will reply Consumer Identified Unknown for all range-matched
events.  Consumers that register individual events may reply Active
or Inactive.  Both are valid.

Usage:
python3.10 check_bt110_consumer_startstop.py

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

    valid_states = ("active", "unknown")

    stop_event  = _clock_event(DEFAULT_CLOCK_ID, 0xF001)
    start_event = _clock_event(DEFAULT_CLOCK_ID, 0xF002)

    # Send sync sequence for 01:23 AM July 22, 2023, rate 4X, running
    # 1. PID Valid for Start (0xF002)
    _send_pid_valid(start_event)
    # 2. PID Valid for Report Rate 4X (0x4010)
    _send_pid_valid(_clock_event(DEFAULT_CLOCK_ID, 0x4010))
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

    # Verify consumer reports consuming Start after sync
    state = _query_consumer_state(start_event, destination, logger)
    if state is None :
        logger.warning("Failure - no Consumer Identified reply for "
                       "Start (0xF002) after sync")
        return (3)
    if state not in valid_states :
        logger.warning("Failure - Start (0xF002) reported as {} after "
                       "sync (expected active or unknown)".format(state))
        return (3)

    olcbchecker.purgeMessages()

    # Send Stop Event
    _send_pcer(stop_event)

    time.sleep(0.5)
    olcbchecker.purgeMessages()

    # Verify consumer still responds for Stop event
    state = _query_consumer_state(stop_event, destination, logger)
    if state is None :
        logger.warning("Failure - no Consumer Identified reply for "
                       "Stop (0xF001) after Stop event")
        return (3)
    if state not in valid_states :
        logger.warning("Failure - Stop (0xF001) reported as {} after "
                       "Stop event (expected active or unknown)"
                       .format(state))
        return (3)

    olcbchecker.purgeMessages()

    # Send Start Event
    _send_pcer(start_event)

    time.sleep(0.5)
    olcbchecker.purgeMessages()

    # Verify consumer still responds for Start event
    state = _query_consumer_state(start_event, destination, logger)
    if state is None :
        logger.warning("Failure - no Consumer Identified reply for "
                       "Start (0xF002) after Start event")
        return (3)
    if state not in valid_states :
        logger.warning("Failure - Start (0xF002) reported as {} after "
                       "Start event (expected active or unknown)"
                       .format(state))
        return (3)

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
