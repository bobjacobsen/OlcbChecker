#!/usr/bin/env python3.10
'''
This checks that a node handles Stream Data Complete with the optional
4-byte total byte count.

Per StreamTransportS section 6.4, Stream Data Complete may optionally
include a 4-byte count of total payload bytes transferred.  The DUT
must handle both forms (with and without the count) without error.

Sequence:
1. PIP guard
2. Open stream, send one full buffer, wait for Proceed
3. Send Stream Data Complete WITH 4-byte byte count
4. Verify no errors, reopen to confirm resources freed
5. Open stream, send one full buffer, wait for Proceed
6. Send Stream Data Complete WITHOUT byte count (2 bytes only)
7. Verify no errors, reopen to confirm resources freed

Usage:
python3.10 check_st200_complete_with_byte_count.py

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


def _send_buffer(destination, did, buf_size):
    '''Send exactly buf_size bytes of stream data.'''
    import olcbchecker
    bytes_sent = 0
    while bytes_sent < buf_size :
        chunk_size = min(buf_size - bytes_sent, 64)
        payload = [((bytes_sent + i) & 0xFF)
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
                    logger.warning("Failure - Proceed SID mismatch ({})"
                                   .format(label))
                    return False
                if received.data[1] != did :
                    logger.warning("Failure - Proceed DID mismatch ({})"
                                   .format(label))
                    return False
                return True
            if received.mti == MTI.Terminate_Due_To_Error :
                logger.warning("Failure - Terminate Due To Error ({})"
                               .format(label))
                return False
            continue
        except Empty:
            logger.warning("Failure - no Proceed ({})".format(label))
            return False


def _check_no_errors(logger, destination, label):
    '''Drain messages and check for errors. Returns True if clean.'''
    import olcbchecker
    time.sleep(0.5)
    while True :
        try :
            received = olcbchecker.getMessage(0.5)
            if destination != received.source :
                continue
            if received.mti == MTI.Terminate_Due_To_Error :
                logger.warning("Failure - Terminate Due To Error after "
                               "Complete ({})".format(label))
                return False
            if received.mti == MTI.Initialization_Complete or \
                    received.mti == MTI.Initialization_Complete_Simple :
                logger.warning("Failure - node rebooted after "
                               "Complete ({})".format(label))
                return False
        except Empty:
            break
    return True


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

    # --- Check 1: Complete WITH 4-byte byte count ---
    sid1 = 0xC0
    buf_size, did1 = _open_stream(logger, destination, 256, sid1)

    if buf_size is None :
        logger.info("Passed - node does not accept streams, cannot "
                     "check Complete with byte count")
        return 0

    _send_buffer(destination, did1, buf_size)

    if not _wait_for_proceed(logger, destination, sid1, did1,
                             "with-count") :
        return(3)

    # Stream Data Complete with byte count: [SID, DID, count(4 bytes BE)]
    total = buf_size
    complete_data = [sid1, did1,
                     (total >> 24) & 0xFF,
                     (total >> 16) & 0xFF,
                     (total >> 8) & 0xFF,
                     total & 0xFF]
    message = Message(MTI.Stream_Data_Complete,
                      NodeID(olcbchecker.ownnodeid()), destination,
                      complete_data)
    olcbchecker.sendMessage(message)

    if not _check_no_errors(logger, destination, "with-count") :
        return(3)

    logger.info("  Complete with 4-byte count accepted")

    # Verify resources freed by reopening
    olcbchecker.purgeMessages()
    buf_size_r, did_r = _open_stream(logger, destination, 256, sid1)

    if buf_size_r is None :
        logger.warning("Failure - could not reopen after Complete "
                       "with byte count")
        return(3)

    # Close the reopen check stream (2-byte form, no count)
    message = Message(MTI.Stream_Data_Complete,
                      NodeID(olcbchecker.ownnodeid()), destination,
                      [sid1, did_r])
    olcbchecker.sendMessage(message)
    time.sleep(0.3)

    # --- Check 2: Complete WITHOUT byte count (2 bytes only) ---
    olcbchecker.purgeMessages()
    sid2 = 0xC1
    buf_size2, did2 = _open_stream(logger, destination, 256, sid2)

    if buf_size2 is None :
        logger.warning("Failure - node rejected second stream open "
                       "after first close")
        return(3)

    _send_buffer(destination, did2, buf_size2)

    if not _wait_for_proceed(logger, destination, sid2, did2,
                             "without-count") :
        return(3)

    # Stream Data Complete without byte count: [SID, DID] only
    message = Message(MTI.Stream_Data_Complete,
                      NodeID(olcbchecker.ownnodeid()), destination,
                      [sid2, did2])
    olcbchecker.sendMessage(message)

    if not _check_no_errors(logger, destination, "without-count") :
        return(3)

    logger.info("  Complete without byte count accepted")

    # Verify resources freed
    olcbchecker.purgeMessages()
    buf_size_r2, did_r2 = _open_stream(logger, destination, 256, sid2)

    if buf_size_r2 is None :
        logger.warning("Failure - could not reopen after Complete "
                       "without byte count")
        return(3)

    message = Message(MTI.Stream_Data_Complete,
                      NodeID(olcbchecker.ownnodeid()), destination,
                      [sid2, did_r2])
    olcbchecker.sendMessage(message)
    time.sleep(0.3)

    logger.info("Passed")
    return 0


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
