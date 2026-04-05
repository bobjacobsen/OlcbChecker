#!/usr/bin/env python3.10
'''
This checks that the DUT handles the maximum number of CAN frames per
buffer window by sending each payload byte as a separate Stream Data
Send message.

Opens a stream with a small buffer (64 bytes) and sends buf_size
individual 1-byte-payload messages per cycle.  This stresses the
receive path and any internal frame-to-stream reassembly.

Usage:
python3.10 check_st130_min_chunk_send.py

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


def _send_single_byte_frames(destination, did, buf_size, offset=0):
    '''Send buf_size bytes, each as a separate Stream Data Send message.'''
    import olcbchecker
    for i in range(buf_size) :
        data = [did, (offset + i) & 0xFF]
        message = Message(MTI.Stream_Data_Send,
                          NodeID(olcbchecker.ownnodeid()), destination, data)
        olcbchecker.sendMessage(message)


def _wait_for_proceed(logger, destination, sid, did, cycle_num):
    '''Wait for a Stream Data Proceed. Returns True on success.'''
    import olcbchecker
    while True :
        try :
            received = olcbchecker.getMessage(5.0)
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

    sid = 0x82
    buf_size, did = _open_stream(logger, destination, 64, sid)

    if buf_size is None :
        logger.info("Passed - node does not accept streams, cannot "
                     "test minimum chunk send")
        return 0

    # Cycle 1: send buf_size individual 1-byte frames
    _send_single_byte_frames(destination, did, buf_size, offset=0)
    if not _wait_for_proceed(logger, destination, sid, did, 1) :
        complete = Message(MTI.Stream_Data_Complete,
                          NodeID(olcbchecker.ownnodeid()), destination,
                          [sid, did])
        olcbchecker.sendMessage(complete)
        time.sleep(0.3)
        return(3)

    # Cycle 2: confirm stability with another round
    _send_single_byte_frames(destination, did, buf_size, offset=buf_size)
    if not _wait_for_proceed(logger, destination, sid, did, 2) :
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

    logger.info("Passed")
    return 0


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
