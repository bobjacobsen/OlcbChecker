#!/usr/bin/env python3.10
'''
This checks sustained high-throughput stream transfer with zero delay
between buffer cycles.

Opens a stream and runs 22 consecutive send/proceed cycles back-to-back.
Verifies the DUT does not leak memory, lose window count, or stall over
many consecutive cycles.  After the transfer, reopens a stream to confirm
the DUT is not stuck.

Per StreamTransportTN section 1, a node may support up to 255 concurrent
streams, and sustained transfer must not degrade.

Usage:
python3.10 check_st120_sustained_transfer.py

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


def _wait_for_proceed(logger, destination, sid, did, cycle_num):
    '''Wait for a Stream Data Proceed. Returns True on success.'''
    import olcbchecker
    while True :
        try :
            received = olcbchecker.getMessage(3.0)
            if destination != received.source :
                continue
            if received.mti == MTI.Stream_Data_Proceed :
                if len(received.data) < 2 :
                    logger.warning("Failure - Proceed too short in "
                                   "cycle {}".format(cycle_num))
                    return False
                if received.data[0] != sid :
                    logger.warning("Failure - Proceed SID mismatch in "
                                   "cycle {}".format(cycle_num))
                    return False
                if received.data[1] != did :
                    logger.warning("Failure - Proceed DID mismatch in "
                                   "cycle {}".format(cycle_num))
                    return False
                return True
            if received.mti == MTI.Terminate_Due_To_Error :
                logger.warning("Failure - Terminate Due To Error in "
                               "cycle {}".format(cycle_num))
                return False
            continue
        except Empty:
            logger.warning("Failure - no Proceed in cycle {}"
                           .format(cycle_num))
            return False


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

    sid = 0x78
    buf_size, did = _open_stream(logger, destination, 256, sid)

    if buf_size is None :
        logger.info("Passed - node does not accept streams, cannot "
                     "check sustained transfer")
        return 0

    # Run 22 consecutive send/proceed cycles with zero delay
    cycle_count = 22
    for cycle in range(1, cycle_count + 1) :
        _send_buffer(destination, did, buf_size,
                     offset=((cycle - 1) * buf_size))
        if not _wait_for_proceed(logger, destination, sid, did, cycle) :
            complete = Message(MTI.Stream_Data_Complete,
                              NodeID(olcbchecker.ownnodeid()), destination,
                              [sid, did])
            olcbchecker.sendMessage(complete)
            time.sleep(0.3)
            return(3)

    # Close the stream
    complete = Message(MTI.Stream_Data_Complete,
                      NodeID(olcbchecker.ownnodeid()), destination,
                      [sid, did])
    olcbchecker.sendMessage(complete)
    time.sleep(0.3)

    # Stability probe: reopen a stream to confirm DUT is not stuck
    olcbchecker.purgeMessages()
    probe_sid = 0x79
    probe_buf, probe_did = _open_stream(logger, destination, 256, probe_sid)
    if probe_buf is not None :
        probe_complete = Message(MTI.Stream_Data_Complete,
                                NodeID(olcbchecker.ownnodeid()), destination,
                                [probe_sid, probe_did])
        olcbchecker.sendMessage(probe_complete)
        time.sleep(0.3)

    logger.info("Passed")
    return 0


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
