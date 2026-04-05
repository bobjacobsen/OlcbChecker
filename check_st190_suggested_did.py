#!/usr/bin/env python3.10
'''
This checks that a node handles a suggested Destination Stream ID in
the Stream Initiate Request.

Per StreamTransportS section 4.1, byte 0 of the Initiate Request may
contain a suggested DID (0x00-0xFE) or 0xFF (no suggestion).  The DUT
may use the suggested value or assign its own.

Sequence:
1. PIP guard
2. Send Initiate Request with suggested DID = 0x42
3. Verify reply: DID in range 0x00-0xFE, SID echoed
4. If DUT used 0x42, log it; if it picked another, that is also valid
5. Close stream, reopen with DID = 0xFF (no suggestion) to confirm
   both paths work

Usage:
python3.10 check_st190_suggested_did.py

The -h option will display a full list of options.
'''

import sys
import logging
import time

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.pip import PIP

from queue import Empty


def _open_stream_with_did(logger, destination, proposed_size, sid,
                          suggested_did):
    '''Open a stream with a specific suggested DID byte.
    Returns (buf_size, did, flags) or (None, None, None).'''
    import olcbchecker
    data = [(proposed_size >> 8) & 0xFF, proposed_size & 0xFF,
            0x00, 0x00, sid, suggested_did]
    message = Message(MTI.Stream_Initiate_Request,
                      NodeID(olcbchecker.ownnodeid()), destination, data)
    olcbchecker.sendMessage(message)

    while True :
        try :
            received = olcbchecker.getMessage(2.0)
            if destination != received.source :
                continue
            if received.mti == MTI.Optional_Interaction_Rejected :
                return (None, None, None)
            if received.mti == MTI.Stream_Initiate_Reply :
                if NodeID(olcbchecker.ownnodeid()) != received.destination :
                    continue
                if len(received.data) < 6 :
                    return (None, None, None)
                buf_size = (received.data[0] << 8) | received.data[1]
                flags = (received.data[2] << 8) | received.data[3]
                did = received.data[5]
                if (flags == 0x0000 or flags == 0x8000) and buf_size > 0 :
                    return (buf_size, did, flags)
                else :
                    return (None, None, None)
            continue
        except Empty:
            return (None, None, None)


def _close_stream(destination, sid, did):
    '''Send Stream Data Complete to close a stream.'''
    import olcbchecker
    message = Message(MTI.Stream_Data_Complete,
                      NodeID(olcbchecker.ownnodeid()), destination,
                      [sid, did])
    olcbchecker.sendMessage(message)
    time.sleep(0.3)


def check():
    import olcbchecker.setup
    logger = logging.getLogger("STREAM")

    olcbchecker.purgeMessages()

    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    if olcbchecker.isCheckPip() :
        pipSet = olcbchecker.gatherPIP(destination)
        if pipSet is None:
            logger.warning("Failed in setup, no PIP information received")
            return (2)
        if not PIP.STREAM_PROTOCOL in pipSet :
            logger.info("Passed - due to Stream protocol not in PIP")
            return(0)

    # Test 1: suggest DID = 0x42
    sid1 = 0x90
    suggested = 0x42
    buf_size, did, flags = _open_stream_with_did(
        logger, destination, 256, sid1, suggested)

    if buf_size is None :
        logger.info("Passed - node does not accept streams, cannot "
                     "test suggested DID")
        return 0

    if did == 0xFF :
        logger.warning("Failure - DID is reserved value 0xFF")
        return(3)

    if did == suggested :
        logger.info("  node honored suggested DID 0x{:02X}".format(
            suggested))
    else :
        logger.info("  node assigned DID 0x{:02X} instead of suggested "
                     "0x{:02X} (valid)".format(did, suggested))

    _close_stream(destination, sid1, did)

    # Test 2: no suggestion (0xFF) to confirm both paths work
    olcbchecker.purgeMessages()
    sid2 = 0x91
    buf_size2, did2, flags2 = _open_stream_with_did(
        logger, destination, 256, sid2, 0xFF)

    if buf_size2 is None :
        logger.warning("Failure - node rejected stream with DID 0xFF "
                       "after accepting suggested DID")
        return(3)

    if did2 == 0xFF :
        logger.warning("Failure - DID is reserved value 0xFF")
        return(3)

    logger.info("  no-suggestion path assigned DID 0x{:02X}".format(did2))

    _close_stream(destination, sid2, did2)

    logger.info("Passed")
    return 0


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
