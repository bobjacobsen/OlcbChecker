#!/usr/bin/env python3.10
'''
This checks that the DUT handles a zero-payload Stream Data Send (flush)
correctly during an active transfer.

Per StreamTransportS Section 6.3: "A Stream Data Send message may also
contain zero payload bytes. This is considered a flush, and should result
in the destination node (and any gateways in between) flushing any
internal buffering for efficiency that may be occurring."

The test sends half the buffer window, then a zero-payload flush, then
the remaining half. The DUT must not crash, not send an error, and must
send Proceed at the correct byte boundary (the flush does not count
toward the buffer window).

Usage:
python3.10 check_st170_zero_payload_flush.py

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


def _send_data(destination, did, payload_bytes):
    '''Send a chunk of stream data with the given payload bytes.'''
    import olcbchecker
    data = [did] + payload_bytes
    message = Message(MTI.Stream_Data_Send,
                      NodeID(olcbchecker.ownnodeid()), destination, data)
    olcbchecker.sendMessage(message)


def _send_flush(destination, did):
    '''Send a zero-payload Stream Data Send (flush).'''
    import olcbchecker
    data = [did]
    message = Message(MTI.Stream_Data_Send,
                      NodeID(olcbchecker.ownnodeid()), destination, data)
    olcbchecker.sendMessage(message)


def _send_bytes(destination, did, count, offset=0):
    '''Send count payload bytes in chunks of up to 64.'''
    bytes_sent = 0
    while bytes_sent < count :
        chunk_size = min(count - bytes_sent, 64)
        payload = [((offset + bytes_sent + i) & 0xFF)
                   for i in range(chunk_size)]
        _send_data(destination, did, payload)
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

    sid = 0xD0
    buf_size, did = _open_stream(logger, destination, 256, sid)

    if buf_size is None :
        logger.info("Passed - node does not accept streams, cannot "
                     "test zero-payload flush")
        return 0

    # Two cycles: send half, flush, send other half, wait for Proceed
    for cycle in range(1, 3) :

        half = buf_size // 2
        remainder = buf_size - half
        offset = (cycle - 1) * buf_size

        # Send first half of the buffer window
        _send_bytes(destination, did, half, offset=offset)

        # Send zero-payload flush
        _send_flush(destination, did)

        # Send remaining half to complete the window
        _send_bytes(destination, did, remainder, offset=(offset + half))

        # Wait for Proceed -- must arrive after full buf_size payload bytes
        if not _wait_for_proceed(logger, destination, sid, did,
                                 "cycle {}".format(cycle)) :
            _close_stream(destination, sid, did)
            return(3)

    _close_stream(destination, sid, did)

    logger.info("Passed")
    return 0


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
