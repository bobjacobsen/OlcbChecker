#!/usr/bin/env python3.10
'''
This checks the consumer's response to a Clock Synchronization sequence
per Standard section 6.3.

Sends the synchronization sequence for 01:23 AM on July 22, 2023 at
rate 4X, stopped.  Then uses Identify Consumer messages to verify the
consumer responds for each clock event ID, confirming it consumes
the clock range.

Note: consumers using Consumer Range Identified (per Standard section
6.1) will reply Consumer Identified Unknown for range-matched events.
Consumers that register individual events may reply Active.  Both
are valid.

Usage:
python3.10 check_bt100_consumer_sync.py

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
    '''Send a Producer Identified Valid (Active) message.'''
    import olcbchecker
    message = Message(MTI.Producer_Identified_Active,
                      NodeID(olcbchecker.ownnodeid()), None,
                      event_id.toArray())
    olcbchecker.sendMessage(message)

def _send_pcer(event_id) :
    '''Send a Producer/Consumer Event Report message.'''
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

    # Send the Clock Synchronization sequence for:
    # 01:23 AM, July 22, 2023, rate 4X, stopped

    # 1. PID Valid for Stop (0xF001)
    _send_pid_valid(_clock_event(DEFAULT_CLOCK_ID, 0xF001))

    # 2. PID Valid for Report Rate 4X (0x4010)
    _send_pid_valid(_clock_event(DEFAULT_CLOCK_ID, 0x4010))

    # 3. PID Valid for Report Year 2023 (0x37E7)
    _send_pid_valid(_clock_event(DEFAULT_CLOCK_ID, 0x37E7))

    # 4. PID Valid for Report Date July 22 (0x2716)
    _send_pid_valid(_clock_event(DEFAULT_CLOCK_ID, 0x2716))

    # 5. PID Valid for Report Time 01:23 (0x0117)
    _send_pid_valid(_clock_event(DEFAULT_CLOCK_ID, 0x0117))

    # 6. PCER for Report Time next minute 01:24 (0x0118)
    _send_pcer(_clock_event(DEFAULT_CLOCK_ID, 0x0118))

    # Allow the consumer time to process the sequence
    time.sleep(1.0)
    olcbchecker.purgeMessages()

    # Now verify the consumer recognizes the clock events by sending
    # Identify Consumer for each expected event ID.
    #
    # A consumer that uses Consumer Range Identified (as the Broadcast
    # Time Standard section 6.1 allows) will reply Consumer Identified
    # Unknown for range-matched events.  A consumer that registers
    # individual events may reply Active.  Either response confirms
    # the consumer is tracking the clock.  Only no reply indicates
    # the consumer does not consume the event at all.

    valid_states = ("active", "unknown")

    checks = [
        ("Stop state",       0xF001),
        ("Rate 4X",          0x4010),
        ("Year 2023",        0x37E7),
        ("Date July 22",     0x2716),
        ("Time 01:23",       0x0117),
    ]

    for name, suffix in checks :
        event_id = _clock_event(DEFAULT_CLOCK_ID, suffix)
        state = _query_consumer_state(event_id, destination, logger)

        if state is None :
            logger.warning("Failure - no Consumer Identified reply "
                           "for {} (0x{:04X})".format(name, suffix))
            return (3)

        if state not in valid_states :
            logger.warning("Failure - {} (0x{:04X}) reported as {} "
                           "(expected active or unknown)"
                           .format(name, suffix, state))
            return (3)

    # Verify Start (0xF002) is also consumed (in the clock range)
    start_event = _clock_event(DEFAULT_CLOCK_ID, 0xF002)
    state = _query_consumer_state(start_event, destination, logger)
    if state is None :
        logger.warning("Failure - no Consumer Identified reply for "
                       "Start (0xF002)")
        return (3)

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
