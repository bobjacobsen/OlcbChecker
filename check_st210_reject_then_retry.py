#!/usr/bin/env python3.10
'''
This checks that a node recovers after rejecting a stream initiate and
accepts a retry once resources are freed.

Per StreamTransportS section 6.2, a node may reject a stream initiate
with a temporary error (0x2020 buffer unavailable).  After the
condition clears, a retry should succeed.

Sequence:
1. PIP guard
2. Open streams until one is rejected (temporary error)
3. If no rejection after 4 attempts, pass -- node has deep pool
4. Close one open stream to free resources
5. Retry the rejected initiate
6. Verify the retry succeeds
7. Close all streams

Usage:
python3.10 check_st210_reject_then_retry.py

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


def _open_stream(logger, destination, proposed_size, sid):
    '''Attempt to open a stream.
    Returns (buf_size, did, rejected) where rejected is True if the
    node sent a rejection or OIR.'''
    import olcbchecker
    data = [(proposed_size >> 8) & 0xFF, proposed_size & 0xFF,
            0x00, 0x00, sid]
    message = Message(MTI.Stream_Initiate_Request,
                      NodeID(olcbchecker.ownnodeid()), destination, data)
    olcbchecker.sendMessage(message)

    while True :
        try :
            received = olcbchecker.getMessage(2.0)
            if destination != received.source :
                continue
            if received.mti == MTI.Optional_Interaction_Rejected :
                return (None, None, True)
            if received.mti == MTI.Stream_Initiate_Reply :
                if NodeID(olcbchecker.ownnodeid()) != received.destination :
                    continue
                if len(received.data) < 6 :
                    return (None, None, True)
                buf_size = (received.data[0] << 8) | received.data[1]
                flags = (received.data[2] << 8) | received.data[3]
                did = received.data[5]
                if (flags == 0x0000 or flags == 0x8000) and buf_size > 0 :
                    return (buf_size, did, False)
                else :
                    return (None, None, True)
            continue
        except Empty:
            return (None, None, True)


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

    # Open streams until we get a rejection
    max_attempts = 4
    open_streams = []  # list of (sid, did)
    rejected_sid = None

    for i in range(max_attempts) :
        sid = 0xD0 + i
        buf_size, did, rejected = _open_stream(
            logger, destination, 256, sid)

        if rejected and len(open_streams) == 0 :
            logger.info("Passed - node does not accept streams, "
                         "cannot test reject-then-retry")
            return 0

        if rejected :
            rejected_sid = sid
            logger.info("  stream 0x{:02X} rejected after {} "
                         "accepted".format(sid, len(open_streams)))
            break

        open_streams.append((sid, did))

    if rejected_sid is None :
        # Node accepted all 4 -- deep pool, cannot force rejection
        for sid, did in open_streams :
            _close_stream(destination, sid, did)
        logger.info("Passed - node accepted all {} streams, "
                     "cannot force rejection".format(max_attempts))
        return 0

    # Close one stream to free resources
    freed_sid, freed_did = open_streams.pop(0)
    _close_stream(destination, freed_sid, freed_did)
    logger.info("  closed stream 0x{:02X} to free resources".format(
        freed_sid))

    # Brief pause for the node to process the close
    olcbchecker.purgeMessages()
    time.sleep(0.3)

    # Retry the rejected SID
    buf_size, did, rejected = _open_stream(
        logger, destination, 256, rejected_sid)

    if rejected :
        logger.warning("Failure - retry after freeing resources was "
                       "still rejected")
        for sid, did_open in open_streams :
            _close_stream(destination, sid, did_open)
        return(3)

    logger.info("  retry stream 0x{:02X} accepted with DID "
                 "0x{:02X}".format(rejected_sid, did))

    # Close all remaining streams
    open_streams.append((rejected_sid, did))
    for sid, did_open in open_streams :
        _close_stream(destination, sid, did_open)

    logger.info("Passed")
    return 0


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
