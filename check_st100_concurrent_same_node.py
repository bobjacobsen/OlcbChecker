#!/usr/bin/env python3.10
'''
This checks that the DUT can handle two concurrent streams from the
same source node with different Source Stream IDs.

Opens stream A (SID 0xA0) and stream B (SID 0xB0), sends data
interleaved on both, and verifies each Proceed carries the correct
SID/DID pair for its stream.

Per StreamTransportTN section 1, a pair of nodes may maintain up to
255 simultaneously open streams.  A DUT that rejects the second stream
is spec-legal -- this test passes with info in that case.

Usage:
python3.10 check_st100_concurrent_same_node.py

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
    '''Attempt to open a stream. Returns (buf_size, did) or (None, None).'''
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
                return (None, None)
            if received.mti == MTI.Stream_Initiate_Reply :
                if NodeID(olcbchecker.ownnodeid()) != received.destination :
                    continue
                if len(received.data) < 6 :
                    return (None, None)
                buf_size = (received.data[0] << 8) | received.data[1]
                flags = (received.data[2] << 8) | received.data[3]
                did = received.data[5]
                if (flags == 0x0000 or flags == 0x8000) and buf_size > 0 :
                    return (buf_size, did)
                else :
                    return (None, None)
            continue
        except Empty:
            return (None, None)


def _send_buffer(destination, did, buf_size, offset=0):
    '''Send exactly buf_size bytes of stream data.'''
    import olcbchecker
    bytes_sent = 0
    while bytes_sent < buf_size :
        chunk_size = min(buf_size - bytes_sent, 64)
        payload = [((offset + bytes_sent + i) & 0xFF)
                   for i in range(chunk_size)]
        data = [did] + payload
        message = Message(MTI.Stream_Data_Send,
                          NodeID(olcbchecker.ownnodeid()), destination, data)
        olcbchecker.sendMessage(message)
        bytes_sent += chunk_size


def _wait_for_proceed(logger, destination, sid, did, label):
    '''Wait for a Stream Data Proceed. Returns True on success.'''
    import olcbchecker
    while True :
        try :
            received = olcbchecker.getMessage(3.0)
            if destination != received.source :
                continue
            if received.mti == MTI.Stream_Data_Proceed :
                if len(received.data) < 2 :
                    logger.warning("Failure - Proceed too short ({})"
                                   .format(label))
                    return False
                if received.data[0] != sid :
                    logger.warning("Failure - Proceed SID mismatch ({}): "
                                   "expected 0x{:02X} got 0x{:02X}"
                                   .format(label, sid, received.data[0]))
                    return False
                if received.data[1] != did :
                    logger.warning("Failure - Proceed DID mismatch ({}): "
                                   "expected 0x{:02X} got 0x{:02X}"
                                   .format(label, did, received.data[1]))
                    return False
                return True
            if received.mti == MTI.Terminate_Due_To_Error :
                logger.warning("Failure - Terminate Due To Error ({})"
                               .format(label))
                return False
            continue
        except Empty:
            logger.warning("Failure - no Proceed ({})"
                           .format(label))
            return False


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

    # Open stream A
    sid_a = 0xA0
    buf_a, did_a = _open_stream(logger, destination, 256, sid_a)

    if buf_a is None :
        logger.info("Passed - node does not accept streams, cannot "
                     "test concurrent streams")
        return 0

    # Open stream B
    sid_b = 0xB0
    buf_b, did_b = _open_stream(logger, destination, 256, sid_b)

    if buf_b is None :
        _close_stream(destination, sid_a, did_a)
        logger.info("Passed - node rejected second concurrent stream, "
                     "spec-legal single-stream node")
        return 0

    # Two rounds of interleaved transfer
    for round_num in range(1, 3) :

        # Send buffer on stream A
        _send_buffer(destination, did_a, buf_a,
                     offset=((round_num - 1) * buf_a))
        if not _wait_for_proceed(logger, destination, sid_a, did_a,
                                 "A round {}".format(round_num)) :
            _close_stream(destination, sid_a, did_a)
            _close_stream(destination, sid_b, did_b)
            return(3)

        # Send buffer on stream B
        _send_buffer(destination, did_b, buf_b,
                     offset=((round_num - 1) * buf_b))
        if not _wait_for_proceed(logger, destination, sid_b, did_b,
                                 "B round {}".format(round_num)) :
            _close_stream(destination, sid_a, did_a)
            _close_stream(destination, sid_b, did_b)
            return(3)

    # Close both streams
    _close_stream(destination, sid_a, did_a)
    _close_stream(destination, sid_b, did_b)

    logger.info("Passed")
    return 0


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
