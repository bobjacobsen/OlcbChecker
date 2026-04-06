#!/usr/bin/env python3.10
'''
This checks that the DUT correctly handles interleaved Stream Data Send
messages on two concurrent streams within the same buffer window.

Existing concurrent checks (st100, st110) send a full buffer on stream A,
wait for Proceed, then send a full buffer on stream B. This check
alternates 32-byte chunks between streams A and B before either window
completes, forcing the DUT to track each stream's byte count
independently.

Per StreamTransportS Section 7.2: "If the node receives multiple
overlapping [streams] from different source nodes, the states shall be
independent." This extends to interleaved data within the same source
when multiple SIDs are in use.

A DUT that rejects the second stream is spec-legal -- this check passes
with info in that case.

Usage:
python3.10 check_st180_interleaved_data_send.py

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


def _send_chunk(destination, did, count, offset=0):
    '''Send exactly count payload bytes as a single Stream Data Send.'''
    import olcbchecker
    payload = [((offset + i) & 0xFF) for i in range(count)]
    data = [did] + payload
    message = Message(MTI.Stream_Data_Send,
                      NodeID(olcbchecker.ownnodeid()), destination, data)
    olcbchecker.sendMessage(message)


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


def _interleaved_send(destination, did_a, buf_a, did_b, buf_b,
                      chunk_size, cycle_offset):
    '''Send interleaved chunks on two streams until both windows are full.

    Alternates: chunk on A, chunk on B, chunk on A, chunk on B, ...
    Each stream gets exactly its buf_size bytes total.
    '''
    sent_a = 0
    sent_b = 0

    while sent_a < buf_a or sent_b < buf_b :

        # Send a chunk on stream A if it still has bytes to send
        if sent_a < buf_a :
            n = min(chunk_size, buf_a - sent_a)
            _send_chunk(destination, did_a, n,
                        offset=(cycle_offset + sent_a))
            sent_a += n

        # Send a chunk on stream B if it still has bytes to send
        if sent_b < buf_b :
            n = min(chunk_size, buf_b - sent_b)
            _send_chunk(destination, did_b, n,
                        offset=(cycle_offset + sent_b))
            sent_b += n


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
    sid_a = 0xE0
    buf_a, did_a = _open_stream(logger, destination, 256, sid_a)

    if buf_a is None :
        logger.info("Passed - node does not accept streams, cannot "
                     "check interleaved data send")
        return 0

    # Open stream B
    sid_b = 0xE1
    buf_b, did_b = _open_stream(logger, destination, 256, sid_b)

    if buf_b is None :
        _close_stream(destination, sid_a, did_a)
        logger.info("Passed - node rejected second concurrent stream, "
                     "spec-legal single-stream node")
        return 0

    # Two cycles of interleaved transfer
    chunk_size = 32

    for cycle in range(1, 3) :

        cycle_offset = (cycle - 1) * max(buf_a, buf_b)

        # Send interleaved chunks: A, B, A, B, ... until both full
        _interleaved_send(destination, did_a, buf_a, did_b, buf_b,
                          chunk_size, cycle_offset)

        # Both windows are now full -- collect Proceeds for both streams.
        # They may arrive in either order.
        got_a = False
        got_b = False

        for _ in range(2) :

            import olcbchecker
            deadline = time.time() + 3.0

            while time.time() < deadline :
                remaining = deadline - time.time()
                if remaining <= 0 :
                    break
                try :
                    received = olcbchecker.getMessage(remaining)
                    if destination != received.source :
                        continue

                    if received.mti == MTI.Terminate_Due_To_Error :
                        logger.warning("Failure - Terminate Due To Error "
                                       "(cycle {})".format(cycle))
                        _close_stream(destination, sid_a, did_a)
                        _close_stream(destination, sid_b, did_b)
                        return(3)

                    if received.mti != MTI.Stream_Data_Proceed :
                        continue

                    if len(received.data) < 2 :
                        logger.warning("Failure - Proceed too short "
                                       "(cycle {})".format(cycle))
                        _close_stream(destination, sid_a, did_a)
                        _close_stream(destination, sid_b, did_b)
                        return(3)

                    rsid = received.data[0]
                    rdid = received.data[1]

                    if rsid == sid_a and rdid == did_a and not got_a :
                        got_a = True
                        break
                    elif rsid == sid_b and rdid == did_b and not got_b :
                        got_b = True
                        break
                    else :
                        logger.warning("Failure - unexpected Proceed "
                                       "SID=0x{:02X} DID=0x{:02X} "
                                       "(cycle {})".format(rsid, rdid, cycle))
                        _close_stream(destination, sid_a, did_a)
                        _close_stream(destination, sid_b, did_b)
                        return(3)

                except Empty:
                    break

        if not got_a :
            logger.warning("Failure - no Proceed for stream A "
                           "(cycle {})".format(cycle))
            _close_stream(destination, sid_a, did_a)
            _close_stream(destination, sid_b, did_b)
            return(3)

        if not got_b :
            logger.warning("Failure - no Proceed for stream B "
                           "(cycle {})".format(cycle))
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
